import base64
import fitz  # PyMuPDF
import httpx
import io
import pptx
import tiktoken
from bs4 import BeautifulSoup
from markitdown import MarkItDown
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, Chunk
from app.services.embeddings import get_embeddings_batch
from app.core.config import get_settings

settings = get_settings()
tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

CHUNK_SIZE = 800  # tokens (slightly larger for better context)
CHUNK_OVERLAP = 150


def split_into_chunks(text: str, document_title: str = "", chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks and prepend document context."""
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    idx = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        
        # Prepend context to improve retrieval
        contextual_text = f"Tài liệu: {document_title}\n---\n{chunk_text}"
        
        chunks.append({
            "text": contextual_text, 
            "raw_content": chunk_text,
            "index": idx, 
            "token_count": len(chunk_tokens)
        })
        idx += 1
        start += chunk_size - overlap
        if end >= len(tokens):
            break

    return chunks


async def extract_text_with_vision(image_bytes: bytes) -> str:
    """Use GPT-4o-mini Vision to extract text and tables from an image in Markdown format."""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a specialized document parser. Extract all text, tables, and lists from this document page image. Output ONLY the extracted content in clean Markdown format. Preserve the visual structure (tables as | | tables, lists as - bullets). If the page is in Vietnamese, extract as Vietnamese."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all content from this page image into Markdown."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        max_tokens=2048
    )
    return response.choices[0].message.content or ""


def recursive_extract_pptx_text(shape) -> str:
    """Recursively extract text from PPTX shapes, including groups and tables."""
    text_content = []
    
    # Process text frames
    if hasattr(shape, "has_text_frame") and shape.has_text_frame:
        for paragraph in shape.text_frame.paragraphs:
            p_text = paragraph.text.strip()
            if p_text:
                text_content.append(p_text)
    
    # Process tables
    if hasattr(shape, "has_table") and shape.has_table:
        for row in shape.table.rows:
            row_text = " | ".join([cell.text_frame.text.strip() for cell in row.cells])
            if row_text.strip():
                text_content.append(row_text)
                
    # Process groups (ShapeType 6 is GROUP)
    if hasattr(shape, "shape_type") and shape.shape_type == 6:
        for subshape in shape.shapes:
            text_content.append(recursive_extract_pptx_text(subshape))
            
    return "\n".join(text_content)


async def ingest_pdf(db: AsyncSession, document_id: int, file_path: str) -> int:
    """Extract text using MarkItDown + Vision Fallback for high-fidelity RAG."""
    doc_record = await db.get(Document, document_id)
    if not doc_record:
        raise ValueError(f"Document {document_id} not found")

    doc_record.status = "processing"
    await db.commit()

    try:
        # 1. Fast Extraction with MarkItDown
        md = MarkItDown()
        result = md.convert(file_path)
        markdown_text = result.text_content
        
        # 2. Heuristic: If extraction is too light (< 200 chars/page), use Vision
        pdf = fitz.open(file_path)
        num_pages = len(pdf)
        doc_record.page_count = num_pages
        
        # Calculate char density (avoid division by zero)
        density = len(markdown_text) / max(num_pages, 1)
        
        if density < 150:  # Threshold for "image-heavy" or "complex layout"
            print(f"Low density ({density}) detected. Switching to Vision-OCR for {document_id}")
            vision_parts = []
            for page_num in range(num_pages):
                page = pdf[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom for better OCR
                img_bytes = pix.tobytes("png")
                page_md = await extract_text_with_vision(img_bytes)
                vision_parts.append(f"<!-- Page {page_num + 1} -->\n{page_md}")
            markdown_text = "\n\n---\n\n".join(vision_parts)
        
        pdf.close()
        
        if not markdown_text.strip():
            doc_record.status = "error"
            await db.commit()
            return 0

        all_chunks = split_into_chunks(markdown_text, document_title=doc_record.title)

        # Generate embeddings and store
        texts = [c["text"] for c in all_chunks]
        embeddings = await get_embeddings_batch(texts)

        for chunk, embedding in zip(all_chunks, embeddings):
            db_chunk = Chunk(
                document_id=document_id,
                content=chunk["text"],
                embedding=embedding,
                chunk_index=chunk["index"],
                token_count=chunk["token_count"],
            )
            db.add(db_chunk)

        doc_record.status = "ready"
        await db.commit()
        return len(all_chunks)

    except Exception as e:
        doc_record.status = "error"
        await db.commit()
        raise e


async def ingest_web(db: AsyncSession, document_id: int, url: str) -> int:
    """Crawl a web page, extract text, chunk it, embed it, and store."""
    doc_record = await db.get(Document, document_id)
    if not doc_record:
        raise ValueError(f"Document {document_id} not found")

    doc_record.status = "processing"
    await db.commit()

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            if settings.web_extractor_url:
                # Use Defuddle worker
                extractor_url = settings.web_extractor_url.rstrip("/")
                target_url = url
                # The worker endpoint is GET /<url>
                fetch_url = f"{extractor_url}/{target_url}"
                resp = await client.get(fetch_url)
                resp.raise_for_status()
                text = resp.text
            else:
                # Fallback to BeautifulSoup
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                # Remove script, style, nav elements
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)

        if not text:
            doc_record.status = "error"
            await db.commit()
            return 0

        all_chunks = split_into_chunks(text, document_title=doc_record.title)

        texts = [c["text"] for c in all_chunks]
        embeddings = await get_embeddings_batch(texts)

        for chunk, embedding in zip(all_chunks, embeddings):
            db_chunk = Chunk(
                document_id=document_id,
                content=chunk["text"],
                embedding=embedding,
                chunk_index=chunk["index"],
                token_count=chunk["token_count"],
            )
            db.add(db_chunk)

        doc_record.status = "ready"
        await db.commit()
        return len(all_chunks)

    except Exception as e:
        doc_record.status = "error"
        await db.commit()
        raise e
async def ingest_ppt(db: AsyncSession, document_id: int, file_path: str) -> int:
    """Extract text from PPTX using Recursive Shape Analysis + MarkItDown fallback."""
    doc_record = await db.get(Document, document_id)
    if not doc_record:
        raise ValueError(f"Document {document_id} not found")

    doc_record.status = "processing"
    await db.commit()

    try:
        prs = pptx.Presentation(file_path)
        doc_record.page_count = len(prs.slides)
        
        slide_parts = []
        for i, slide in enumerate(prs.slides):
            page_text = f"<!-- Slide {i+1} -->\n"
            shapes_text = []
            for shape in slide.shapes:
                shapes_text.append(recursive_extract_pptx_text(shape))
            
            # If shape extraction is very light, use MarkItDown for the whole slide?
            # Or just trust the recursive walker.
            slide_md = "\n".join([t for t in shapes_text if t.strip()])
            slide_parts.append(page_text + slide_md)
            
        markdown_text = "\n\n---\n\n".join(slide_parts)

        if not markdown_text.strip():
            # Fallback to MarkItDown
            md = MarkItDown()
            result = md.convert(file_path)
            markdown_text = result.text_content

        if not markdown_text.strip():
            doc_record.status = "error"
            await db.commit()
            return 0

        all_chunks = split_into_chunks(markdown_text, document_title=doc_record.title)

        # Generate embeddings and store
        texts = [c["text"] for c in all_chunks]
        embeddings = await get_embeddings_batch(texts)

        for chunk, embedding in zip(all_chunks, embeddings):
            db_chunk = Chunk(
                document_id=document_id,
                content=chunk["text"],
                embedding=embedding,
                chunk_index=chunk["index"],
                token_count=chunk["token_count"],
            )
            db.add(db_chunk)

        doc_record.status = "ready"
        await db.commit()
        return len(all_chunks)

    except Exception as e:
        doc_record.status = "error"
        await db.commit()
        raise e

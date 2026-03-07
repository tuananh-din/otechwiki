import os
import shutil
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.document import Document, Chunk, Product, document_products
from app.services.ingest import ingest_web
from app.schemas.schemas import DocumentResponse, ProductResponse, ProductCreate, AnalyticsResponse
from app.services.discovery import discover_urls

settings = get_settings()
router = APIRouter(prefix="/api", tags=["documents"])


# --- Products ---
@router.get("/products", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Product, func.count(document_products.c.document_id).label("doc_count"))
        .outerjoin(document_products, Product.id == document_products.c.product_id)
        .group_by(Product.id)
        .order_by(Product.name)
    )
    return [
        ProductResponse(
            id=p.id, name=p.name, slug=p.slug, description=p.description,
            category=p.category, image_url=p.image_url, document_count=count,
        )
        for p, count in result.all()
    ]


@router.get("/products/{slug}")
async def get_product(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.slug == slug))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    docs_result = await db.execute(
        select(Document)
        .join(document_products, Document.id == document_products.c.document_id)
        .where(document_products.c.product_id == product.id, Document.status == "ready")
    )
    docs = docs_result.scalars().all()

    return {
        "product": ProductResponse.model_validate(product),
        "documents": [DocumentResponse(
            id=d.id, title=d.title, source_type=d.source_type, source_url=d.source_url,
            document_type=d.document_type, page_count=d.page_count, status=d.status,
            created_at=d.created_at,
        ) for d in docs],
    }


@router.post("/products", response_model=ProductResponse)
async def create_product(req: ProductCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    product = Product(name=req.name, slug=req.slug, description=req.description, category=req.category)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse(id=product.id, name=product.name, slug=product.slug,
                           description=product.description, category=product.category, document_count=0)


# --- Documents ---
@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id, title=d.title, source_type=d.source_type, source_url=d.source_url,
            document_type=d.document_type, page_count=d.page_count, status=d.status,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    return {
        "document": DocumentResponse(
            id=doc.id, title=doc.title, source_type=doc.source_type, source_url=doc.source_url,
            document_type=doc.document_type, page_count=doc.page_count, status=doc.status,
            created_at=doc.created_at,
        ),
        "chunks": [{"id": c.id, "content": c.content, "page_number": c.page_number,
                     "section_title": c.section_title, "chunk_index": c.chunk_index} for c in chunks],
    }


# --- Admin: Upload & Ingest ---
@router.post("/admin/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("product_spec"),
    product_ids: str = Form(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ext = file.filename.lower().split(".")[-1]
    if ext not in ["pdf", "pptx"]:
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files accepted")

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)
    doc = Document(
        title=title, source_type=ext, source_path=file_path,
        document_type=document_type, file_size=file_size,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Link to products
    if product_ids:
        for pid in product_ids.split(","):
            pid = pid.strip()
            if pid.isdigit():
                await db.execute(document_products.insert().values(document_id=doc.id, product_id=int(pid)))
        await db.commit()

    if ext == "pdf":
        from app.services.ingest import ingest_pdf
        chunk_count = await ingest_pdf(db, doc.id, file_path)
    else:
        from app.services.ingest import ingest_ppt
        chunk_count = await ingest_ppt(db, doc.id, file_path)
        
    return {"document_id": doc.id, "chunks_created": chunk_count, "status": "ready"}

# Keep alias for backward compatibility
@router.post("/admin/upload-pdf")
async def upload_pdf_alias(*args, **kwargs):
    return await upload_document(*args, **kwargs)


@router.post("/admin/ingest-web")
async def ingest_web_page(
    url: str = Form(...),
    title: str = Form(...),
    document_type: str = Form("company_info"),
    product_ids: str = Form(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    doc = Document(title=title, source_type="web", source_url=url, document_type=document_type)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if product_ids:
        for pid in product_ids.split(","):
            pid = pid.strip()
            if pid.isdigit():
                await db.execute(document_products.insert().values(document_id=doc.id, product_id=int(pid)))
        await db.commit()

    chunk_count = await ingest_web(db, doc.id, url)
    return {"document_id": doc.id, "chunks_created": chunk_count, "status": "ready"}


@router.post("/admin/scan-urls")
async def scan_urls(
    homepage_url: str = Form(...),
    limit: int = Form(60),
    depth: int = Form(2),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Discover sub-pages starting from a homepage."""
    urls = await discover_urls(homepage_url, limit=limit, depth=depth)
    
    # Check which URLs already exist in DB
    existing_result = await db.execute(select(Document.source_url).where(Document.source_url.in_(urls)))
    existing_urls = set(existing_result.scalars().all())
    
    # Return list of objects with exists flag
    results = []
    for url in urls:
        results.append({
            "url": url,
            "exists": url in existing_urls
        })
    
    return results


@router.post("/admin/bulk-ingest-web")
async def bulk_ingest_web(
    urls: list[str],
    document_type: str = "company_info",
    product_ids: list[int] = [],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Ingest multiple URLs at once."""
    success_count = 0
    results = []
    
    for url in urls:
        # Final safety check against duplicates
        existing = await db.execute(select(Document).where(Document.source_url == url))
        if existing.scalar_one_or_none():
            continue
            
        try:
            # Generate a title from URL (last part or domain)
            parsed = urlparse(url)
            title = parsed.path.strip("/").split("/")[-1] or parsed.netloc
            title = title.replace("-", " ").replace("_", " ").title()
            
            doc = Document(title=title, source_type="web", source_url=url, document_type=document_type)
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            
            if product_ids:
                for pid in product_ids:
                    await db.execute(document_products.insert().values(document_id=doc.id, product_id=pid))
                await db.commit()
                
            chunks = await ingest_web(db, doc.id, url)
            results.append({"url": url, "document_id": doc.id, "chunks": chunks, "status": "success"})
            success_count += 1
        except Exception as e:
            results.append({"url": url, "error": str(e), "status": "error"})
            
    return {"processed": len(urls), "success": success_count, "details": results}


# --- Admin: Analytics ---
@router.get("/admin/analytics", response_model=AnalyticsResponse)
async def get_analytics(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from app.models.document import SearchLog

    total_searches = (await db.execute(select(func.count(SearchLog.id)))).scalar() or 0
    total_documents = (await db.execute(select(func.count(Document.id)).where(Document.status == "ready"))).scalar() or 0
    total_chunks = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0

    # Top queries
    top_q = await db.execute(
        select(SearchLog.query, func.count(SearchLog.id).label("count"))
        .group_by(SearchLog.query)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
    )
    top_queries = [{"query": q, "count": c} for q, c in top_q.all()]

    # No-result queries
    no_res = await db.execute(
        select(SearchLog.query, func.count(SearchLog.id).label("count"))
        .where(SearchLog.results_count == 0)
        .group_by(SearchLog.query)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
    )
    no_result_queries = [{"query": q, "count": c} for q, c in no_res.all()]

    # Searches by day (last 30 days)
    daily = await db.execute(
        select(func.date_trunc("day", SearchLog.created_at).label("day"), func.count(SearchLog.id).label("count"))
        .group_by("day")
        .order_by("day")
        .limit(30)
    )
    searches_by_day = [{"date": d.isoformat(), "count": c} for d, c in daily.all()]

    return AnalyticsResponse(
        total_searches=total_searches, total_documents=total_documents, total_chunks=total_chunks,
        top_queries=top_queries, no_result_queries=no_result_queries, searches_by_day=searches_by_day,
    )

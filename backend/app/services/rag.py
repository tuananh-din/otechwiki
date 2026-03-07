import openai
from app.core.config import get_settings
from app.services.search import hybrid_search
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    default_headers=settings.openai_extra_headers
)

SYSTEM_PROMPT = """Bạn là trợ lý tra cứu kiến thức sản phẩm nội bộ. Nhiệm vụ của bạn:

1. CHỈ trả lời dựa trên thông tin trong phần CONTEXT bên dưới.
2. Mỗi thông tin bạn đưa ra PHẢI kèm trích dẫn theo format [Nguồn: tên_tài_liệu, trang X] hoặc [Nguồn: tên_tài_liệu].
3. Trả lời ngắn gọn, rõ ràng, dễ copy để nhân viên CS sử dụng ngay.
4. Nếu CONTEXT không chứa đủ thông tin để trả lời → BẮT BUỘC phải nói: "Không tìm thấy thông tin phù hợp trong dữ liệu hiện có. Vui lòng kiểm tra lại từ khóa hoặc cập nhật thêm nguồn tài liệu."
5. TUYỆT ĐỐI KHÔNG bịa thêm thông tin ngoài CONTEXT.
6. Trả lời bằng tiếng Việt.
"""


async def ask_with_rag(
    db: AsyncSession,
    query: str,
    product_filter: str | None = None,
    doc_type_filter: str | None = None,
) -> dict:
    """RAG pipeline: search → build context → LLM answer with citations."""
    # 0. Analyze query for intent
    from app.services.query_understanding import analyze_query
    analysis = await analyze_query(query)
    
    # 1. Retrieve relevant chunks
    chunks = await hybrid_search(
        db, query, limit=settings.rag_context_chunks, product_filter=product_filter, doc_type_filter=doc_type_filter
    )

    if not chunks:
        return {
            "answer": "Không tìm thấy thông tin phù hợp trong dữ liệu hiện có. Vui lòng kiểm tra lại từ khóa hoặc cập nhật thêm nguồn tài liệu.",
            "citations": [],
            "no_result": True,
        }

    # 2. Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["document_title"]
        page = f", trang {chunk['page_number']}" if chunk.get("page_number") else ""
        section = f", phần {chunk['section_title']}" if chunk.get("section_title") else ""
        context_parts.append(f"[Nguồn {i}: {source}{page}{section}]\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    # 3. Call LLM with Intent awareness
    intent_guidance = ""
    if analysis.intent == "troubleshooting":
        intent_guidance = "\nLƯU Ý: Đây là câu hỏi về lỗi/sửa chữa. Hãy trình bày các bước khắc phục rõ ràng theo dạng danh sách."
    elif analysis.intent == "comparison":
        intent_guidance = "\nLƯU Ý: Đây là câu hỏi về so sánh. Hãy so sánh các đặc điểm khác biệt chính giữa các model/sản phẩm."
    elif analysis.intent == "specifications":
        intent_guidance = "\nLƯU Ý: Đây là câu hỏi về thông số kỹ thuật. Hãy tập trung vào các con số và đơn vị đo lường."

    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + intent_guidance},
            {"role": "user", "content": f"QUERY ANALYSIS:\n- Intent: {analysis.intent}\n- Keywords: {', '.join(analysis.expanded_keywords)}\n\nCONTEXT:\n{context}\n\nCÂU HỎI: {query}"},
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    answer = response.choices[0].message.content

    # 4. Build citations
    citations = [
        {
            "document_id": chunk["document_id"],
            "document_title": chunk["document_title"],
            "page_number": chunk.get("page_number"),
            "section_title": chunk.get("section_title"),
            "snippet": chunk["content"][:200],
        }
        for chunk in chunks
    ]

    return {"answer": answer, "citations": citations, "no_result": False}

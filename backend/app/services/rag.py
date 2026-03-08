import openai
from app.core.config import get_settings
from app.services.search import hybrid_search
from app.services.follow_up import generate_follow_ups
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

settings = get_settings()
client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    default_headers=settings.openai_extra_headers
)

# ── Standard RAG prompt ───────────────────────────────────────────────

SYSTEM_PROMPT = """Bạn là trợ lý tra cứu kiến thức sản phẩm nội bộ. Nhiệm vụ của bạn:

1. CHỈ trả lời dựa trên thông tin trong phần CONTEXT bên dưới.
2. Mỗi thông tin bạn đưa ra PHẢI kèm trích dẫn theo format [Nguồn: tên_tài_liệu, trang X] hoặc [Nguồn: tên_tài_liệu].
3. Trả lời ngắn gọn, rõ ràng, dễ copy để nhân viên CS sử dụng ngay.
4. Nếu CONTEXT không chứa đủ thông tin để trả lời → BẮT BUỘC phải nói: "Không tìm thấy thông tin phù hợp trong dữ liệu hiện có. Vui lòng kiểm tra lại từ khóa hoặc cập nhật thêm nguồn tài liệu."
5. TUYỆT ĐỐI KHÔNG bịa thêm thông tin ngoài CONTEXT.
6. Trả lời bằng tiếng Việt.
"""

# ── Comparison synthesis prompt ───────────────────────────────────────

COMPARISON_PROMPT = """Bạn là trợ lý tra cứu kiến thức sản phẩm nội bộ. Nhiệm vụ hiện tại: SO SÁNH SẢN PHẨM.

QUY TẮC NGHIÊM NGẶT:
1. CHỈ sử dụng thông tin trong CONTEXT. TUYỆT ĐỐI KHÔNG bịa thêm.
2. Nếu CONTEXT không đủ dữ liệu để so sánh → nói rõ: "Chưa đủ dữ liệu để so sánh đầy đủ."
3. Trả lời bằng tiếng Việt, ngắn gọn, dễ dùng cho nhân viên CS.

FORMAT TRẢ LỜI BẮT BUỘC:

**1. Tổng quan**
[Giới thiệu ngắn 1-2 câu về các sản phẩm được so sánh]

**2. Điểm giống nhau**
- [Liệt kê các đặc điểm chung]

**3. Điểm khác nhau**
| Tiêu chí | [Model A] | [Model B] |
|----------|-----------|-----------|
| [tiêu chí] | [giá trị] | [giá trị] |

**4. Kết luận**
[Tóm tắt 1-2 câu giúp CS tư vấn nhanh]

**5. Nguồn tham chiếu**
[Liệt kê các nguồn đã dùng]
"""

# ── Model recommendation prompt ───────────────────────────────────────

RECOMMENDATION_PROMPT = """Bạn là trợ lý tra cứu kiến thức sản phẩm nội bộ. Nhiệm vụ hiện tại: TƯ VẤN CHỌN MODEL.

QUY TẮC NGHIÊM NGẶT:
1. CHỈ sử dụng thông tin trong CONTEXT. TUYỆT ĐỐI KHÔNG bịa thêm.
2. Nếu CONTEXT không đủ dữ liệu để tư vấn → nói rõ: "Chưa đủ dữ liệu để đưa ra tư vấn chính xác."
3. Kết luận phải dựa trên bằng chứng có trong tài liệu.
4. Trả lời bằng tiếng Việt, ngắn gọn, dễ dùng cho nhân viên CS.

FORMAT TRẢ LỜI BẮT BUỘC:

**1. Nhu cầu người dùng**
[Tóm tắt nhu cầu được hỏi]

**2. Model phù hợp**
[Tên model được tư vấn]

**3. Lý do lựa chọn**
- [Lý do 1 dựa trên dữ liệu]
- [Lý do 2 dựa trên dữ liệu]

**4. Lưu ý**
[Nếu có model khác cũng đáng cân nhắc, hoặc hạn chế cần biết]

**5. Nguồn tham chiếu**
[Liệt kê các nguồn đã dùng]
"""

# ── Intent guidance (for standard queries) ────────────────────────────

INTENT_GUIDANCE = {
    "troubleshooting": "\nLƯU Ý: Đây là câu hỏi về lỗi/sửa chữa. Hãy trình bày các bước khắc phục rõ ràng theo dạng danh sách.",
    "specifications": "\nLƯU Ý: Đây là câu hỏi về thông số kỹ thuật. Hãy tập trung vào các con số và đơn vị đo lường.",
    "price_lookup": "\nLƯU Ý: Đây là câu hỏi về giá. Hãy trả lời trực tiếp giá và các thông tin liên quan đến chi phí.",
    "feature_lookup": "\nLƯU Ý: Đây là câu hỏi về tính năng. Hãy liệt kê các tính năng nổi bật ngắn gọn.",
    "policy": "\nLƯU Ý: Đây là câu hỏi về chính sách/bảo hành. Hãy trả lời chính xác các điều khoản và điều kiện.",
}

# Synthesis intents that use special prompts
SYNTHESIS_INTENTS = {"comparison", "model_recommendation"}


async def ask_with_rag(
    db: AsyncSession,
    query: str,
    product_filter: str | None = None,
    doc_type_filter: str | None = None,
) -> dict:
    """RAG pipeline: analyze → retrieve → answer → follow-ups."""
    # 0. Analyze query for intent + product detection
    from app.services.query_understanding import analyze_query
    analysis = await analyze_query(query)

    # 1. Retrieve relevant chunks
    is_synthesis = analysis.intent in SYNTHESIS_INTENTS

    if is_synthesis and len(analysis.detected_products) >= 2:
        # Multi-product retrieval: search each product separately for better coverage
        all_chunks = []
        seen_ids = set()
        for product in analysis.detected_products:
            product_query = f"{product} {query}"
            chunks = await hybrid_search(
                db, product_query, limit=settings.rag_context_chunks,
                product_filter=product_filter, doc_type_filter=doc_type_filter,
            )
            for c in chunks:
                if c["id"] not in seen_ids:
                    all_chunks.append(c)
                    seen_ids.add(c["id"])
        chunks = all_chunks[:settings.rag_context_chunks * 2]  # Allow more context for comparisons

    elif analysis.intent == "price_lookup" and analysis.detected_product:
        # Direct product page chunk injection: bypass search ranking for price queries
        # Search ranking fails for prices because '14.990.000₫' doesn't match 'giá' semantically
        all_chunks = []
        seen_ids = set()

        # 1. Direct lookup: get chunks from the product's own detail page
        product_chunks_sql = text("""
            SELECT c.id, COALESCE(c.cleaned_content, c.content) as content,
                   c.document_id, c.page_number, c.section_title,
                   d.title as document_title, d.source_type,
                   1.0 as rrf_score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            JOIN document_products dp ON d.id = dp.document_id
            JOIN products p ON dp.product_id = p.id
            JOIN product_aliases pa ON p.id = pa.product_id
            WHERE d.status = 'ready'
              AND d.page_type = 'product_detail'
              AND (c.is_searchable = true OR c.is_searchable IS NULL)
              AND LOWER(pa.alias) = LOWER(:product_name)
            ORDER BY dp.confidence DESC, c.chunk_index ASC
            LIMIT 4
        """)
        result = await db.execute(product_chunks_sql, {"product_name": analysis.detected_product})
        product_rows = result.mappings().all()
        for row in product_rows:
            chunk = {
                "id": row["id"], "content": row["content"],
                "score": float(row["rrf_score"]),
                "document_id": row["document_id"],
                "document_title": row["document_title"],
                "source_type": row["source_type"],
                "page_number": row["page_number"],
                "section_title": row["section_title"],
            }
            if chunk["id"] not in seen_ids:
                all_chunks.append(chunk)
                seen_ids.add(chunk["id"])

        # 2. Top up with regular search results
        search_results = await hybrid_search(
            db, query, limit=settings.rag_context_chunks,
            product_filter=product_filter, doc_type_filter=doc_type_filter,
        )
        for c in search_results:
            if c["id"] not in seen_ids:
                all_chunks.append(c)
                seen_ids.add(c["id"])

        chunks = all_chunks[:settings.rag_context_chunks + 4]

    elif analysis.intent in ("policy", "troubleshooting", "feature_lookup", "specifications"):
        # Multi-query retrieval: product search + topic-specific search
        # This ensures warranty questions get both product AND policy context
        all_chunks = []
        seen_ids = set()

        # Primary search: original query
        primary = await hybrid_search(
            db, query, limit=settings.rag_context_chunks,
            product_filter=product_filter, doc_type_filter=doc_type_filter,
        )
        for c in primary:
            if c["id"] not in seen_ids:
                all_chunks.append(c)
                seen_ids.add(c["id"])

        # Secondary search: intent-specific query to broaden context
        topic_queries = {
            "policy": "chính sách bảo hành đổi trả điều kiện thời hạn",
            "troubleshooting": "hướng dẫn xử lý lỗi cách khắc phục",
            "feature_lookup": "thông số kỹ thuật đặc điểm nổi bật tính năng",
            "specifications": "thông số cấu hình kích thước pin lực hút",
        }
        secondary_query = topic_queries.get(analysis.intent, "")
        if secondary_query:
            # Combine with detected product for relevance
            if analysis.detected_product:
                secondary_query = f"{analysis.detected_product} {secondary_query}"
            secondary = await hybrid_search(
                db, secondary_query, limit=settings.rag_context_chunks // 2,
                product_filter=product_filter, doc_type_filter=doc_type_filter,
            )
            for c in secondary:
                if c["id"] not in seen_ids:
                    all_chunks.append(c)
                    seen_ids.add(c["id"])

        chunks = all_chunks[:settings.rag_context_chunks + 4]  # Allow a bit more context

    else:
        chunks = await hybrid_search(
            db, query, limit=settings.rag_context_chunks,
            product_filter=product_filter, doc_type_filter=doc_type_filter,
        )

    if not chunks:
        follow_ups = generate_follow_ups(query, analysis.intent, analysis.detected_product)
        return {
            "answer": "Không tìm thấy thông tin phù hợp trong dữ liệu hiện có. Vui lòng kiểm tra lại từ khóa hoặc cập nhật thêm nguồn tài liệu.",
            "citations": [],
            "no_result": True,
            "answer_type": "standard",
            "follow_up_questions": follow_ups,
        }

    # 2. Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["document_title"]
        page = f", trang {chunk['page_number']}" if chunk.get("page_number") else ""
        section = f", phần {chunk['section_title']}" if chunk.get("section_title") else ""
        context_parts.append(f"[Nguồn {i}: {source}{page}{section}]\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    # 3. Select prompt based on intent
    if analysis.intent == "comparison":
        system_prompt = COMPARISON_PROMPT
        answer_type = "comparison"
    elif analysis.intent == "model_recommendation":
        system_prompt = RECOMMENDATION_PROMPT
        answer_type = "recommendation"
    else:
        intent_extra = INTENT_GUIDANCE.get(analysis.intent, "")
        system_prompt = SYSTEM_PROMPT + intent_extra
        answer_type = "standard"

    # 4. Call LLM
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"QUERY ANALYSIS:\n- Intent: {analysis.intent}\n- Keywords: {', '.join(analysis.expanded_keywords)}\n- Products: {', '.join(analysis.detected_products) or 'N/A'}\n\nCONTEXT:\n{context}\n\nCÂU HỎI: {query}"},
        ],
        temperature=0.1,
        max_tokens=1200 if is_synthesis else 1000,
    )

    answer = response.choices[0].message.content

    # 5. Build citations
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

    # 6. Generate follow-up suggestions (rule-based, 0 token cost)
    follow_ups = generate_follow_ups(query, analysis.intent, analysis.detected_product)

    return {
        "answer": answer,
        "citations": citations,
        "no_result": False,
        "answer_type": answer_type,
        "follow_up_questions": follow_ups,
    }

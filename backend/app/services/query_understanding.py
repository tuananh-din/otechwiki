import json
import logging
from typing import Optional, List
from pydantic import BaseModel
import openai
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    default_headers=settings.openai_extra_headers
)

class QueryAnalysis(BaseModel):
    intent: str
    expanded_keywords: List[str]
    detected_language: str
    suggested_filters: dict
    detected_product: Optional[str] = None
    detected_products: List[str] = []

QUERY_ANALYSIS_PROMPT = """Bạn là chuyên gia phân tích truy vấn cho hệ thống RAG (Retrieval-Augmented Generation) của ứng dụng tra cứu kiến thức sản phẩm nội bộ.
Nhiệm vụ của bạn là phân tích câu hỏi của người dùng (có thể là tiếng Việt, tiếng Anh hoặc pha trộn) để tối ưu hóa việc tìm kiếm.

Hãy phân tích và trả về kết quả dưới định dạng JSON với các trường sau:
1. "intent": Loại ý định của người dùng. Chọn một trong: [price_lookup, feature_lookup, specifications, comparison, model_recommendation, policy, troubleshooting, company_info, faq, general].
   - price_lookup: hỏi giá, chi phí
   - feature_lookup: hỏi tính năng, điểm nổi bật
   - specifications: hỏi thông số kỹ thuật, kích thước, công suất
   - comparison: so sánh 2+ model/sản phẩm
   - model_recommendation: hỏi nên chọn model nào, tư vấn model phù hợp
   - policy: bảo hành, chính sách, quy định
   - troubleshooting: lỗi, sửa chữa, khắc phục
   - company_info: thông tin công ty
   - faq: câu hỏi thường gặp chung
   - general: các câu hỏi khác
2. "expanded_keywords": Danh sách các từ khóa mở rộng liên quan đến câu hỏi. Bao gồm:
   - Các từ đồng nghĩa trong tiếng Việt.
   - Các thuật ngữ tương đương trong tiếng Anh (nếu có).
   - Các model sản phẩm hoặc linh kiện liên quan (nếu được nhắc tới).
   - Các biến thể viết tắt (ví dụ: BH cho bảo hành, CS cho Customer Service).
3. "detected_language": Ngôn ngữ chính hoặc loại ngôn ngữ (vi, en, mixed).
4. "suggested_filters": Các bộ lọc gợi ý dựa trên intent hoặc nội dung câu hỏi (ví dụ: product_slug, document_type).
5. "detected_product": Tên/model sản phẩm CHÍNH được nhắc tới trong câu hỏi (null nếu không có). Ví dụ: "F25", "F25 Ultra", "Máy giặt LG".
6. "detected_products": Danh sách TẤT CẢ các sản phẩm/model được nhắc tới (mảng rỗng nếu không có). Quan trọng khi so sánh nhiều model.

QUY TẮC:
- Nếu là câu hỏi về lỗi hoặc sửa chữa -> intent=troubleshooting.
- Nếu là câu hỏi về thông số, kích thước, công suất -> intent=specifications.
- Nếu là câu hỏi so sánh 2+ model -> intent=comparison.
- Nếu hỏi "nên chọn model nào", "model nào phù hợp" -> intent=model_recommendation.
- Nếu là câu hỏi về giá, chi phí -> intent=price_lookup.
- Nếu là câu hỏi về tính năng, điểm đặc biệt -> intent=feature_lookup.
- Nếu là câu hỏi về quy định, thời gian bảo hành -> intent=policy.
- Kết quả TRẢ VỀ CHỈ LÀ JSON, không kèm lời giải thích.

VÍ DỤ 1:
Query: "Giá F25"
Response:
{
  "intent": "price_lookup",
  "expanded_keywords": ["giá", "price", "F25", "chi phí", "bao nhiêu tiền"],
  "detected_language": "vi",
  "suggested_filters": {"product_slug": "f25"},
  "detected_product": "F25",
  "detected_products": ["F25"]
}

VÍ DỤ 2:
Query: "F25 khác gì F25 Ultra?"
Response:
{
  "intent": "comparison",
  "expanded_keywords": ["F25", "F25 Ultra", "khác nhau", "so sánh", "difference", "compare"],
  "detected_language": "vi",
  "suggested_filters": {},
  "detected_product": "F25",
  "detected_products": ["F25", "F25 Ultra"]
}

VÍ DỤ 3:
Query: "Nên chọn model nào cho nhà nhỏ?"
Response:
{
  "intent": "model_recommendation",
  "expanded_keywords": ["chọn model", "nhà nhỏ", "phù hợp", "tư vấn", "recommend", "small house"],
  "detected_language": "vi",
  "suggested_filters": {},
  "detected_product": null,
  "detected_products": []
}
"""

async def analyze_query(query: str) -> QueryAnalysis:
    """Analyze user query using LLM for intent, keywords, and product detection."""
    try:
        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
                {"role": "user", "content": f'Query: "{query}"'},
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return QueryAnalysis(**data)
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return QueryAnalysis(
            intent="general",
            expanded_keywords=[query],
            detected_language="mixed",
            suggested_filters={},
            detected_product=None,
            detected_products=[],
        )

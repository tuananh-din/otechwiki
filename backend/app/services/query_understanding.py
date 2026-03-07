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

QUERY_ANALYSIS_PROMPT = """Bạn là chuyên gia phân tích truy vấn cho hệ thống RAG (Retrieval-Augmented Generation) của ứng dụng tra cứu kiến thức sản phẩm nội bộ.
Nhiệm vụ của bạn là phân tích câu hỏi của người dùng (có thể là tiếng Việt, tiếng Anh hoặc pha trộn) để tối ưu hóa việc tìm kiếm.

Hãy phân tích và trả về kết quả dưới định dạng JSON với các trường sau:
1. "intent": Loại ý định của người dùng. Chọn một trong: [troubleshooting, specifications, comparison, policy, manual, company_info, faq, general].
2. "expanded_keywords": Danh sách các từ khóa mở rộng liên quan đến câu hỏi. Bao gồm:
   - Các từ đồng nghĩa trong tiếng Việt.
   - Các thuật ngữ tương đương trong tiếng Anh (nếu có).
   - Các model sản phẩm hoặc linh kiện liên quan (nếu được nhắc tới).
   - Các biến thể viết tắt (ví dụ: BH cho bảo hành, CS cho Customer Service).
3. "detected_language": Ngôn ngữ chính hoặc loại ngôn ngữ (vi, en, mixed).
4. "suggested_filters": Các bộ lọc gợi ý dựa trên intent hoặc nội dung câu hỏi (ví dụ: product_slug, document_type).

QUY TẮC:
- Nếu là câu hỏi về lỗi hoặc sửa chữa -> intent=troubleshooting.
- Nếu là câu hỏi về thông số, kích thước, công suất -> intent=specifications.
- Nếu là câu hỏi so sánh 2 model -> intent=comparison.
- Nếu là câu hỏi về quy định, thời gian bảo hành -> intent=policy.
- Kết quả TRẢ VỀ CHỈ LÀ JSON, không kèm lời giải thích.

VÍ DỤ:
Query: "làm sao để fix lỗi E1 trên máy lọc nước"
Response:
{
  "intent": "troubleshooting",
  "expanded_keywords": ["lỗi E1", "error E1", "máy lọc nước", "water purifier", "sửa lỗi", "khắc phục", "fix bug"],
  "detected_language": "vi",
  "suggested_filters": {"document_type": "manual"}
}
"""

async def analyze_query(query: str) -> QueryAnalysis:
    """Analyze user query using LLM for intent and keywords expansion."""
    try:
        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Query: \"{query}\""},
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return QueryAnalysis(**data)
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        # Fallback to simple analysis if LLM fails
        return QueryAnalysis(
            intent="general",
            expanded_keywords=[query],
            detected_language="mixed",
            suggested_filters={}
        )

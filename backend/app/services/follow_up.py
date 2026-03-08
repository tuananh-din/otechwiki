"""Rule-based + LLM fallback follow-up question generator.

Strategy:
1. Use detected intent + product to pick from templates (0 token cost)
2. Only fall back to LLM if templates produce <3 relevant results
"""

from typing import Optional


# ── Templates keyed by (intent, has_product) ──────────────────────────

_PRODUCT_TEMPLATES: dict[str, list[str]] = {
    "price_lookup": [
        "Tính năng nổi bật của {product} là gì?",
        "Thông số chính của {product}",
        "{product} phù hợp với nhu cầu nào?",
        "{product} khác gì model khác?",
        "Bảo hành {product} như thế nào?",
    ],
    "feature_lookup": [
        "Giá {product} bao nhiêu?",
        "Thông số chính của {product}",
        "{product} phù hợp với ai?",
        "{product} khác model nào gần nhất?",
        "Bảo hành {product} thế nào?",
    ],
    "specifications": [
        "Tính năng nổi bật của {product} là gì?",
        "Giá {product} bao nhiêu?",
        "{product} so với model nào tương đương?",
        "Bảo hành {product} thế nào?",
        "{product} phù hợp cho nhu cầu nào?",
    ],
    "comparison": [
        "Giá của từng model đang so sánh?",
        "Thông số chi tiết từng model?",
        "Nên chọn model nào nếu ưu tiên giá?",
        "Nên chọn model nào nếu ưu tiên tính năng?",
        "Bảo hành của từng model?",
    ],
    "model_recommendation": [
        "Giá của model được tư vấn?",
        "Thông số chi tiết của model được tư vấn?",
        "Model nào khác cũng phù hợp?",
        "Bảo hành model này thế nào?",
        "Tính năng nổi bật nhất của model này?",
    ],
    "policy": [
        "Điều kiện áp dụng cụ thể là gì?",
        "Thời gian áp dụng bao lâu?",
        "Có ngoại lệ nào không?",
        "Cách phản hồi khách hàng về vấn đề này?",
        "Chính sách này áp dụng cho sản phẩm nào?",
    ],
    "troubleshooting": [
        "Nếu cách trên không khắc phục được thì sao?",
        "Liên hệ bảo hành ở đâu?",
        "Các lỗi tương tự thường gặp khác?",
        "Hướng dẫn sử dụng đúng cách để tránh lỗi?",
        "Chi phí sửa chữa nếu hết bảo hành?",
    ],
    "general": [
        "Giá sản phẩm này bao nhiêu?",
        "Tính năng nổi bật là gì?",
        "Bảo hành như thế nào?",
        "Phù hợp với nhu cầu nào?",
        "Có model nào tương tự không?",
    ],
}

# Generic fallback when no product detected
_GENERIC_TEMPLATES: dict[str, list[str]] = {
    "price_lookup": [
        "Sản phẩm này có tính năng gì nổi bật?",
        "Thông số kỹ thuật chính?",
        "So sánh với model khác trong tầm giá?",
        "Bảo hành sản phẩm này thế nào?",
    ],
    "feature_lookup": [
        "Giá sản phẩm này bao nhiêu?",
        "Thông số kỹ thuật chi tiết?",
        "Phù hợp với đối tượng nào?",
        "So sánh với model tương tự?",
    ],
    "policy": [
        "Điều kiện áp dụng cụ thể?",
        "Có ngoại lệ nào không?",
        "Thời gian áp dụng?",
        "Cách trả lời khách về vấn đề này?",
    ],
}


def generate_follow_ups(
    query: str,
    intent: str,
    detected_product: Optional[str] = None,
    max_items: int = 5,
) -> list[str]:
    """Generate follow-up questions using rule-based templates.
    
    Returns 3-5 contextual follow-up suggestions based on the detected
    intent and product. Zero token cost for all template-covered cases.
    """
    suggestions: list[str] = []

    if detected_product:
        # Use product-specific templates
        templates = _PRODUCT_TEMPLATES.get(intent, _PRODUCT_TEMPLATES["general"])
        suggestions = [t.format(product=detected_product) for t in templates]
    else:
        # Use generic templates
        templates = _GENERIC_TEMPLATES.get(intent, _PRODUCT_TEMPLATES.get(intent, _PRODUCT_TEMPLATES["general"]))
        suggestions = list(templates)

    # Filter out suggestions too similar to the original query
    query_lower = query.lower().strip()
    suggestions = [s for s in suggestions if s.lower().strip() != query_lower]

    return suggestions[:max_items]

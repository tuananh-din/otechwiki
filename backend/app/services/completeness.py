"""Completeness scoring per document type. Scores 0-100 based on expected fields."""
import re
from typing import Optional


# Expected fields per page type
EXPECTED_FIELDS = {
    "product_detail": {
        "has_title": 15,
        "has_price": 20,
        "has_description": 10,
        "has_specs": 15,
        "has_features": 10,
        "has_warranty": 10,
        "has_images_info": 5,
        "has_faq": 5,
        "content_length": 10,  # >500 chars = full points
    },
    "collection": {
        "has_title": 20,
        "has_products_list": 30,
        "has_description": 20,
        "content_length": 30,
    },
    "homepage": {
        "has_title": 20,
        "has_description": 20,
        "has_navigation": 20,
        "content_length": 40,
    },
    "other": {
        "has_title": 20,
        "has_headings": 20,
        "content_length": 60,
    },
}

# Patterns for detecting field presence
PRICE_PATTERNS = [
    re.compile(r"\d{1,3}(?:\.\d{3})+\s*₫", re.IGNORECASE),
    re.compile(r"\d{1,3}(?:,\d{3})+\s*(?:VND|đ|₫)", re.IGNORECASE),
    re.compile(r"giá\s*(?:bán|gốc|niêm yết)?\s*:?\s*\d", re.IGNORECASE),
]

SPEC_PATTERNS = [
    re.compile(r"thông số|specifications|kích thước|trọng lượng|công suất|dung tích", re.IGNORECASE),
    re.compile(r"\d+\s*(?:mm|cm|kg|W|Pa|mAh|ml|lít)", re.IGNORECASE),
]

FEATURE_PATTERNS = [
    re.compile(r"tính năng|feature|đặc điểm|nổi bật|ưu điểm", re.IGNORECASE),
]

WARRANTY_PATTERNS = [
    re.compile(r"bảo hành|warranty|chính sách đổi trả|đổi hàng", re.IGNORECASE),
]

FAQ_PATTERNS = [
    re.compile(r"câu hỏi|FAQ|hỏi đáp|thắc mắc", re.IGNORECASE),
]


def score_completeness(cleaned_text: str, page_type: Optional[str] = None) -> dict:
    """Score document completeness 0-100 based on page type expectations.
    
    Returns dict with:
      - score: int 0-100
      - fields: dict of field_name -> bool
      - missing: list of missing field names
    """
    if not cleaned_text:
        return {"score": 0, "fields": {}, "missing": []}

    page_type = page_type or "other"
    weights = EXPECTED_FIELDS.get(page_type, EXPECTED_FIELDS["other"])

    fields = {}
    score = 0

    # Universal checks
    text_lower = cleaned_text.lower()
    text_len = len(cleaned_text)
    has_headings = bool(re.search(r"^#{1,6}\s+", cleaned_text, re.MULTILINE))

    # Title check (first heading or first line)
    has_title = has_headings or (len(cleaned_text.split("\n")[0].strip()) > 5)
    fields["has_title"] = has_title
    if has_title and "has_title" in weights:
        score += weights["has_title"]

    # Content length check
    if "content_length" in weights:
        if text_len > 500:
            score += weights["content_length"]
        elif text_len > 200:
            score += weights["content_length"] // 2

    # Headings check
    if "has_headings" in weights:
        fields["has_headings"] = has_headings
        if has_headings:
            score += weights["has_headings"]

    # Product-specific checks
    if page_type == "product_detail":
        # Price
        has_price = any(p.search(cleaned_text) for p in PRICE_PATTERNS)
        fields["has_price"] = has_price
        if has_price:
            score += weights.get("has_price", 0)

        # Description (at least 100 chars of prose)
        prose_lines = [l for l in cleaned_text.split("\n") if len(l.strip()) > 50 and not l.strip().startswith("#")]
        has_description = len(prose_lines) >= 2
        fields["has_description"] = has_description
        if has_description:
            score += weights.get("has_description", 0)

        # Specs
        has_specs = any(p.search(cleaned_text) for p in SPEC_PATTERNS)
        fields["has_specs"] = has_specs
        if has_specs:
            score += weights.get("has_specs", 0)

        # Features
        has_features = any(p.search(cleaned_text) for p in FEATURE_PATTERNS)
        fields["has_features"] = has_features
        if has_features:
            score += weights.get("has_features", 0)

        # Warranty
        has_warranty = any(p.search(cleaned_text) for p in WARRANTY_PATTERNS)
        fields["has_warranty"] = has_warranty
        if has_warranty:
            score += weights.get("has_warranty", 0)

        # Images info (alt text references)
        has_images_info = "hình ảnh" in text_lower or "image" in text_lower
        fields["has_images_info"] = has_images_info
        if has_images_info:
            score += weights.get("has_images_info", 0)

        # FAQ
        has_faq = any(p.search(cleaned_text) for p in FAQ_PATTERNS)
        fields["has_faq"] = has_faq
        if has_faq:
            score += weights.get("has_faq", 0)

    elif page_type == "collection":
        # Products list (multiple product names/links)
        product_mentions = len(re.findall(r"roborock\s+\w+", text_lower))
        has_products_list = product_mentions >= 3
        fields["has_products_list"] = has_products_list
        if has_products_list:
            score += weights.get("has_products_list", 0)

        has_description = text_len > 200
        fields["has_description"] = has_description
        if has_description:
            score += weights.get("has_description", 0)

    elif page_type == "homepage":
        has_description = text_len > 300
        fields["has_description"] = has_description
        if has_description:
            score += weights.get("has_description", 0)

        has_navigation = "sản phẩm" in text_lower or "trang chủ" in text_lower
        fields["has_navigation"] = has_navigation
        if has_navigation:
            score += weights.get("has_navigation", 0)

    # Cap at 100
    score = min(score, 100)

    # Missing fields
    missing = [field for field, present in fields.items() if not present and field in weights]

    return {"score": score, "fields": fields, "missing": missing}

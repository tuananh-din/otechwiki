"""Rule-based HTML cleaning for web pages. Zero LLM tokens."""
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse


# ───────────── Blacklists ─────────────
# CSS selectors to remove entirely
REMOVE_SELECTORS = [
    "script", "style", "noscript", "iframe",
    "nav", "footer", "header",
    ".breadcrumb", ".breadcrumbs", "[class*=breadcrumb]",
    ".related-products", "[class*=related-product]", "[class*=RelatedProduct]",
    ".newsletter", "[class*=newsletter]",
    ".cookie-banner", "[class*=cookie]", "[id*=cookie]",
    ".popup", ".modal", "[class*=popup]", "[class*=modal]",
    ".social-share", "[class*=social]", "[class*=share-btn]", "[class*=share]",
    ".pagination", "[class*=pagination]",
    ".sidebar", "aside",
    "form",
    "[class*=filter]", "[class*=facet]",
    "[class*=announcement]", "[class*=banner]",
    "[class*=cart]", "[class*=wishlist]",
    "[class*=login]", "[class*=signup]",
    # Product page specific
    "[class*=swatch]", "[class*=variant]", "[class*=option-selector]",
    "[class*=color-selector]", "[class*=size-selector]",
    "[class*=review-star]", "[class*=rating]", "[class*=star-rating]",
    "[class*=product-form]", "[class*=add-to-cart]",
    "[class*=quantity]", "[class*=qty]",
    "[class*=shipping-info]", "[class*=delivery]",
    "[class*=trust-badge]", "[class*=badge]",
    "[class*=recently-viewed]", "[class*=you-may-also]",
    "[class*=blog-teaser]", "[class*=blog-card]",
    # Footer-like nav blocks
    "[class*=footer-menu]", "[class*=footer-nav]",
    "[class*=site-footer]", "[class*=mega-menu]",
]

# Text patterns to remove (exact line match after strip)
BLACKLIST_TEXT_PATTERNS = [
    r"^Chuyển đến nội dung$",
    r"^Đăng nhập$",
    r"^(Facebook|Instagram|YouTube|TikTok|Zalo)$",
    r"^Tìm kiếm$",
    r"^Xóa$",
    r"^Khám Phá$",
    r"^Translation missing:",
    r"^Trang \d+$",
    r"^Từ giá$", r"^Đến giá$",
    r"^₫$",
    r"^Mua ngay$", r"^Thêm vào giỏ$", r"^Buy now$", r"^Add to cart$",
    r"^FAQs$",
    r"^Cách Xử Lý Lỗi$",
    r"^Giúp Bạn Chọn Sản Phẩm$",
    r"^So Sánh Robot Hút Bụi$", r"^So Sánh Máy Hút Bụi$",
    r"^Tra Cứu Bảo Hành$", r"^Bảo Hành Đổi Trả$",
    r"^\d+\.\d{3}₫$",  # Price-only lines like "15.990₫"
    r"^\d+\.\d{3}\.\d{3}₫$",  # "15.990.000₫"
    r"^Bỏ qua nội dung$",
    r"^Skip to content$",
    r"^Liên hệ$",
    r"^Hotline:",
    # Ratings / review noise
    r"^\d+ đánh giá\d*$",
    r"^tổng số đánh giá$",
    r"^\d+\.\d+ đánh giá\d*$",
    r"^\d+\.\d$",  # Bare rating like "5.0"
    # Color/variant selectors
    r"^Màu sắc:?.*$",
    r"^(Đen|Trắng|Xám|Bạc|Hồng|Xanh|Vàng){2,}$",  # Repeated color names
    r"^(Đen|Trắng|Xám|Bạc|Hồng|Xanh|Vàng)$",  # Single color name
    # Share buttons
    r"^Share:?.*$",
    r"^Chia sẻ:?.*$",
    # English support/shipping text
    r"^We'll get back to you",
    r"^Shipping Information$",
    r"^Return Policy$",
    r"^within 24 hours",
    # Blog teasers
    r"^\.\.\.$",
    r"^…Đọc thêm$",
    r"^\.\.\.Đọc thêm$",
    r"^Đọc thêm$",
    r"^\d+ bình luận$",
    r"^0 bình luận$",
    r"^\d{2}/\d{2}/\d{4}$",  # Bare dates
    r"^bởi\w*$",  # "bởi" author attribution
    # Footer nav items (exact matches)
    r"^Roborock App$",
    r"^Mua Ở Đâu$",
    r"^Giới Thiệu$",
    r"^Liên Hệ$",
    r"^Hỗ trợ$",
    r"^Blog$",
    r"^Thông tin$",
    r"^Robot Hút Bụi$",
    r"^Máy Hút Bụi$",
    r"^Roborock Vietnam$",
]

# Multi-word noise patterns (substring match in line)
NOISE_SUBSTRINGS = [
    "Roborock VietnamThông tin",  # Concatenated footer
    "Share:ShareShare",
    "tổng số đánh giátổng",  # Repeated rating text
    "đánh giá24",  # Concatenated rating noise
    "đánh giá17",
    "ĐenĐen",  # Concatenated color text
    "TrắngTrắng",
    "Translation missing",
]


_blacklist_compiled = [re.compile(p, re.IGNORECASE) for p in BLACKLIST_TEXT_PATTERNS]

# Patterns for product detail pages
PRODUCT_URL_PATTERNS = [
    r"/products?/",
    r"/san-pham/",
    r"/p/",
    r"/detail/",
]

COLLECTION_URL_PATTERNS = [
    r"/collections?/",
    r"/danh-muc/",
    r"/category/",
    r"/c/",
]


def detect_page_type(url: str, html: str = "") -> str:
    """Detect page type from URL pattern."""
    path = urlparse(url).path.lower()

    for pattern in PRODUCT_URL_PATTERNS:
        if re.search(pattern, path):
            return "product_detail"

    for pattern in COLLECTION_URL_PATTERNS:
        if re.search(pattern, path):
            return "collection"

    # Homepage detection
    if path in ("", "/", "/index.html", "/home"):
        return "homepage"

    return "other"


def clean_html(html: str, page_type: str = "other") -> dict:
    """
    Rule-based HTML cleaning. Returns cleaned text + stats.
    Zero LLM tokens used.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove blacklisted selectors
    removed_count = 0
    for selector in REMOVE_SELECTORS:
        try:
            for tag in soup.select(selector):
                tag.decompose()
                removed_count += 1
        except Exception:
            continue

    # 2. Extract text with structure
    lines = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "span", "div", "article", "section"]):
        text = element.get_text(strip=True)
        if not text:
            continue

        # Apply text blacklist
        if any(pat.match(text) for pat in _blacklist_compiled):
            removed_count += 1
            continue

        # Apply noise substring check (for concatenated garbage)
        if any(ns in text for ns in NOISE_SUBSTRINGS):
            removed_count += 1
            continue

        # Skip very short noise (1-2 chars that aren't meaningful)
        if len(text) <= 2 and not text.isdigit():
            continue

        # Add heading markers for chunking
        tag_name = element.name
        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_name[1])
            prefix = "#" * level
            lines.append(f"{prefix} {text}")
        else:
            lines.append(text)

    # 3. Deduplicate consecutive identical lines
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    raw_text = "\n".join(lines)
    cleaned_text = "\n".join(deduped)

    # 4. Stats
    raw_len = len(html)
    clean_len = len(cleaned_text)
    noise_pct = round((1 - clean_len / max(raw_len, 1)) * 100, 1) if raw_len > 0 else 0

    return {
        "cleaned_text": cleaned_text,
        "raw_text": raw_text,
        "removed_blocks": removed_count,
        "noise_percent": noise_pct,
        "line_count": len(deduped),
    }


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc

"""Knowledge Extractor: GPT-based draft extraction for structured JSON.

Extracts structured records from cleaned document text:
- product_specs: spec table as JSON
- faq_pairs: Q&A from content
- pricing: price info
- compare: comparison tables

All outputs are DRAFT only. Must be reviewed + promoted via admin API.
"""
import json
import re
from pathlib import Path
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.models.document import Document, Product, document_products
from app.services.manifest import KNOWLEDGE_ROOT, register_source, log_migration, _write_json, _now_iso

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)


EXTRACT_SPECS_PROMPT = """Bạn là chuyên gia phân tích sản phẩm Roborock. Từ nội dung dưới đây, hãy trích xuất THÔNG SỐ KỸ THUẬT dưới dạng JSON.

Yêu cầu:
- Trích xuất DUY NHẤT thông tin có trong nội dung gốc
- KHÔNG bịa thêm thông số
- Giữ nguyên đơn vị đo
- Nhóm theo category

Output JSON format:
{
  "product_code": "MODEL-CODE",
  "product_name": "Roborock ...",
  "specs": [
    {"category": "Hiệu suất", "key": "Lực hút tối đa", "value": "...Pa"},
    {"category": "Pin", "key": "Dung lượng pin", "value": "...mAh"}
  ],
  "features": ["Tính năng 1", "Tính năng 2"],
  "source_confidence": "high|medium|low"
}

NỘI DUNG:
"""

EXTRACT_FAQ_PROMPT = """Từ nội dung dưới đây, trích xuất các cặp CÂU HỎI - TRẢ LỜI dưới dạng JSON.

Yêu cầu:
- Chỉ trích xuất Q&A thực sự có trong nội dung
- KHÔNG tạo câu hỏi mới
- Giữ nguyên ý nghĩa

Output JSON format:
[
  {
    "product_code": "MODEL-CODE",
    "question": "Câu hỏi?",
    "answer": "Trả lời.",
    "category": "usage|specs|troubleshoot|purchase|warranty"
  }
]

NỘI DUNG:
"""

EXTRACT_PRICING_PROMPT = """Từ nội dung dưới đây, trích xuất THÔNG TIN GIÁ dưới dạng JSON.

Output JSON format:
{
  "product_code": "MODEL-CODE",
  "product_name": "Roborock ...",
  "price": 0,
  "price_formatted": "0₫",
  "compare_price": null,
  "currency": "VND",
  "availability": "in_stock|out_of_stock|pre_order",
  "source": "shopify|web|manual"
}

NỘI DUNG:
"""


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("roborock ", "")).strip("-")


def _product_code(name: str) -> str:
    short = re.sub(r"^Roborock\s*", "", name, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", "-", short).upper()


async def extract_product_specs(
    db: AsyncSession,
    product_id: int,
) -> dict:
    """Extract product specs from cleaned text of product_detail docs. Returns draft JSON."""
    product = await db.get(Product, product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    # Get product_detail docs for this product
    docs_result = await db.execute(
        select(Document)
        .join(document_products, Document.id == document_products.c.document_id)
        .where(
            document_products.c.product_id == product_id,
            Document.page_type == "product_detail",
        )
    )
    docs = docs_result.scalars().all()

    if not docs:
        # Fallback: get any docs for this product
        docs_result = await db.execute(
            select(Document)
            .join(document_products, Document.id == document_products.c.document_id)
            .where(document_products.c.product_id == product_id)
            .limit(3)
        )
        docs = docs_result.scalars().all()

    if not docs:
        return {"error": f"No documents found for product {product.name}"}

    # Combine cleaned text from docs (limit to 6000 chars)
    combined = ""
    for doc in docs:
        text = doc.cleaned_text or doc.raw_text or ""
        if text:
            combined += f"\n--- Source: {doc.title} ---\n{text}\n"
        if len(combined) > 6000:
            combined = combined[:6000]
            break

    if not combined.strip():
        return {"error": f"No text content for product {product.name}"}

    # GPT extraction
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract structured data from product pages. Return ONLY valid JSON."},
            {"role": "user", "content": EXTRACT_SPECS_PROMPT + combined},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content
    try:
        specs_data = json.loads(raw_json)
    except json.JSONDecodeError:
        return {"error": "GPT returned invalid JSON", "raw": raw_json}

    # Enrich with known data
    product_code = _product_code(product.name)
    specs_data["product_code"] = product_code
    specs_data["product_name"] = product.name
    specs_data["extraction_model"] = "gpt-4o-mini"
    specs_data["extraction_status"] = "draft"
    specs_data["extracted_at"] = _now_iso()

    # Merge pricing from metadata if available
    meta = product.metadata_ or {}
    if meta.get("price"):
        specs_data["price"] = meta["price"]

    # Save to filesystem
    slug = _slugify(product.name)
    output_path = KNOWLEDGE_ROOT / "structured" / "product_specs" / f"{slug}.json"
    _write_json(output_path, specs_data)

    # Log migration
    log_migration(product_id, "legacy", "structured", "draft", f"Extracted specs for {product.name}")

    return {
        "product": product.name,
        "product_code": product_code,
        "output_path": str(output_path.relative_to(KNOWLEDGE_ROOT)),
        "specs_count": len(specs_data.get("specs", [])),
        "features_count": len(specs_data.get("features", [])),
        "confidence": specs_data.get("source_confidence", "unknown"),
        "status": "draft",
    }


async def extract_faq_pairs(
    db: AsyncSession,
    product_id: int,
) -> dict:
    """Extract FAQ pairs from docs mentioning this product."""
    product = await db.get(Product, product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    # Get docs with FAQ-like content
    docs_result = await db.execute(
        select(Document)
        .join(document_products, Document.id == document_products.c.document_id)
        .where(document_products.c.product_id == product_id)
        .limit(5)
    )
    docs = docs_result.scalars().all()

    combined = ""
    for doc in docs:
        text = doc.cleaned_text or doc.raw_text or ""
        if text:
            combined += f"\n--- {doc.title} ---\n{text}\n"
        if len(combined) > 6000:
            combined = combined[:6000]
            break

    if not combined.strip():
        return {"error": f"No text content for product {product.name}"}

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract FAQ pairs. Return ONLY valid JSON array."},
            {"role": "user", "content": EXTRACT_FAQ_PROMPT + combined},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content
    try:
        faq_data = json.loads(raw_json)
    except json.JSONDecodeError:
        return {"error": "GPT returned invalid JSON", "raw": raw_json}

    # Normalize: if wrapped in object, extract array
    if isinstance(faq_data, dict):
        faq_data = faq_data.get("faq_pairs", faq_data.get("faqs", [faq_data]))

    product_code = _product_code(product.name)
    for item in faq_data:
        item["product_code"] = product_code
        item["product_name"] = product.name
        item["extraction_status"] = "draft"

    slug = _slugify(product.name)
    output_path = KNOWLEDGE_ROOT / "structured" / "faq_pairs" / f"{slug}.json"
    _write_json(output_path, faq_data)

    log_migration(product_id, "legacy", "structured", "draft", f"Extracted FAQ for {product.name}")

    return {
        "product": product.name,
        "output_path": str(output_path.relative_to(KNOWLEDGE_ROOT)),
        "faq_count": len(faq_data),
        "status": "draft",
    }


async def extract_pricing(
    db: AsyncSession,
    product_id: int,
) -> dict:
    """Extract pricing from product metadata (Shopify) + docs."""
    product = await db.get(Product, product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    meta = product.metadata_ or {}
    product_code = _product_code(product.name)
    slug = _slugify(product.name)

    pricing = {
        "product_code": product_code,
        "product_name": product.name,
        "price": meta.get("price_raw", 0),
        "price_formatted": meta.get("price", "N/A"),
        "compare_price": meta.get("compare_price"),
        "currency": "VND",
        "availability": "in_stock",
        "source": "shopify" if meta.get("shopify_handle") else "manual",
        "shopify_handle": meta.get("shopify_handle"),
        "extraction_status": "draft",
        "extracted_at": _now_iso(),
    }

    output_path = KNOWLEDGE_ROOT / "structured" / "pricing" / f"{slug}.json"
    _write_json(output_path, pricing)

    return {
        "product": product.name,
        "output_path": str(output_path.relative_to(KNOWLEDGE_ROOT)),
        "price": pricing["price_formatted"],
        "source": pricing["source"],
        "status": "draft",
    }


async def batch_extract(
    db: AsyncSession,
    product_ids: list[int],
    extract_types: list[str] | None = None,
) -> list[dict]:
    """Extract structured data for multiple products."""
    if extract_types is None:
        extract_types = ["specs", "pricing", "faq"]

    results = []
    for pid in product_ids:
        product_result = {"product_id": pid, "extractions": {}}
        try:
            if "specs" in extract_types:
                product_result["extractions"]["specs"] = await extract_product_specs(db, pid)
            if "pricing" in extract_types:
                product_result["extractions"]["pricing"] = await extract_pricing(db, pid)
            if "faq" in extract_types:
                product_result["extractions"]["faq"] = await extract_faq_pairs(db, pid)
        except Exception as e:
            product_result["error"] = str(e)
        results.append(product_result)

    return results

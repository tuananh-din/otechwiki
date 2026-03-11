"""Structured lookup: direct access to canonical JSON records.

Bypasses vector search for structured data types:
- product_specs: returns spec table directly
- pricing: returns price info
- faq_pairs: returns matching Q&A
- policies: returns policy content

Used by RAG pipeline to inject high-confidence structured context.
"""
import json
import re
from pathlib import Path
from app.services.manifest import KNOWLEDGE_ROOT


STRUCTURED_DIR = KNOWLEDGE_ROOT / "structured"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("roborock ", "")).strip("-")


def _find_json_file(category: str, product_name: str) -> Path | None:
    """Find the structured JSON file for a product in a category."""
    slug = _slugify(product_name)
    candidate = STRUCTURED_DIR / category / f"{slug}.json"
    if candidate.exists():
        return candidate

    # Fuzzy match: try partial slug matches
    cat_dir = STRUCTURED_DIR / category
    if not cat_dir.exists():
        return None

    slug_parts = slug.split("-")
    for f in cat_dir.glob("*.json"):
        f_slug = f.stem
        # Check if all parts of the search slug exist in file slug
        if all(part in f_slug for part in slug_parts):
            return f

    return None


def _load_json(path: Path) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def lookup_specs(product_name: str) -> dict | None:
    """Lookup product specs from structured JSON. Returns None if not found."""
    path = _find_json_file("product_specs", product_name)
    if not path:
        return None
    data = _load_json(path)
    if not data or not isinstance(data, dict):
        return None
    if data.get("extraction_status") in ("rejected", "archived"):
        return None
    return data


def lookup_pricing(product_name: str) -> dict | None:
    """Lookup pricing from structured JSON."""
    path = _find_json_file("pricing", product_name)
    if not path:
        return None
    data = _load_json(path)
    if not data or not isinstance(data, dict):
        return None
    if data.get("extraction_status") in ("rejected", "archived"):
        return None
    return data


def lookup_faq(product_name: str) -> list | None:
    """Lookup FAQ pairs from structured JSON."""
    path = _find_json_file("faq_pairs", product_name)
    if not path:
        return None
    data = _load_json(path)
    if not data:
        return None
    # Can be list directly or wrapped
    if isinstance(data, list):
        return [d for d in data if d.get("extraction_status") not in ("rejected", "archived")]
    if isinstance(data, dict):
        return data.get("faq_pairs", data.get("faqs", [data]))
    return None


def format_specs_context(specs_data: dict) -> str:
    """Format specs JSON into a readable context block for LLM."""
    lines = []
    name = specs_data.get("product_name", "")
    lines.append(f"## Thông số kỹ thuật: {name}")

    # Price if available
    price = specs_data.get("price")
    if price:
        lines.append(f"**Giá bán:** {price}")

    # Specs table
    specs = specs_data.get("specs", [])
    if specs:
        current_cat = ""
        for s in specs:
            cat = s.get("category", "")
            if cat != current_cat:
                lines.append(f"\n### {cat}")
                current_cat = cat
            lines.append(f"- {s.get('key', '')}: {s.get('value', '')}")

    # Features
    features = specs_data.get("features", [])
    if features:
        lines.append("\n### Tính năng nổi bật")
        for f in features:
            lines.append(f"- {f}")

    confidence = specs_data.get("source_confidence", "draft")
    status = specs_data.get("extraction_status", "draft")
    lines.append(f"\n[Nguồn: structured/{status}, confidence: {confidence}]")

    return "\n".join(lines)


def format_pricing_context(pricing_data: dict) -> str:
    """Format pricing JSON into context block."""
    name = pricing_data.get("product_name", "")
    price = pricing_data.get("price_formatted", "N/A")
    compare = pricing_data.get("compare_price")
    source = pricing_data.get("source", "unknown")
    availability = pricing_data.get("availability", "unknown")

    lines = [
        f"## Giá {name}",
        f"**Giá bán:** {price}",
    ]
    if compare:
        lines.append(f"**Giá gốc:** {compare}")
    lines.append(f"**Tình trạng:** {availability}")
    lines.append(f"[Nguồn: {source}]")

    return "\n".join(lines)


def format_faq_context(faq_data: list, product_name: str = "") -> str:
    """Format FAQ pairs into context block."""
    lines = [f"## FAQ: {product_name}"]
    for item in faq_data[:10]:  # Limit to 10 FAQ pairs
        q = item.get("question", "")
        a = item.get("answer", "")
        lines.append(f"\n**Q:** {q}")
        lines.append(f"**A:** {a}")
    return "\n".join(lines)


def get_structured_context(product_name: str, intent: str) -> str | None:
    """Get relevant structured context for a product + intent.

    Returns formatted text ready for LLM injection, or None if no structured data.
    This is the main entry point used by the RAG pipeline.
    """
    blocks = []

    if intent in ("price_lookup", "specifications", "feature_lookup", "comparison", "model_recommendation"):
        # Always include pricing for price-related intents
        pricing = lookup_pricing(product_name)
        if pricing:
            blocks.append(format_pricing_context(pricing))

    if intent in ("specifications", "feature_lookup", "comparison", "model_recommendation"):
        specs = lookup_specs(product_name)
        if specs:
            blocks.append(format_specs_context(specs))

    if intent in ("general", "how_to", "troubleshooting"):
        faq = lookup_faq(product_name)
        if faq:
            blocks.append(format_faq_context(faq, product_name))

    if not blocks:
        return None

    return "\n\n---\n\n".join(blocks)

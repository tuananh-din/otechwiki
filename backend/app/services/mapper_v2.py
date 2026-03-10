"""Multi-source confidence mapping with strict variant-aware matching.

Key principle: a document about 'F25 Ace Pro' must NOT map to 'F25' base model.
Uses longest-first regex matching from product_mapper.py patterns + Shopify handle matching.
"""
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.document import Product, Document, ProductAlias, document_products


# Confidence thresholds
AUTO_APPROVE = 0.9
NEEDS_REVIEW = 0.7


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_product_name_strict(text: str) -> str | None:
    """Extract the MOST SPECIFIC product name from text using longest-first matching.

    This is the core disambiguation logic: patterns are ordered longest-first,
    so 'F25 Ace Pro' is matched before 'F25 Ace' before 'F25'.
    """
    from app.services.product_mapper import _compiled
    clean = re.sub(r"Robot Hu[tts] B[uụ]i\s*", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"^Roborock\s*", "", clean, flags=re.IGNORECASE)

    for pattern, raw in _compiled:
        if pattern.search(clean):
            name = re.sub(r"\s+", " ", raw.replace(r"\s*", " ").replace(r"\s+", " ")).strip()
            return f"Roborock {name}"
    return None


def generate_aliases(products: list[Product]) -> list[dict]:
    """Auto-generate common aliases from product names."""
    aliases = []
    for p in products:
        name = p.name  # e.g. "Roborock F25 Ace Pro"

        # 1. Without brand prefix
        short = re.sub(r"^Roborock\s*", "", name, flags=re.IGNORECASE).strip()
        if short and short != name:
            aliases.append({"product_id": p.id, "alias": short, "type": "abbreviation"})

        # 2. No spaces (e.g. "F25AcePro")
        no_space = re.sub(r"\s+", "", short)
        if no_space != short:
            aliases.append({"product_id": p.id, "alias": no_space, "type": "abbreviation"})

        # 3. Slug form (e.g. "f25-ace-pro")
        slug = re.sub(r"[^a-z0-9]+", "-", short.lower()).strip("-")
        aliases.append({"product_id": p.id, "alias": slug, "type": "slug"})

        # 4. Common Vietnamese abbreviations
        vn_name = name.replace("Roborock ", "")
        aliases.append({"product_id": p.id, "alias": f"Robot hút bụi {vn_name}", "type": "nickname"})

    return aliases


async def seed_aliases(db: AsyncSession) -> int:
    """Generate and save product aliases."""
    result = await db.execute(select(Product))
    products = result.scalars().all()

    aliases = generate_aliases(products)

    # Clear existing auto-generated aliases
    await db.execute(delete(ProductAlias).where(ProductAlias.alias_type != "manual"))

    # Insert new
    for a in aliases:
        db.add(ProductAlias(
            product_id=a["product_id"],
            alias=a["alias"],
            alias_type=a["type"],
        ))

    await db.commit()
    return len(aliases)


def _get_shopify_handle_from_url(url: str) -> str | None:
    """Extract Shopify product handle from URL.
    e.g. 'https://roborock.com.vn/products/roborock-f25-ace-pro' → 'roborock-f25-ace-pro'
    """
    if not url:
        return None
    m = re.search(r"/products/([a-z0-9\-]+)", url.lower())
    return m.group(1) if m else None


def score_mapping(
    doc: Document,
    product: Product,
    aliases: list[ProductAlias],
) -> dict | None:
    """
    Score how well a document maps to a product.
    Uses STRICT variant-aware matching to prevent cross-product contamination.

    Strategy:
    1. Shopify handle matching (URL contains product handle) → 1.0
    2. Exact product extraction from title (longest-first regex) → 1.0
    3. Exact product extraction from content (longest-first regex) → 0.7-0.8
    """
    title_norm = _normalize(doc.title)
    product_name_norm = _normalize(product.name)
    product_meta = product.metadata_ or {}
    shopify_handle = product_meta.get("shopify_handle", "")

    best_confidence = 0.0
    matched_by = ""
    reason = ""

    # === Strategy 1: Shopify handle in URL (most reliable) ===
    if shopify_handle and doc.source_url:
        doc_handle = _get_shopify_handle_from_url(doc.source_url)
        if doc_handle and doc_handle == shopify_handle:
            best_confidence = 1.0
            matched_by = "shopify_url"
            reason = f"URL handle '{doc_handle}' matches Shopify handle"

    # === Strategy 2: Exact product extraction from title ===
    if best_confidence < 1.0:
        extracted_name = _extract_product_name_strict(doc.title)
        if extracted_name:
            extracted_norm = _normalize(extracted_name)
            if extracted_norm == product_name_norm:
                best_confidence = 1.0
                matched_by = "title_exact"
                reason = f"Title extracts to '{extracted_name}' (exact match)"

    # === Strategy 3: Collection/comparison page — product mentioned in title ===
    if best_confidence < 0.8:
        # Only match if the FULL product short name appears in title as a distinct mention
        product_short = re.sub(r"^roborock\s*", "", product_name_norm).strip()
        if len(product_short) >= 3:
            # Use word boundary matching to avoid partial matches
            pattern = re.compile(
                r"\b" + re.escape(product_short) + r"\b",
                re.IGNORECASE,
            )
            if pattern.search(doc.title):
                # But verify this is the MOST SPECIFIC match for this product family
                title_extracted = _extract_product_name_strict(doc.title)
                if title_extracted and _normalize(title_extracted) == product_name_norm:
                    best_confidence = 0.85
                    matched_by = "title_contains"
                    reason = f"Title mentions '{product_short}' as primary product"

    # === Strategy 4: URL slug contains product slug ===
    if best_confidence < 0.7 and doc.source_url:
        url_norm = _normalize(doc.source_url)
        product_short = re.sub(r"^roborock\s*", "", product_name_norm).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", product_short).strip("-")
        if slug and len(slug) >= 5 and slug in url_norm:
            # Verify no longer slug also matches (e.g. "f25" vs "f25-ace-pro")
            # Check if any other product has a longer slug that also matches
            is_most_specific = True
            all_slugs = []
            for alias in aliases:
                if alias.alias_type == "slug" and alias.product_id != product.id:
                    if slug in _normalize(alias.alias) and len(alias.alias) > len(slug):
                        # A more specific product also matches this URL
                        a_slug = _normalize(alias.alias)
                        if a_slug in url_norm:
                            is_most_specific = False
                            break
            if is_most_specific:
                best_confidence = 0.7
                matched_by = "url_slug"
                reason = f"URL contains slug '{slug}'"

    # === Strategy 5: Content mention with strict extraction ===
    if best_confidence < 0.7 and doc.cleaned_text:
        # Extract product name from first 3000 chars of content
        content_prefix = doc.cleaned_text[:3000]
        content_name = _extract_product_name_strict(content_prefix)
        if content_name and _normalize(content_name) == product_name_norm:
            best_confidence = 0.7
            matched_by = "content_extract"
            reason = f"Content extracts to '{content_name}'"

    if best_confidence < NEEDS_REVIEW:
        return None

    return {
        "product_id": product.id,
        "confidence": best_confidence,
        "matched_by": matched_by,
        "reason": reason,
        "review_status": "auto" if best_confidence >= AUTO_APPROVE else "needs_review",
    }


async def map_document_v2(db: AsyncSession, doc: Document) -> list[dict]:
    """Map a document to products using strict variant-aware scoring."""
    # Get products and aliases
    products_result = await db.execute(select(Product))
    products = products_result.scalars().all()

    aliases_result = await db.execute(select(ProductAlias))
    aliases = aliases_result.scalars().all()

    mappings = []
    for product in products:
        result = score_mapping(doc, product, aliases)
        if result:
            mappings.append(result)

    # Sort by confidence descending
    mappings.sort(key=lambda x: x["confidence"], reverse=True)

    return mappings


async def apply_mappings(db: AsyncSession, doc: Document, mappings: list[dict]) -> int:
    """Save product mappings to document_products."""
    # Remove existing mappings for this doc
    await db.execute(
        delete(document_products).where(document_products.c.document_id == doc.id)
    )

    count = 0
    for m in mappings:
        await db.execute(
            document_products.insert().values(
                document_id=doc.id,
                product_id=m["product_id"],
                matched_by=m["matched_by"],
                confidence=m["confidence"],
                review_status=m["review_status"],
            )
        )
        count += 1

    await db.commit()
    return count

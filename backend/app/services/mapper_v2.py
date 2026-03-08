"""Multi-source confidence mapping with alias support."""
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
        # "Robot hút bụi X" pattern
        aliases.append({"product_id": p.id, "alias": f"Robot hút bụi {vn_name}", "type": "nickname"})

        # 5. Model number only (e.g. for S8, F25, Q8)
        model_match = re.search(r"\b([A-Z]\d+)\b", short)
        if model_match:
            model_code = model_match.group(1)
            # Only add if model code is unique enough (>= 2 chars)
            if len(model_code) >= 2:
                aliases.append({"product_id": p.id, "alias": model_code, "type": "abbreviation"})

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


def score_mapping(
    doc: Document,
    product: Product,
    aliases: list[ProductAlias],
) -> dict | None:
    """
    Score how well a document maps to a product.
    Returns {product_id, confidence, matched_by, reason} or None.
    """
    title_norm = _normalize(doc.title)
    product_name_norm = _normalize(product.name)
    product_short = _normalize(re.sub(r"^Roborock\s*", "", product.name, flags=re.IGNORECASE))

    best_confidence = 0.0
    matched_by = ""
    reason = ""

    # 1. Exact title match → 1.0
    if product_name_norm in title_norm or product_short in title_norm:
        best_confidence = 1.0
        matched_by = "title"
        reason = f"Title contains '{product.name}'"

    # 2. Alias match → 0.95
    if best_confidence < 0.95:
        product_aliases = [a for a in aliases if a.product_id == product.id]
        for alias in product_aliases:
            alias_norm = _normalize(alias.alias)
            if len(alias_norm) >= 3 and alias_norm in title_norm:
                best_confidence = max(best_confidence, 0.95)
                matched_by = "alias"
                reason = f"Title matches alias '{alias.alias}'"
                break

    # 3. URL pattern match → 0.5
    if best_confidence < 0.5 and doc.source_url:
        url_norm = _normalize(doc.source_url)
        slug = re.sub(r"[^a-z0-9]+", "-", product_short).strip("-")
        if slug and len(slug) >= 3 and slug in url_norm:
            best_confidence = max(best_confidence, 0.5)
            matched_by = "url"
            reason = f"URL contains slug '{slug}'"

    # 4. Content mention → 0.7
    if best_confidence < 0.7 and doc.cleaned_text:
        content_norm = _normalize(doc.cleaned_text[:2000])  # Check first 2000 chars
        if product_short in content_norm:
            best_confidence = max(best_confidence, 0.7)
            matched_by = "content"
            reason = f"Content mentions '{product.name}'"

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
    """Map a document to products using multi-source confidence scoring."""
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

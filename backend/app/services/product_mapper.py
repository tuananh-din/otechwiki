"""Auto-extract products from document titles and map documents to products."""
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Document, Product, document_products

# Known product model patterns for Roborock
PRODUCT_PATTERNS = [
    # Specific models first (longer matches)
    r"Saros\s*Z70",
    r"Saros\s*20\s*Sonic", r"Saros\s*20",
    r"Saros\s*10R", r"Saros\s*10",
    r"Qrevo\s*Curv\s*2\s*Pro", r"Qrevo\s*Curv\s*2\s*Flow", r"Qrevo\s*Curv\s*2",
    r"Qrevo\s*Curv", r"Qrevo\s*Edget",
    r"Qrevo\s*S\s*Pro", r"Qrevo\s*S",
    r"Qrevo\s*Maxv", r"Qrevo\s*Master", r"Qrevo\s*Pro", r"Qrevo\s*C\s*Pro", r"Qrevo",
    r"S8\s*Maxv\s*Ultra", r"S8\s*Max\s*Ultra", r"S8\s*Pro\s*Ultra", r"S8",
    r"F25\s*Ultra", r"F25\s*Ace\s*Pro", r"F25\s*Ace", r"F25",
    r"H60\s*Ultra", r"H60\s*Hub\s*Pro", r"H60",
    r"Flexi\s*Pro", r"Flexi\s*Lite", r"Flexi",
    r"Dyad\s*Pro\s*Combo", r"Dyad\s*Pro", r"Dyad\s*Air\s*Combo", r"Dyad\s*Air", r"Dyad",
    r"Q8\s*Max\+?", r"Q5\s*Pro\+?",
]

# Compile patterns
_compiled = [(re.compile(rf"\b{p}\b", re.IGNORECASE), p) for p in PRODUCT_PATTERNS]


def extract_product_name(title: str) -> str | None:
    """Extract product model name from document title."""
    # Normalize: remove common prefixes
    clean = re.sub(r"Robot Hu[tts] B[uụ]i\s*", "", title, flags=re.IGNORECASE)
    clean = re.sub(r"^Roborock\s*", "", clean, flags=re.IGNORECASE)

    for pattern, raw in _compiled:
        if pattern.search(clean):
            # Normalize the matched name
            name = re.sub(r"\s+", " ", raw.replace(r"\s*", " ").replace(r"\s+", " ")).strip()
            return f"Roborock {name}"

    return None


def slugify(name: str) -> str:
    """Convert product name to URL slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def auto_create_products(db: AsyncSession) -> list[dict]:
    """Scan document titles, extract unique products, create Product records."""
    result = await db.execute(select(Document.title))
    titles = [r[0] for r in result.all()]

    # Extract unique product names
    seen = set()
    products_to_create = []
    for title in titles:
        name = extract_product_name(title)
        if name and name not in seen:
            seen.add(name)
            products_to_create.append(name)

    # Check which already exist
    existing_result = await db.execute(select(Product.name))
    existing_names = {r[0] for r in existing_result.all()}

    created = []
    for name in sorted(products_to_create):
        if name not in existing_names:
            # Determine category
            if any(k in name.lower() for k in ["dyad", "flexi", "h60", "f25"]):
                category = "handheld"
            else:
                category = "robot"

            product = Product(name=name, slug=slugify(name), category=category)
            db.add(product)
            created.append({"name": name, "category": category})

    await db.commit()
    return created


async def auto_map_documents(db: AsyncSession) -> dict:
    """Map documents to products based on title matching."""
    # Get all products
    products_result = await db.execute(select(Product))
    products = products_result.scalars().all()

    # Get all documents
    docs_result = await db.execute(select(Document))
    docs = docs_result.scalars().all()

    # Get existing mappings
    existing_result = await db.execute(select(document_products))
    existing_pairs = {(r.document_id, r.product_id) for r in existing_result.all()}

    mapped_count = 0
    for doc in docs:
        product_name = extract_product_name(doc.title)
        if not product_name:
            continue

        # Find matching product
        matching = [p for p in products if p.name == product_name]
        if matching:
            product = matching[0]
            if (doc.id, product.id) not in existing_pairs:
                await db.execute(document_products.insert().values(
                    document_id=doc.id, product_id=product.id
                ))
                mapped_count += 1

    await db.commit()
    return {"documents_mapped": mapped_count}

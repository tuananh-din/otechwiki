"""Seed autocomplete entries from products and curated templates."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Product, AutocompleteEntry, SearchLog


# Intent templates: keyword → intent + query templates
INTENT_TEMPLATES = {
    "gia_ban": [
        "Giá {product}",
        "{product} giá bao nhiêu",
        "{product} price",
    ],
    "bao_hanh": [
        "{product} bảo hành bao lâu",
        "Bảo hành {product}",
        "Điều kiện bảo hành {product}",
    ],
    "so_sanh": [
        "{product} có gì khác",
        "So sánh {product}",
    ],
    "tinh_nang": [
        "{product} có gì nổi bật",
        "Tính năng {product}",
        "{product} tính năng chính",
    ],
    "thong_so": [
        "Thông số kỹ thuật {product}",
        "{product} specs",
    ],
    "mua_hang": [
        "Mua {product} ở đâu",
        "{product} chính hãng",
    ],
}

# General curated suggestions (not product-specific)
GENERAL_CURATED = [
    ("Roborock bảo hành bao lâu", "bao_hanh", 9),
    ("Trung tâm bảo hành Roborock ở đâu", "bao_hanh", 8),
    ("Nhà nhiều tầng nên mua con nào", "tinh_nang", 8),
    ("Robot hút bụi nào tốt nhất", "so_sanh", 8),
    ("Chính sách đổi trả Roborock", "bao_hanh", 7),
    ("Roborock có ship COD không", "mua_hang", 7),
    ("Phụ kiện Roborock chính hãng", "mua_hang", 7),
    ("Roborock khuyến mãi", "gia_ban", 8),
]

# Priority products (higher priority in autocomplete)
PRIORITY_PRODUCTS = [
    "Roborock F25", "Roborock F25 Ultra", "Roborock F25 Ace", "Roborock F25 Ace Pro",
    "Roborock Qrevo Curv", "Roborock Qrevo Curv 2", "Roborock Saros 10R", "Roborock Saros 20",
    "Roborock S8 Maxv Ultra",
]


async def seed_autocomplete(db: AsyncSession) -> dict:
    """Generate autocomplete entries from products and templates."""
    # Get all products
    result = await db.execute(select(Product.name).order_by(Product.name))
    products = [r[0] for r in result.all()]

    # Clear existing seeded entries (keep admin-edited ones if any)
    await db.execute(
        AutocompleteEntry.__table__.delete().where(
            AutocompleteEntry.category.in_(["product", "curated", "popular"])
        )
    )

    entries_created = 0

    # 1. Product name entries
    for product_name in products:
        short_name = product_name.replace("Roborock ", "")
        priority = 8 if product_name in PRIORITY_PRODUCTS else 5
        for name_variant in [product_name, short_name]:
            entry = AutocompleteEntry(
                category="product", query=name_variant,
                intent="tinh_nang", priority=priority,
            )
            db.add(entry)
            entries_created += 1

    # 2. Intent template entries
    for intent, templates in INTENT_TEMPLATES.items():
        for product_name in products:
            short_name = product_name.replace("Roborock ", "")
            priority = 7 if product_name in PRIORITY_PRODUCTS else 4
            # Only use first template per intent for non-priority products
            templates_to_use = templates if product_name in PRIORITY_PRODUCTS else templates[:1]
            for tpl in templates_to_use:
                entry = AutocompleteEntry(
                    category="curated", query=tpl.format(product=short_name),
                    intent=intent, priority=priority,
                )
                db.add(entry)
                entries_created += 1

    # 3. General curated suggestions
    for query, intent, priority in GENERAL_CURATED:
        entry = AutocompleteEntry(
            category="curated", query=query, intent=intent, priority=priority,
        )
        db.add(entry)
        entries_created += 1

    # 4. Popular queries from search logs
    popular_result = await db.execute(
        select(SearchLog.query, func.count(SearchLog.id).label("cnt"))
        .group_by(SearchLog.query)
        .having(func.count(SearchLog.id) >= 2)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
    )
    for row in popular_result.all():
        entry = AutocompleteEntry(
            category="popular", query=row[0], intent=None, priority=6,
        )
        db.add(entry)
        entries_created += 1

    await db.commit()
    return {"entries_created": entries_created, "products": len(products)}

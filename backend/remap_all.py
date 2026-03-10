"""Clear all document_products mappings and re-map using strict mapper_v2. Run inside backend container."""
import asyncio
from app.core.database import async_session
from app.models.document import Product, Document, document_products
from app.services.mapper_v2 import map_document_v2, apply_mappings, seed_aliases
from sqlalchemy import select, delete, func


async def remap_all():
    # 1. Seed aliases
    async with async_session() as db:
        alias_count = await seed_aliases(db)
        print(f"Seeded {alias_count} aliases", flush=True)

    # 2. Clear ALL existing mappings
    async with async_session() as db:
        result = await db.execute(select(func.count()).select_from(document_products))
        old_count = result.scalar()
        await db.execute(delete(document_products))
        await db.commit()
        print(f"Cleared {old_count} old mappings", flush=True)

    # 3. Get all documents
    async with async_session() as db:
        docs = (await db.execute(
            select(Document).order_by(Document.id)
        )).scalars().all()

    total = len(docs)
    print(f"\nRe-mapping {total} documents...", flush=True)
    print("=" * 80, flush=True)

    mapped_total = 0
    doc_mapped = 0
    doc_unmapped = 0

    for i, doc in enumerate(docs):
        async with async_session() as db:
            # Re-fetch doc in this session
            doc_fresh = await db.get(Document, doc.id)
            if not doc_fresh:
                continue

            mappings = await map_document_v2(db, doc_fresh)

            if mappings:
                await apply_mappings(db, doc_fresh, mappings)
                mapped_total += len(mappings)
                doc_mapped += 1
                products = ", ".join(
                    f"{m['matched_by']}:{m['confidence']:.1f}"
                    for m in mappings[:3]
                )
                print(f"[{i+1}/{total}] {doc.title[:60]} → {len(mappings)} products ({products})", flush=True)
            else:
                doc_unmapped += 1
                if (i + 1) % 50 == 0:
                    print(f"[{i+1}/{total}] ... ({doc_unmapped} unmapped so far)", flush=True)

    print("=" * 80, flush=True)
    print(f"DONE: {doc_mapped} docs mapped, {doc_unmapped} unmapped, {mapped_total} total mappings", flush=True)

    # 4. Summary: product mapping counts
    print("\n--- Product Mapping Counts ---", flush=True)
    async with async_session() as db:
        result = await db.execute(
            select(
                Product.name,
                func.count(document_products.c.document_id).label("doc_count")
            )
            .outerjoin(document_products, document_products.c.product_id == Product.id)
            .group_by(Product.id, Product.name)
            .order_by(func.count(document_products.c.document_id).desc())
        )
        for row in result.all():
            print(f"  {row.name}: {row.doc_count} docs", flush=True)


if __name__ == "__main__":
    asyncio.run(remap_all())

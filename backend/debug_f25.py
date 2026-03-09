"""Debug: check product names, aliases, and document mappings for F25 variants."""
import asyncio
from app.core.database import async_session
from sqlalchemy import text


async def debug_f25():
    async with async_session() as db:
        # 1. Products containing F25
        r = await db.execute(text(
            "SELECT id, name, slug FROM products WHERE LOWER(name) ILIKE '%f25%' ORDER BY name"
        ))
        print("=== PRODUCTS with F25 ===")
        for row in r.all():
            print(f"  id={row[0]} name={row[1]} slug={row[2]}")

        # 2. Aliases containing F25
        r2 = await db.execute(text(
            "SELECT pa.alias, p.name, p.id FROM product_aliases pa "
            "JOIN products p ON pa.product_id = p.id "
            "WHERE LOWER(pa.alias) ILIKE '%f25%' ORDER BY pa.alias"
        ))
        print("\n=== ALIASES with F25 ===")
        for row in r2.all():
            print(f"  alias={row[0]} -> product={row[1]} (id={row[2]})")

        # 3. Documents with F25 in title
        r3 = await db.execute(text(
            "SELECT d.id, d.title, d.page_type FROM documents d "
            "WHERE LOWER(d.title) ILIKE '%f25%' AND d.status = 'ready' ORDER BY d.title"
        ))
        print("\n=== DOCUMENTS with F25 ===")
        for row in r3.all():
            print(f"  id={row[0]} type={row[2]} title={row[1][:80]}")

        # 4. Document-Product mappings for F25 products
        r4 = await db.execute(text(
            "SELECT dp.document_id, d.title, p.name, dp.confidence "
            "FROM document_products dp "
            "JOIN documents d ON dp.document_id = d.id "
            "JOIN products p ON dp.product_id = p.id "
            "WHERE LOWER(p.name) ILIKE '%f25%' "
            "ORDER BY p.name, dp.confidence DESC"
        ))
        print("\n=== DOC-PRODUCT MAPPINGS for F25 ===")
        for row in r4.all():
            print(f"  doc_id={row[0]} conf={row[3]} product={row[2]} doc_title={row[1][:60]}")

        # 5. Product metadata for F25 products
        r5 = await db.execute(text(
            "SELECT name, metadata->>'price' as price FROM products "
            "WHERE LOWER(name) ILIKE '%f25%' ORDER BY name"
        ))
        print("\n=== F25 PRODUCT PRICES ===")
        for row in r5.all():
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    asyncio.run(debug_f25())

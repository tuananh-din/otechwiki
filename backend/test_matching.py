"""Test: verify 2-stage product matching returns correct product for F25."""
import asyncio
from app.core.database import async_session
from sqlalchemy import text


async def test_matching():
    async with async_session() as db:
        test_queries = ["F25", "Roborock F25", "F25 Ace Pro", "F25 Ultra", "F25 Ace"]

        for q in test_queries:
            # Stage 1: exact match
            variants = [q]
            if not q.lower().startswith("roborock"):
                variants.append(f"Roborock {q}")

            matched = None
            for v in variants:
                r = await db.execute(text(
                    "SELECT DISTINCT p.id, p.name FROM products p "
                    "LEFT JOIN product_aliases pa ON p.id = pa.product_id "
                    "WHERE LOWER(p.name) = LOWER(:q) "
                    "   OR LOWER(COALESCE(pa.alias, '')) = LOWER(:q) "
                    "LIMIT 1"
                ), {"q": v})
                row = r.first()
                if row:
                    matched = (row[0], row[1], "EXACT", v)
                    break

            # Stage 2: ILIKE fallback
            if not matched:
                r = await db.execute(text(
                    "SELECT p.id, p.name FROM products p "
                    "LEFT JOIN product_aliases pa ON p.id = pa.product_id "
                    "WHERE LOWER(p.name) ILIKE '%%' || LOWER(:q) || '%%' "
                    "   OR LOWER(COALESCE(pa.alias, '')) ILIKE '%%' || LOWER(:q) || '%%' "
                    "ORDER BY LENGTH(p.name) ASC LIMIT 1"
                ), {"q": q})
                row = r.first()
                if row:
                    matched = (row[0], row[1], "ILIKE", q)

            if matched:
                pid, pname, method, variant = matched
                print(f"  Query '{q}' -> [{method} on '{variant}'] -> id={pid} name='{pname}'")

                # Check chunk count for this product
                r2 = await db.execute(text(
                    "SELECT COUNT(*) FROM chunks c "
                    "JOIN documents d ON c.document_id = d.id "
                    "JOIN document_products dp ON d.id = dp.document_id "
                    "WHERE dp.product_id = :pid AND d.page_type = 'product_detail' "
                    "AND d.status = 'ready'"
                ), {"pid": pid})
                chunk_count = r2.scalar()
                print(f"    -> {chunk_count} product_detail chunks available")
            else:
                print(f"  Query '{q}' -> NO MATCH")

        # Also test the API endpoint directly
        print("\n=== API TEST (httpx) ===")
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            for q in ["gia F25", "tinh nang F25", "gia F25 Ultra"]:
                try:
                    r = await client.post(
                        "http://localhost:8000/api/ask",
                        json={"query": q}
                    )
                    data = r.json()
                    answer = data.get("answer", "ERROR")[:200]
                    print(f"\nQ: {q}")
                    print(f"A: {answer}")
                except Exception as e:
                    print(f"\nQ: {q} -> ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_matching())

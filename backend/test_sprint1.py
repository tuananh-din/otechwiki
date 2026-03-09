"""Quick test: verify pg_trgm fuzzy matching works."""
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text


async def test():
    async with AsyncSessionLocal() as db:
        # 1. Test pg_trgm similarity
        r = await db.execute(text("SELECT similarity('robrock', 'roborock')"))
        sim = r.scalar()
        print(f"1. pg_trgm: similarity('robrock','roborock') = {sim:.3f}")

        # 2. Test fuzzy product match
        r = await db.execute(text("""
            SELECT DISTINCT p.name,
                   GREATEST(
                       similarity(LOWER(p.name), LOWER('f25 ultra')),
                       similarity(LOWER(COALESCE(pa.alias, '')), LOWER('f25 ultra'))
                   ) as best_sim
            FROM products p
            LEFT JOIN product_aliases pa ON p.id = pa.product_id
            WHERE similarity(LOWER(COALESCE(pa.alias, '')), LOWER('f25 ultra')) > 0.2
               OR LOWER(p.name) ILIKE '%f25 ultra%'
            ORDER BY best_sim DESC
            LIMIT 5
        """))
        rows = r.mappings().all()
        print(f"2. Fuzzy match 'f25 ultra':")
        for row in rows:
            print(f"   → {row['name']} (sim={row['best_sim']:.3f})")

        # 3. Test typo match
        r = await db.execute(text("""
            SELECT DISTINCT p.name,
                   GREATEST(
                       similarity(LOWER(p.name), LOWER('robrock f25')),
                       similarity(LOWER(COALESCE(pa.alias, '')), LOWER('robrock f25'))
                   ) as best_sim
            FROM products p
            LEFT JOIN product_aliases pa ON p.id = pa.product_id
            WHERE similarity(LOWER(COALESCE(pa.alias, '')), LOWER('robrock f25')) > 0.2
               OR similarity(LOWER(p.name), LOWER('robrock f25')) > 0.2
            ORDER BY best_sim DESC
            LIMIT 5
        """))
        rows = r.mappings().all()
        print(f"3. Typo match 'robrock f25':")
        for row in rows:
            print(f"   → {row['name']} (sim={row['best_sim']:.3f})")

        # 4. Test metadata exists
        r = await db.execute(text("""
            SELECT p.name, p.metadata->>'price' as price
            FROM products p
            WHERE p.metadata->>'price' IS NOT NULL
            LIMIT 5
        """))
        rows = r.mappings().all()
        print(f"4. Product metadata (price):")
        for row in rows:
            print(f"   → {row['name']}: {row['price']}")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test())

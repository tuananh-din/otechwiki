"""Sprint 1 Migration: Enable pg_trgm extension + indexes for fuzzy search."""
import asyncio
from sqlalchemy import text
from app.core.database import async_engine


async def migrate():
    async with async_engine.begin() as conn:
        print("1. Enabling pg_trgm extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        print("   ✓ pg_trgm enabled")

        print("2. Creating trigram index on product_aliases.alias...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_product_aliases_alias_trgm
            ON product_aliases USING gin (LOWER(alias) gin_trgm_ops)
        """))
        print("   ✓ idx_product_aliases_alias_trgm created")

        print("3. Creating trigram index on products.name...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_products_name_trgm
            ON products USING gin (LOWER(name) gin_trgm_ops)
        """))
        print("   ✓ idx_products_name_trgm created")

        print("4. Setting similarity threshold...")
        await conn.execute(text("SELECT set_limit(0.3)"))
        print("   ✓ Similarity threshold set to 0.3")

    print("\n✅ Sprint 1 migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())

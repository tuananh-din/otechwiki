"""Sprint 2 migration: Add incremental pipeline columns to documents table."""
import asyncio
import sys

MIGRATION_SQL = """
-- Add incremental pipeline columns
ALTER TABLE documents ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS raw_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS clean_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS etag VARCHAR(200);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_modified_header VARCHAR(200);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS completeness_score INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS freshness_score INTEGER DEFAULT 100;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_fetched_at TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS import_status VARCHAR(20) DEFAULT 'discovered';

-- Index for canonical URL lookups
CREATE INDEX IF NOT EXISTS idx_documents_canonical_url ON documents (canonical_url);

-- Index for import status filtering
CREATE INDEX IF NOT EXISTS idx_documents_import_status ON documents (import_status);

-- Backfill canonical_url from source_url for existing records
UPDATE documents SET canonical_url = LOWER(RTRIM(SPLIT_PART(SPLIT_PART(source_url, '#', 1), '?', 1), '/'))
WHERE source_url IS NOT NULL AND canonical_url IS NULL;
"""


async def run_migration():
    from app.core.database import engine
    from sqlalchemy import text

    async with engine.begin() as conn:
        for stmt in MIGRATION_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                print(f"  Running: {stmt[:80]}...", flush=True)
                await conn.execute(text(stmt))

    print("Sprint 2 migration complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(run_migration())

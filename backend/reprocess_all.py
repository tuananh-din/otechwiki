"""Reprocess all web documents through V2 pipeline. Run inside backend container."""
import asyncio
import sys
from app.core.database import async_session
from app.models.document import Document
from app.services.ingest import ingest_web
from app.services.mapper_v2 import seed_aliases
from sqlalchemy import select


async def reprocess_all():
    # First, get list of all doc IDs to process
    async with async_session() as db:
        result = await db.execute(
            select(Document.id, Document.title, Document.source_url).where(
                Document.source_type == "web",
                Document.source_url.isnot(None),
            )
        )
        docs = [(r[0], r[1], r[2]) for r in result.all()]

    total = len(docs)
    print(f"Total web documents to reprocess: {total}", flush=True)

    success = 0
    errors = 0
    error_list = []

    for i, (doc_id, title, url) in enumerate(docs):
        # Use a fresh session per document to avoid connection pool issues
        try:
            async with async_session() as db:
                count = await ingest_web(db, doc_id, url)
                success += 1
                print(f"[{i+1}/{total}] OK: {title[:50]} -> {count} chunks", flush=True)
        except Exception as e:
            errors += 1
            err_msg = str(e)[:80]
            error_list.append(f"{title[:40]}: {err_msg}")
            print(f"[{i+1}/{total}] ERR: {title[:50]} -> {err_msg}", flush=True)

    # Seed aliases after all docs processed
    try:
        async with async_session() as db:
            alias_count = await seed_aliases(db)
    except Exception as e:
        alias_count = 0
        print(f"Alias seeding error: {e}", flush=True)

    print(f"\n{'='*50}", flush=True)
    print(f"REPROCESS COMPLETE", flush=True)
    print(f"Success: {success}/{total}", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(f"Aliases created: {alias_count}", flush=True)

    if error_list:
        print(f"\nError details:", flush=True)
        for err in error_list[:20]:
            print(f"  - {err}", flush=True)


asyncio.run(reprocess_all())

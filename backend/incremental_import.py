"""Incremental import orchestrator: discover → compare → upsert only new/changed pages."""
import asyncio
from sqlalchemy import select
from app.core.database import async_session
from app.models.document import Document
from app.services.discovery import discover_urls
from app.services.url_utils import normalize_url
from app.services.ingest import ingest_web
from urllib.parse import urlparse


async def incremental_import(
    seed_url: str,
    max_depth: int = 5,
    max_urls: int = 500,
    force_recrawl: bool = False,
):
    """Discover, compare, and upsert only new or changed pages.
    
    Returns report dict with stats.
    """
    print(f"=== Incremental Import: {seed_url} ===")
    print(f"  depth={max_depth}, max_urls={max_urls}, force={force_recrawl}")
    print()

    # 1. Discover all URLs
    print("Phase 1: Discovering URLs...")
    urls = await discover_urls(seed_url, limit=max_urls, depth=max_depth)
    print(f"  Found {len(urls)} URLs")

    # 2. Load existing canonical URLs
    print("Phase 2: Comparing with existing documents...")
    async with async_session() as db:
        result = await db.execute(
            select(Document.id, Document.canonical_url, Document.source_url, Document.raw_hash, Document.import_status)
        )
        existing = {}
        for row in result.all():
            canonical = row[1] or (normalize_url(row[2]) if row[2] else None)
            if canonical:
                existing[canonical] = {
                    "id": row[0],
                    "raw_hash": row[3],
                    "import_status": row[4],
                }

    new_urls = []
    existing_urls = []
    skipped_urls = []

    for url in urls:
        canonical = normalize_url(url)
        if canonical in existing:
            doc_info = existing[canonical]
            if force_recrawl or not doc_info["raw_hash"]:
                existing_urls.append((url, doc_info["id"]))
            else:
                skipped_urls.append(url)
        else:
            new_urls.append(url)

    print(f"  New: {len(new_urls)}")
    print(f"  Re-check: {len(existing_urls)}")
    print(f"  Skip (has hash): {len(skipped_urls)}")
    print()

    # Stats
    stats = {
        "discovered": len(urls),
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
    }

    # 3. Process new URLs
    if new_urls:
        print(f"Phase 3a: Importing {len(new_urls)} new pages...")
        for i, url in enumerate(new_urls, 1):
            try:
                async with async_session() as db:
                    parsed = urlparse(url)
                    path = parsed.path.strip("/")
                    title = path.replace("/", " - ").replace("-", " ").title() if path else "Homepage"

                    doc = Document(
                        title=title,
                        source_type="web",
                        source_url=url,
                        canonical_url=normalize_url(url),
                        document_type="company_info",
                        status="pending",
                        import_status="discovered",
                    )
                    db.add(doc)
                    await db.commit()
                    await db.refresh(doc)

                    chunks = await ingest_web(db, doc.id, url)
                    status = "new" if chunks > 0 else "empty"
                    print(f"  [{i}/{len(new_urls)}] {status}: {url} ({chunks} chunks)")
                    stats["new"] += 1
            except Exception as e:
                print(f"  [{i}/{len(new_urls)}] ERROR: {url} -> {str(e)[:80]}")
                stats["errors"] += 1

    # 4. Re-check existing URLs (hash-based skip happens inside ingest_web)
    if existing_urls:
        print(f"Phase 3b: Re-checking {len(existing_urls)} existing pages...")
        for i, (url, doc_id) in enumerate(existing_urls, 1):
            try:
                async with async_session() as db:
                    chunks = await ingest_web(db, doc_id, url)
                    if chunks == 0:
                        print(f"  [{i}/{len(existing_urls)}] unchanged: {url}")
                        stats["unchanged"] += 1
                    else:
                        print(f"  [{i}/{len(existing_urls)}] updated: {url} ({chunks} chunks)")
                        stats["updated"] += 1
            except Exception as e:
                print(f"  [{i}/{len(existing_urls)}] ERROR: {url} -> {str(e)[:80]}")
                stats["errors"] += 1

    stats["unchanged"] += len(skipped_urls)

    # 5. Auto-map new documents
    if stats["new"] > 0 or stats["updated"] > 0:
        print()
        print("Phase 4: Auto-mapping new documents...")
        try:
            async with async_session() as db:
                from app.services.product_mapper import auto_create_products, auto_map_documents
                from app.services.mapper_v2 import seed_aliases
                products = await auto_create_products(db)
                mapped = await auto_map_documents(db)
                aliases = await seed_aliases(db)
                print(f"  Products: {products}, Mapped: {mapped}, Aliases: {aliases}")
        except Exception as e:
            print(f"  Mapping error: {e}")

    # 5b. Cross-page dedup
    print()
    print("Phase 5: Cross-page dedup...")
    try:
        async with async_session() as db:
            from app.services.dedup import cross_page_dedup
            dedup_result = await cross_page_dedup(db)
            print(f"  Found {dedup_result['duplicate_hashes']} shared text blocks, marked {dedup_result['chunks_marked']} duplicate chunks")
    except Exception as e:
        print(f"  Dedup error: {e}")

    # 6. Report
    print()
    print("=" * 50)
    print(f"INCREMENTAL IMPORT COMPLETE")
    print(f"  Discovered: {stats['discovered']}")
    print(f"  New:        {stats['new']}")
    print(f"  Updated:    {stats['updated']}")
    print(f"  Unchanged:  {stats['unchanged']}")
    print(f"  Errors:     {stats['errors']}")
    print("=" * 50)

    return stats


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://roborock.com.vn"
    force = "--force" in sys.argv
    asyncio.run(incremental_import(url, force_recrawl=force))

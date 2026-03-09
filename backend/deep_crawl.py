"""Deep crawl roborock.com.vn: discover ALL subpages, compare with existing, import new ones."""
import asyncio
import sys
from urllib.parse import urlparse
from sqlalchemy import select, text
from app.core.database import async_session
from app.models.document import Document
from app.services.discovery import discover_urls
from app.services.ingest import ingest_web


SEED_URL = "https://roborock.com.vn"
MAX_DEPTH = 5
MAX_URLS = 500


async def deep_crawl():
    print(f"=== Deep Crawl: {SEED_URL} ===")
    print(f"Max depth: {MAX_DEPTH}, Max URLs: {MAX_URLS}")
    print()

    # 1. Discover all URLs
    print("Phase 1: Discovering URLs...")
    urls = await discover_urls(SEED_URL, limit=MAX_URLS, depth=MAX_DEPTH)
    print(f"  Found {len(urls)} URLs")
    for u in urls:
        print(f"    {u}")
    print()

    # 2. Get existing URLs
    print("Phase 2: Comparing with existing documents...")
    async with async_session() as db:
        result = await db.execute(select(Document.source_url))
        existing_urls = {row[0] for row in result.all() if row[0]}

    # Normalize for comparison
    def normalize(url):
        return url.rstrip("/").split("?")[0].split("#")[0].lower()

    existing_normalized = {normalize(u) for u in existing_urls}
    new_urls = [u for u in urls if normalize(u) not in existing_normalized]
    existing_count = len(urls) - len(new_urls)

    print(f"  Existing: {existing_count}")
    print(f"  New: {len(new_urls)}")
    if new_urls:
        print("  New URLs:")
        for u in new_urls:
            print(f"    + {u}")
    print()

    if not new_urls:
        print("No new URLs to import. Done!")
        return

    # 3. Import new URLs
    print(f"Phase 3: Importing {len(new_urls)} new pages...")
    success = 0
    errors = 0
    for i, url in enumerate(new_urls, 1):
        try:
            async with async_session() as db:
                # Create document record
                parsed = urlparse(url)
                path = parsed.path.strip("/")
                title = path.replace("/", " - ").replace("-", " ").title() if path else "Homepage"

                doc = Document(
                    title=title,
                    source_type="web",
                    source_url=url,
                    document_type="company_info",
                    status="pending",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)

                # Ingest through V2 pipeline
                chunks = await ingest_web(db, doc.id, url)
                print(f"  [{i}/{len(new_urls)}] OK: {url} ({chunks} chunks)")
                success += 1
        except Exception as e:
            print(f"  [{i}/{len(new_urls)}] ERROR: {url} -> {e}")
            errors += 1

    print()
    print(f"=== Done! Success: {success}, Errors: {errors} ===")

    # 4. Auto-map new documents to products
    if success > 0:
        print()
        print("Phase 4: Auto-mapping new documents to products...")
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


if __name__ == "__main__":
    asyncio.run(deep_crawl())

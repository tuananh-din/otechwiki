"""Smart recrawl policy: auto-detect stale pages and schedule re-import."""
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, func
from app.core.database import async_session
from app.models.document import Document
from app.services.ingest import ingest_web


# Default policy settings
DEFAULT_MAX_AGE_DAYS = 7          # Pages older than this are stale
DEFAULT_MIN_FRESHNESS = 60        # Pages with freshness below this need recrawl
DEFAULT_BATCH_SIZE = 50           # Max pages to recrawl per run


async def decay_freshness_scores():
    """Decay freshness scores based on time since last fetch.
    
    Score decays ~5 points per day since last fetch.
    """
    async with async_session() as db:
        now = datetime.now(timezone.utc)
        
        result = await db.execute(
            select(Document.id, Document.last_fetched_at, Document.freshness_score)
            .where(
                Document.last_fetched_at.isnot(None),
                Document.freshness_score > 0,
            )
        )
        docs = result.all()
        
        updated = 0
        for doc_id, last_fetched, current_score in docs:
            if not last_fetched:
                continue
            days_since = (now - last_fetched).days
            new_score = max(0, 100 - (days_since * 5))  # -5/day
            if new_score != current_score:
                await db.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(freshness_score=new_score)
                )
                updated += 1
        
        await db.commit()
        return {"updated": updated}


async def find_stale_pages(
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    min_freshness: int = DEFAULT_MIN_FRESHNESS,
    limit: int = DEFAULT_BATCH_SIZE,
) -> list[dict]:
    """Find pages that need recrawling."""
    async with async_session() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        
        result = await db.execute(
            select(
                Document.id,
                Document.title,
                Document.source_url,
                Document.last_fetched_at,
                Document.freshness_score,
                Document.import_status,
            )
            .where(
                Document.source_type == "web",
                Document.source_url.isnot(None),
                Document.status == "ready",
            )
            .where(
                # Either: never fetched, stale by time, or low freshness
                (Document.last_fetched_at.is_(None)) |
                (Document.last_fetched_at < cutoff) |
                (Document.freshness_score < min_freshness)
            )
            .order_by(Document.freshness_score.asc().nullsfirst())
            .limit(limit)
        )
        
        return [
            {
                "id": r[0],
                "title": r[1],
                "url": r[2],
                "last_fetched": r[3],
                "freshness": r[4],
                "status": r[5],
            }
            for r in result.all()
        ]


async def smart_recrawl(
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    min_freshness: int = DEFAULT_MIN_FRESHNESS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """Auto-recrawl stale pages. Hash-based skip in ingest_web handles unchanged content.
    
    Returns stats dict.
    """
    print("=== Smart Recrawl ===")
    
    # 1. Decay scores
    print("Phase 1: Decaying freshness scores...")
    decay_result = await decay_freshness_scores()
    print(f"  Updated {decay_result['updated']} scores")
    
    # 2. Find stale pages
    print(f"Phase 2: Finding stale pages (max_age={max_age_days}d, min_freshness={min_freshness})...")
    stale = await find_stale_pages(max_age_days, min_freshness, batch_size)
    print(f"  Found {len(stale)} stale pages")
    
    if not stale:
        print("No stale pages. Done!")
        return {"stale": 0, "updated": 0, "unchanged": 0, "errors": 0}
    
    # 3. Recrawl
    print(f"Phase 3: Recrawling {len(stale)} pages...")
    stats = {"stale": len(stale), "updated": 0, "unchanged": 0, "errors": 0}
    
    for i, page in enumerate(stale, 1):
        try:
            async with async_session() as db:
                chunks = await ingest_web(db, page["id"], page["url"])
                if chunks == 0:
                    print(f"  [{i}/{len(stale)}] unchanged: {page['title'][:50]}")
                    stats["unchanged"] += 1
                else:
                    print(f"  [{i}/{len(stale)}] updated: {page['title'][:50]} ({chunks} chunks)")
                    stats["updated"] += 1
        except Exception as e:
            print(f"  [{i}/{len(stale)}] ERROR: {page['title'][:50]} -> {str(e)[:80]}")
            stats["errors"] += 1
    
    print(f"\n=== Done! Updated: {stats['updated']}, Unchanged: {stats['unchanged']}, Errors: {stats['errors']} ===")
    return stats


if __name__ == "__main__":
    import sys
    max_age = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MAX_AGE_DAYS
    asyncio.run(smart_recrawl(max_age_days=max_age))

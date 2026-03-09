"""Analytics import reports: generate coverage and quality dashboards."""
import asyncio
from sqlalchemy import select, func
from app.core.database import async_session
from app.models.document import Document, Chunk


async def generate_import_report() -> dict:
    """Generate comprehensive import analytics report."""
    async with async_session() as db:
        # Document stats
        doc_stats = await db.execute(
            select(
                func.count(Document.id).label("total"),
                func.count(Document.id).filter(Document.status == "ready").label("ready"),
                func.count(Document.id).filter(Document.status == "error").label("errors"),
                func.avg(Document.completeness_score).label("avg_completeness"),
                func.avg(Document.freshness_score).label("avg_freshness"),
            )
        )
        doc_row = doc_stats.one()

        # By page type
        page_type_stats = await db.execute(
            select(
                Document.page_type,
                func.count(Document.id).label("count"),
                func.avg(Document.completeness_score).label("avg_completeness"),
            )
            .group_by(Document.page_type)
            .order_by(func.count(Document.id).desc())
        )
        page_types = [
            {"type": r[0] or "unknown", "count": r[1], "avg_completeness": round(r[2] or 0, 1)}
            for r in page_type_stats.all()
        ]

        # By import status
        status_stats = await db.execute(
            select(
                Document.import_status,
                func.count(Document.id).label("count"),
            )
            .group_by(Document.import_status)
        )
        import_statuses = {r[0] or "unknown": r[1] for r in status_stats.all()}

        # Chunk stats
        chunk_stats = await db.execute(
            select(
                func.count(Chunk.id).label("total"),
                func.count(Chunk.id).filter(Chunk.is_searchable == True).label("searchable"),
                func.count(Chunk.id).filter(Chunk.is_searchable == False).label("non_searchable"),
                func.avg(Chunk.token_count).label("avg_tokens"),
            )
        )
        chunk_row = chunk_stats.one()

        # Low completeness documents
        low_quality = await db.execute(
            select(Document.id, Document.title, Document.completeness_score, Document.page_type)
            .where(Document.completeness_score < 50, Document.status == "ready")
            .order_by(Document.completeness_score.asc())
            .limit(10)
        )
        low_quality_docs = [
            {"id": r[0], "title": r[1][:50], "score": r[2], "type": r[3]}
            for r in low_quality.all()
        ]

        # Documents without hashes (not yet incremental)
        no_hash = await db.execute(
            select(func.count(Document.id))
            .where(Document.raw_hash.is_(None), Document.source_type == "web")
        )
        no_hash_count = no_hash.scalar() or 0

        # Freshness distribution
        freshness_dist = await db.execute(
            select(
                func.count(Document.id).filter(Document.freshness_score >= 80).label("fresh"),
                func.count(Document.id).filter(
                    Document.freshness_score >= 50, Document.freshness_score < 80
                ).label("aging"),
                func.count(Document.id).filter(Document.freshness_score < 50).label("stale"),
            )
        )
        fresh_row = freshness_dist.one()

    report = {
        "documents": {
            "total": doc_row[0],
            "ready": doc_row[1],
            "errors": doc_row[2],
            "avg_completeness": round(doc_row[3] or 0, 1),
            "avg_freshness": round(doc_row[4] or 0, 1),
        },
        "page_types": page_types,
        "import_statuses": import_statuses,
        "chunks": {
            "total": chunk_row[0],
            "searchable": chunk_row[1],
            "non_searchable": chunk_row[2],
            "avg_tokens": round(chunk_row[3] or 0, 1),
        },
        "quality": {
            "low_quality_docs": low_quality_docs,
            "docs_without_hash": no_hash_count,
        },
        "freshness": {
            "fresh_80_100": fresh_row[0],
            "aging_50_79": fresh_row[1],
            "stale_0_49": fresh_row[2],
        },
    }

    return report


async def print_report():
    """Print formatted analytics report."""
    report = await generate_import_report()

    print("=" * 60)
    print("📊 IMPORT ANALYTICS REPORT")
    print("=" * 60)

    d = report["documents"]
    print(f"\n📄 Documents: {d['total']} total ({d['ready']} ready, {d['errors']} errors)")
    print(f"   Avg Completeness: {d['avg_completeness']}%")
    print(f"   Avg Freshness:    {d['avg_freshness']}%")

    print(f"\n📑 Page Types:")
    for pt in report["page_types"]:
        print(f"   {pt['type']:20s} {pt['count']:4d} docs  (completeness: {pt['avg_completeness']}%)")

    print(f"\n🔄 Import Status:")
    for status, count in report["import_statuses"].items():
        print(f"   {status:15s} {count:4d}")

    c = report["chunks"]
    print(f"\n📦 Chunks: {c['total']} total ({c['searchable']} searchable, {c['non_searchable']} hidden)")
    print(f"   Avg Tokens/Chunk: {c['avg_tokens']}")

    f = report["freshness"]
    print(f"\n🕐 Freshness:")
    print(f"   Fresh (80-100):  {f['fresh_80_100']}")
    print(f"   Aging (50-79):   {f['aging_50_79']}")
    print(f"   Stale (0-49):    {f['stale_0_49']}")

    q = report["quality"]
    print(f"\n⚠️  Quality Issues:")
    print(f"   Docs without hash: {q['docs_without_hash']}")
    if q["low_quality_docs"]:
        print(f"   Low quality docs ({len(q['low_quality_docs'])}):")
        for doc in q["low_quality_docs"]:
            print(f"     [{doc['score']:3d}%] {doc['title']} ({doc['type']})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(print_report())

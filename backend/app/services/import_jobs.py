"""Background import job tracker — runs bulk ingestion asynchronously with progress."""
import asyncio
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, Chunk, document_products
from app.services.ingest import ingest_web
from app.core.database import async_session


# In-memory job store (sufficient for single-instance deployment)
_jobs: dict[str, dict] = {}


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def list_jobs() -> list[dict]:
    return [{"job_id": k, "status": v["status"], "total": v["total"], "completed": v["completed"]} for k, v in _jobs.items()]


async def start_import_job(
    urls: list[str],
    document_type: str = "company_info",
    product_ids: list[int] | None = None,
    reimport: bool = True,
) -> str:
    """Start a background import job. Returns job_id."""
    job_id = str(uuid.uuid4())[:8]
    job = {
        "status": "running",
        "total": len(urls),
        "completed": 0,
        "current_url": "",
        "results": [],
        "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
    }
    _jobs[job_id] = job

    asyncio.create_task(_run_import(job_id, urls, document_type, product_ids or [], reimport))
    return job_id


async def _run_import(
    job_id: str,
    urls: list[str],
    document_type: str,
    product_ids: list[int],
    reimport: bool,
):
    job = _jobs[job_id]

    for url in urls:
        job["current_url"] = url

        async with async_session() as db:
            try:
                # Check if URL already exists
                existing_result = await db.execute(select(Document).where(Document.source_url == url))
                existing_doc = existing_result.scalar_one_or_none()

                if existing_doc:
                    if reimport:
                        # Delete old document (cascade deletes chunks)
                        await db.execute(document_products.delete().where(document_products.c.document_id == existing_doc.id))
                        await db.delete(existing_doc)
                        await db.commit()
                    else:
                        job["results"].append({"url": url, "status": "skipped", "reason": "already exists"})
                        job["completed"] += 1
                        continue

                # Create document
                parsed = urlparse(url)
                title = parsed.path.strip("/").split("/")[-1] or parsed.netloc
                title = title.replace("-", " ").replace("_", " ").title()

                doc = Document(title=title, source_type="web", source_url=url, document_type=document_type)
                db.add(doc)
                await db.commit()
                await db.refresh(doc)

                # Link to products
                if product_ids:
                    for pid in product_ids:
                        await db.execute(document_products.insert().values(document_id=doc.id, product_id=pid))
                    await db.commit()

                # Ingest
                chunks = await ingest_web(db, doc.id, url)
                job["results"].append({"url": url, "status": "success", "document_id": doc.id, "chunks": chunks})

            except Exception as e:
                job["errors"].append({"url": url, "error": str(e)})
                job["results"].append({"url": url, "status": "error", "error": str(e)})

        job["completed"] += 1

    job["status"] = "done"
    job["current_url"] = ""
    job["finished_at"] = datetime.now(timezone.utc).isoformat()

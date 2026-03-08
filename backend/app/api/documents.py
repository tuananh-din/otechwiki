import os
import shutil
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.document import Document, Chunk, Product, document_products
from app.services.ingest import ingest_web
from app.schemas.schemas import DocumentResponse, ProductResponse, ProductCreate, AnalyticsResponse
from app.services.discovery import discover_urls
from app.services.import_jobs import start_import_job, get_job

settings = get_settings()
router = APIRouter(prefix="/api", tags=["documents"])


# --- Products ---
@router.get("/products", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Product, func.count(document_products.c.document_id).label("doc_count"))
        .outerjoin(document_products, Product.id == document_products.c.product_id)
        .group_by(Product.id)
        .order_by(Product.name)
    )
    return [
        ProductResponse(
            id=p.id, name=p.name, slug=p.slug, description=p.description,
            category=p.category, image_url=p.image_url, document_count=count,
        )
        for p, count in result.all()
    ]


@router.get("/products/{slug}")
async def get_product(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.slug == slug))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    docs_result = await db.execute(
        select(Document)
        .join(document_products, Document.id == document_products.c.document_id)
        .where(document_products.c.product_id == product.id, Document.status == "ready")
    )
    docs = docs_result.scalars().all()

    return {
        "product": ProductResponse.model_validate(product),
        "documents": [DocumentResponse(
            id=d.id, title=d.title, source_type=d.source_type, source_url=d.source_url,
            document_type=d.document_type, page_count=d.page_count, status=d.status,
            created_at=d.created_at,
        ) for d in docs],
    }


@router.post("/products", response_model=ProductResponse)
async def create_product(req: ProductCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    product = Product(name=req.name, slug=req.slug, description=req.description, category=req.category)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse(id=product.id, name=product.name, slug=product.slug,
                           description=product.description, category=product.category, document_count=0)


# --- Documents ---
@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id, title=d.title, source_type=d.source_type, source_url=d.source_url,
            document_type=d.document_type, page_count=d.page_count, status=d.status,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    return {
        "document": DocumentResponse(
            id=doc.id, title=doc.title, source_type=doc.source_type, source_url=doc.source_url,
            document_type=doc.document_type, page_count=doc.page_count, status=doc.status,
            created_at=doc.created_at,
        ),
        "chunks": [{"id": c.id, "content": c.content, "page_number": c.page_number,
                     "section_title": c.section_title, "chunk_index": c.chunk_index} for c in chunks],
    }


# --- Delete Documents ---
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete product links first
    await db.execute(document_products.delete().where(document_products.c.document_id == doc_id))
    # Delete document (chunks cascade automatically)
    await db.delete(doc)
    await db.commit()

    # Remove uploaded file if exists
    if doc.source_path and os.path.exists(doc.source_path):
        os.remove(doc.source_path)

    return {"message": f"Document '{doc.title}' deleted", "id": doc_id}


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/documents/bulk-delete")
async def bulk_delete_documents(req: BulkDeleteRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    if not req.ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    # Fetch all docs to delete
    result = await db.execute(select(Document).where(Document.id.in_(req.ids)))
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found")

    deleted_ids = []
    for doc in docs:
        await db.execute(document_products.delete().where(document_products.c.document_id == doc.id))
        if doc.source_path and os.path.exists(doc.source_path):
            os.remove(doc.source_path)
        await db.delete(doc)
        deleted_ids.append(doc.id)

    await db.commit()
    return {"message": f"Deleted {len(deleted_ids)} documents", "deleted_ids": deleted_ids}


# --- Admin: Upload & Ingest ---
@router.post("/admin/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("product_spec"),
    product_ids: str = Form(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # Check duplicate title
    existing = await db.execute(select(Document).where(Document.title == title))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Document with title '{title}' already exists")

    ext = file.filename.lower().split(".")[-1]
    if ext not in ["pdf", "pptx"]:
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files accepted")

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)
    doc = Document(
        title=title, source_type=ext, source_path=file_path,
        document_type=document_type, file_size=file_size,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Link to products
    if product_ids:
        for pid in product_ids.split(","):
            pid = pid.strip()
            if pid.isdigit():
                await db.execute(document_products.insert().values(document_id=doc.id, product_id=int(pid)))
        await db.commit()

    if ext == "pdf":
        from app.services.ingest import ingest_pdf
        chunk_count = await ingest_pdf(db, doc.id, file_path)
    else:
        from app.services.ingest import ingest_ppt
        chunk_count = await ingest_ppt(db, doc.id, file_path)
        
    return {"document_id": doc.id, "chunks_created": chunk_count, "status": "ready"}

# Keep alias for backward compatibility
@router.post("/admin/upload-pdf")
async def upload_pdf_alias(*args, **kwargs):
    return await upload_document(*args, **kwargs)


@router.post("/admin/ingest-web")
async def ingest_web_page(
    url: str = Form(...),
    title: str = Form(...),
    document_type: str = Form("company_info"),
    product_ids: str = Form(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # Check duplicate URL
    existing = await db.execute(select(Document).where(Document.source_url == url))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"URL '{url}' already imported")
    doc = Document(title=title, source_type="web", source_url=url, document_type=document_type)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if product_ids:
        for pid in product_ids.split(","):
            pid = pid.strip()
            if pid.isdigit():
                await db.execute(document_products.insert().values(document_id=doc.id, product_id=int(pid)))
        await db.commit()

    chunk_count = await ingest_web(db, doc.id, url)
    return {"document_id": doc.id, "chunks_created": chunk_count, "status": "ready"}


@router.post("/admin/scan-urls")
async def scan_urls(
    homepage_url: str = Form(...),
    limit: int = Form(200),
    depth: int = Form(2),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Discover sub-pages starting from a homepage."""
    urls = await discover_urls(homepage_url, limit=limit, depth=depth)
    
    # Check which URLs already exist in DB
    existing_result = await db.execute(select(Document.source_url).where(Document.source_url.in_(urls)))
    existing_urls = set(existing_result.scalars().all())
    
    # Return list of objects with exists flag
    results = []
    for url in urls:
        results.append({
            "url": url,
            "exists": url in existing_urls
        })
    
    return results


@router.post("/admin/bulk-ingest-web")
async def bulk_ingest_web(
    urls: list[str],
    document_type: str = "company_info",
    product_ids: list[int] = [],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Ingest multiple URLs at once."""
    success_count = 0
    results = []
    
    for url in urls:
        # Final safety check against duplicates
        existing = await db.execute(select(Document).where(Document.source_url == url))
        if existing.scalar_one_or_none():
            continue
            
        try:
            # Generate a title from URL (last part or domain)
            parsed = urlparse(url)
            title = parsed.path.strip("/").split("/")[-1] or parsed.netloc
            title = title.replace("-", " ").replace("_", " ").title()
            
            doc = Document(title=title, source_type="web", source_url=url, document_type=document_type)
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            
            if product_ids:
                for pid in product_ids:
                    await db.execute(document_products.insert().values(document_id=doc.id, product_id=pid))
                await db.commit()
                
            chunks = await ingest_web(db, doc.id, url)
            results.append({"url": url, "document_id": doc.id, "chunks": chunks, "status": "success"})
            success_count += 1
        except Exception as e:
            results.append({"url": url, "error": str(e), "status": "error"})
            
    return {"processed": len(urls), "success": success_count, "details": results}


class StartImportRequest(BaseModel):
    urls: list[str]
    document_type: str = "company_info"
    product_ids: list[int] = []
    reimport: bool = True


@router.post("/admin/start-import")
async def start_import(req: StartImportRequest, admin: User = Depends(require_admin)):
    """Start background import job. Returns job_id for polling."""
    if not req.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    job_id = await start_import_job(
        urls=req.urls,
        document_type=req.document_type,
        product_ids=req.product_ids,
        reimport=req.reimport,
    )
    return {"job_id": job_id, "total": len(req.urls)}


@router.get("/admin/import-job/{job_id}")
async def get_import_status(job_id: str, admin: User = Depends(require_admin)):
    """Poll background import job progress."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# --- Autocomplete ---
@router.get("/autocomplete")
async def autocomplete(q: str = "", db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Public autocomplete — zero LLM token, DB-backed."""
    from app.services.autocomplete import search_suggestions, get_default_suggestions
    if not q.strip():
        return await get_default_suggestions(db)
    return await search_suggestions(db, q)


@router.get("/admin/autocomplete-entries")
async def list_autocomplete_entries(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from app.models.document import AutocompleteEntry
    result = await db.execute(
        select(AutocompleteEntry).where(AutocompleteEntry.active == True).order_by(AutocompleteEntry.priority.desc())
    )
    entries = result.scalars().all()
    return [{"id": e.id, "category": e.category, "query": e.query, "intent": e.intent, "priority": e.priority} for e in entries]


class BulkAutocompleteRequest(BaseModel):
    entries: list[dict]


@router.post("/admin/autocomplete-entries")
async def save_autocomplete_entries(req: BulkAutocompleteRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Bulk replace autocomplete entries from admin config."""
    from app.models.document import AutocompleteEntry
    from app.services.autocomplete import _cache
    # Delete all custom entries
    await db.execute(AutocompleteEntry.__table__.delete())
    count = 0
    for e in req.entries:
        entry = AutocompleteEntry(
            category=e.get("category", "curated"),
            query=e["query"],
            intent=e.get("intent"),
            priority=e.get("priority", 5),
            active=True,
        )
        db.add(entry)
        count += 1
    await db.commit()
    _cache.clear()
    return {"saved": count}


@router.post("/admin/seed-autocomplete")
async def seed_autocomplete_endpoint(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from app.services.seed_autocomplete import seed_autocomplete
    from app.services.autocomplete import _cache
    result = await seed_autocomplete(db)
    _cache.clear()
    return result


# --- Admin: V2 Pipeline ---


@router.post("/admin/reprocess/{document_id}")
async def reprocess_document(document_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Reprocess a single document through V2 pipeline."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.source_type != "web" or not doc.source_url:
        raise HTTPException(400, "Only web documents can be reprocessed")

    chunks_count = await ingest_web(db, document_id, doc.source_url)
    return {"document_id": document_id, "chunks": chunks_count, "status": "reprocessed"}


@router.post("/admin/reprocess-all")
async def reprocess_all(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Reprocess all web documents through V2 pipeline."""
    result = await db.execute(
        select(Document).where(Document.source_type == "web", Document.source_url.isnot(None))
    )
    docs = result.scalars().all()

    processed = 0
    errors = 0
    for doc in docs:
        try:
            await ingest_web(db, doc.id, doc.source_url)
            processed += 1
        except Exception:
            errors += 1

    # Seed aliases after reprocessing
    from app.services.mapper_v2 import seed_aliases
    alias_count = await seed_aliases(db)

    return {"processed": processed, "errors": errors, "total": len(docs), "aliases_created": alias_count}


@router.get("/admin/cleaning-stats")
async def cleaning_stats(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Get cleaning pipeline statistics."""
    # Total counts
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_chunks = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0
    searchable_chunks = (await db.execute(
        select(func.count(Chunk.id)).where(Chunk.is_searchable == True)
    )).scalar() or 0

    # Cleaning status breakdown
    cleaning_result = await db.execute(
        select(Document.cleaning_status, func.count(Document.id)).group_by(Document.cleaning_status)
    )
    cleaning_breakdown = {r[0] or "unknown": r[1] for r in cleaning_result.all()}

    # Page type breakdown
    page_type_result = await db.execute(
        select(Document.page_type, func.count(Document.id)).group_by(Document.page_type)
    )
    page_type_breakdown = {r[0] or "unknown": r[1] for r in page_type_result.all()}

    # Mapping coverage
    mapped = (await db.execute(
        select(func.count(func.distinct(document_products.c.document_id)))
    )).scalar() or 0

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "searchable_chunks": searchable_chunks,
        "non_searchable_chunks": total_chunks - searchable_chunks,
        "cleaning_breakdown": cleaning_breakdown,
        "page_type_breakdown": page_type_breakdown,
        "mapping_coverage": {
            "mapped": mapped,
            "unmapped": total_docs - mapped,
            "percentage": round(mapped / max(total_docs, 1) * 100, 1)
        }
    }


# --- Admin: Product Mapping ---
@router.post("/admin/auto-map")
async def auto_map(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Auto-extract products from document titles and map documents."""
    from app.services.product_mapper import auto_create_products, auto_map_documents
    created = await auto_create_products(db)
    mapped = await auto_map_documents(db)
    return {"products_created": len(created), "products": created, **mapped}


@router.get("/admin/product-matrix")
async def get_product_matrix(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Get product × document_type coverage matrix."""
    doc_types = ["product_spec", "faq", "manual", "comparison", "warranty", "troubleshooting", "policy", "company_info"]

    # Get all products with their documents
    products_result = await db.execute(select(Product).order_by(Product.name))
    products = products_result.scalars().all()

    matrix = []
    for product in products:
        # Get documents for this product
        docs_result = await db.execute(
            select(Document.id, Document.title, Document.document_type, Document.status)
            .join(document_products, Document.id == document_products.c.document_id)
            .where(document_products.c.product_id == product.id, Document.status == "ready")
        )
        docs = docs_result.all()

        # Build coverage map
        coverage = {}
        doc_details = {}
        for d in docs:
            dt = d.document_type or "company_info"
            coverage[dt] = coverage.get(dt, 0) + 1
            if dt not in doc_details:
                doc_details[dt] = []
            doc_details[dt].append({"id": d.id, "title": d.title})

        # Calculate chunks
        chunk_count_result = await db.execute(
            select(func.count(Chunk.id))
            .join(Document, Chunk.document_id == Document.id)
            .join(document_products, Document.id == document_products.c.document_id)
            .where(document_products.c.product_id == product.id)
        )
        total_chunks = chunk_count_result.scalar() or 0

        matrix.append({
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "category": product.category,
            "coverage": {dt: coverage.get(dt, 0) for dt in doc_types},
            "doc_details": doc_details,
            "total_docs": len(docs),
            "total_chunks": total_chunks,
            "coverage_score": sum(1 for dt in doc_types if coverage.get(dt, 0) > 0),
        })

    # Count unmapped docs
    mapped_ids_result = await db.execute(select(document_products.c.document_id).distinct())
    mapped_ids = {r[0] for r in mapped_ids_result.all()}
    total_docs_result = await db.execute(select(func.count(Document.id)).where(Document.status == "ready"))
    total_docs = total_docs_result.scalar() or 0
    unmapped = total_docs - len(mapped_ids)

    return {
        "products": sorted(matrix, key=lambda x: -x["coverage_score"]),
        "unmapped_docs": unmapped,
        "total_docs": total_docs,
        "doc_types": doc_types,
    }


# --- Admin: Analytics ---
@router.get("/admin/analytics", response_model=AnalyticsResponse)
async def get_analytics(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from app.models.document import SearchLog

    total_searches = (await db.execute(select(func.count(SearchLog.id)))).scalar() or 0
    total_documents = (await db.execute(select(func.count(Document.id)).where(Document.status == "ready"))).scalar() or 0
    total_chunks = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0

    # Top queries
    top_q = await db.execute(
        select(SearchLog.query, func.count(SearchLog.id).label("count"))
        .group_by(SearchLog.query)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
    )
    top_queries = [{"query": q, "count": c} for q, c in top_q.all()]

    # No-result queries
    no_res = await db.execute(
        select(SearchLog.query, func.count(SearchLog.id).label("count"))
        .where(SearchLog.results_count == 0)
        .group_by(SearchLog.query)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
    )
    no_result_queries = [{"query": q, "count": c} for q, c in no_res.all()]

    # Searches by day (last 30 days)
    daily = await db.execute(
        select(func.date_trunc("day", SearchLog.created_at).label("day"), func.count(SearchLog.id).label("count"))
        .group_by("day")
        .order_by("day")
        .limit(30)
    )
    searches_by_day = [{"date": d.isoformat(), "count": c} for d, c in daily.all()]

    return AnalyticsResponse(
        total_searches=total_searches, total_documents=total_documents, total_chunks=total_chunks,
        top_queries=top_queries, no_result_queries=no_result_queries, searches_by_day=searches_by_day,
    )

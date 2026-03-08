from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.embeddings import get_embedding
from app.services.query_understanding import analyze_query
from app.core.config import get_settings

settings = get_settings()


async def hybrid_search(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    product_filter: str | None = None,
    doc_type_filter: str | None = None,
) -> list[dict]:
    """
    Hybrid search combining keyword (full-text) and semantic (vector) search.
    Uses Reciprocal Rank Fusion (RRF) to merge results.
    """
    # 0. Analyze query for intent and expansion
    analysis = await analyze_query(query)
    
    # 1. Generate embedding for original query
    query_embedding = await get_embedding(query)

    # 2. Build filter conditions
    filters = []
    # Use expanded keywords for text search, original for vector
    keywords_str = " | ".join(analysis.expanded_keywords)
    params = {
        "query": query, 
        "keywords": keywords_str,
        "embedding": str(query_embedding), 
        "limit": limit
    }

    if product_filter:
        filters.append("p.slug = :product_filter")
        params["product_filter"] = product_filter
    if doc_type_filter:
        filters.append("d.document_type = :doc_type_filter")
        params["doc_type_filter"] = doc_type_filter

    filter_join = ""
    filter_where = ""
    if product_filter:
        filter_join = "JOIN document_products dp ON d.id = dp.document_id JOIN products p ON dp.product_id = p.id"
    if filters:
        filter_where = "AND " + " AND ".join(filters)

    sql = text(f"""
        WITH keyword_results AS (
            SELECT c.id, COALESCE(c.cleaned_content, c.content) as content,
                   c.document_id, c.page_number, c.section_title,
                   d.title as document_title, d.source_type,
                   ts_rank(to_tsvector('simple', COALESCE(c.cleaned_content, c.content)), plainto_tsquery('simple', :query)) as kw_score,
                   ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('simple', COALESCE(c.cleaned_content, c.content)), plainto_tsquery('simple', :query)) DESC) as kw_rank
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            {filter_join}
            WHERE d.status = 'ready'
              AND (c.is_searchable = true OR c.is_searchable IS NULL)
              AND to_tsvector('simple', COALESCE(c.cleaned_content, c.content)) @@ plainto_tsquery('simple', :keywords)
              {filter_where}
            LIMIT 20
        ),
        semantic_results AS (
            SELECT c.id, COALESCE(c.cleaned_content, c.content) as content,
                   c.document_id, c.page_number, c.section_title,
                   d.title as document_title, d.source_type,
                   1 - (c.embedding <=> CAST(:embedding AS vector)) as sem_score,
                   ROW_NUMBER() OVER (ORDER BY c.embedding <=> CAST(:embedding AS vector)) as sem_rank
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            {filter_join}
            WHERE d.status = 'ready'
              AND (c.is_searchable = true OR c.is_searchable IS NULL)
              AND c.embedding IS NOT NULL
              {filter_where}
            LIMIT 20
        ),
        combined AS (
            SELECT
                COALESCE(k.id, s.id) as id,
                COALESCE(k.content, s.content) as content,
                COALESCE(k.document_id, s.document_id) as document_id,
                COALESCE(k.document_title, s.document_title) as document_title,
                COALESCE(k.source_type, s.source_type) as source_type,
                COALESCE(k.page_number, s.page_number) as page_number,
                COALESCE(k.section_title, s.section_title) as section_title,
                COALESCE(1.0 / (60 + k.kw_rank), 0) + COALESCE(1.0 / (60 + s.sem_rank), 0) as rrf_score
            FROM keyword_results k
            FULL OUTER JOIN semantic_results s ON k.id = s.id
        )
        SELECT * FROM combined
        ORDER BY rrf_score DESC
        LIMIT :limit
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "score": float(row["rrf_score"]),
            "document_id": row["document_id"],
            "document_title": row["document_title"],
            "source_type": row["source_type"],
            "page_number": row["page_number"],
            "section_title": row["section_title"],
        }
        for row in rows
    ]


async def keyword_search(db: AsyncSession, query: str, limit: int = 10) -> list[dict]:
    """Pure keyword search using PostgreSQL full-text search."""
    sql = text("""
        SELECT c.id, COALESCE(c.cleaned_content, c.content) as content,
               c.document_id, c.page_number, c.section_title,
               d.title as document_title, d.source_type,
               ts_rank(to_tsvector('simple', COALESCE(c.cleaned_content, c.content)), plainto_tsquery('simple', :query)) as score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.status = 'ready'
          AND (c.is_searchable = true OR c.is_searchable IS NULL)
          AND to_tsvector('simple', COALESCE(c.cleaned_content, c.content)) @@ plainto_tsquery('simple', :query)
        ORDER BY score DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"query": query, "limit": limit})
    return [dict(row) for row in result.mappings().all()]

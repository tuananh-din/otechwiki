from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import SearchLog
from app.services.search import hybrid_search, keyword_search
from app.services.rag import ask_with_rag
from app.schemas.schemas import SearchRequest, SearchResponse, ChunkResult, AskRequest, AskResponse, Citation
from sqlalchemy import select

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if req.search_type == "keyword":
        results = await keyword_search(db, req.query, req.limit)
    else:
        results = await hybrid_search(db, req.query, req.limit, req.product_filter, req.doc_type_filter)

    # Log search
    log = SearchLog(user_id=user.id, query=req.query, search_type=req.search_type, results_count=len(results))
    db.add(log)
    await db.commit()

    return SearchResponse(
        query=req.query,
        results=[ChunkResult(**r) for r in results],
        total=len(results),
    )


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await ask_with_rag(db, req.query, req.product_filter, req.doc_type_filter)

    # Log
    log = SearchLog(
        user_id=user.id, query=req.query, search_type="rag", results_count=len(result["citations"]),
        had_ai_answer=not result["no_result"],
    )
    db.add(log)
    await db.commit()

    return AskResponse(
        query=req.query,
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        no_result=result["no_result"],
    )


@router.get("/recent-searches")
async def recent_searches(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(SearchLog)
        .where(SearchLog.user_id == user.id)
        .order_by(SearchLog.created_at.desc())
        .limit(20)
    )
    logs = result.scalars().all()
    return [{"query": l.query, "type": l.search_type, "created_at": l.created_at.isoformat()} for l in logs]

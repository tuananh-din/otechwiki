"""Deduplication at URL, block, and chunk levels."""
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document


def text_hash(text: str) -> str:
    """SHA256 hash of normalized text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def dedup_url(db: AsyncSession, url: str) -> Document | None:
    """Check if URL already imported. Returns existing doc or None."""
    clean_url = url.rstrip("/")
    result = await db.execute(
        select(Document).where(
            Document.source_url.ilike(f"%{clean_url}%"),
            Document.status == "ready"
        ).limit(1)
    )
    return result.scalar_one_or_none()


def dedup_blocks(text: str, min_block_len: int = 30) -> str:
    """Remove repeated text blocks within the same document."""
    lines = text.split("\n")
    seen_hashes = set()
    result = []

    for line in lines:
        stripped = line.strip()
        if len(stripped) < min_block_len:
            # Keep short lines (headings, bullets) without dedup
            result.append(line)
            continue

        h = text_hash(stripped)
        if h not in seen_hashes:
            seen_hashes.add(h)
            result.append(line)
        # else: skip duplicate block

    return "\n".join(result)


def dedup_chunks(chunks: list[dict]) -> list[dict]:
    """
    Flag duplicate chunks by dedup_hash.
    Chunks with duplicate hashes get is_searchable=False.
    """
    seen = set()
    for chunk in chunks:
        h = chunk.get("dedup_hash", "")
        if h in seen:
            chunk["is_searchable"] = False
        else:
            seen.add(h)
            chunk["is_searchable"] = True
    return chunks


async def cross_page_dedup(db: AsyncSession, min_occurrences: int = 3) -> dict:
    """Find chunks that appear in multiple documents and mark duplicates.
    
    Shared text (warranty, shipping, etc.) is kept searchable in ONE document
    and marked non-searchable in all others.
    
    Returns stats dict.
    """
    from app.models.document import Chunk
    from sqlalchemy import func, update

    # Find dedup_hashes that appear in chunks from multiple documents
    result = await db.execute(
        select(
            Chunk.dedup_hash,
            func.count(func.distinct(Chunk.document_id)).label("doc_count"),
            func.count(Chunk.id).label("chunk_count"),
        )
        .where(Chunk.dedup_hash.isnot(None), Chunk.is_searchable == True)
        .group_by(Chunk.dedup_hash)
        .having(func.count(func.distinct(Chunk.document_id)) >= min_occurrences)
    )
    duplicates = result.all()

    total_marked = 0
    for dup_hash, doc_count, chunk_count in duplicates:
        # Get all chunk IDs with this hash, ordered by document_id
        chunk_result = await db.execute(
            select(Chunk.id, Chunk.document_id)
            .where(Chunk.dedup_hash == dup_hash, Chunk.is_searchable == True)
            .order_by(Chunk.document_id)
        )
        chunks = chunk_result.all()
        
        if len(chunks) <= 1:
            continue

        # Keep the first chunk searchable, mark the rest as non-searchable
        ids_to_mark = [c[0] for c in chunks[1:]]
        if ids_to_mark:
            await db.execute(
                update(Chunk)
                .where(Chunk.id.in_(ids_to_mark))
                .values(is_searchable=False)
            )
            total_marked += len(ids_to_mark)

    await db.commit()
    return {
        "duplicate_hashes": len(duplicates),
        "chunks_marked": total_marked,
    }


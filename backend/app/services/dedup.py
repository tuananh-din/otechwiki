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

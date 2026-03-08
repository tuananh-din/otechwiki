"""Autocomplete search suggestions — zero LLM token, DB-backed with LRU cache."""
import time
import unicodedata
import re
from collections import OrderedDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from app.models.document import AutocompleteEntry


# --- In-memory LRU Cache ---
class LRUCache:
    def __init__(self, max_size: int = 128, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[float, list]] = OrderedDict()

    def get(self, key: str) -> list | None:
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < self.ttl:
                self._cache.move_to_end(key)
                return value
            else:
                del self._cache[key]
        return None

    def put(self, key: str, value: list):
        self._cache[key] = (time.time(), value)
        self._cache.move_to_end(key)
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()


_cache = LRUCache(max_size=128, ttl=300)


def normalize_query(q: str) -> str:
    """Normalize: lowercase, strip accents, collapse whitespace."""
    q = q.lower().strip()
    # Remove Vietnamese accents for matching
    nfkd = unicodedata.normalize("NFKD", q)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip()


async def search_suggestions(db: AsyncSession, query: str, limit: int = 8) -> list[dict]:
    """Search autocomplete entries using unaccent + ILIKE prefix/substring matching."""
    if not query or not query.strip():
        return []

    q_normalized = query.strip().lower()
    cache_key = q_normalized

    # Check cache
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # Use PostgreSQL unaccent for accent-insensitive matching
    # Priority: prefix match first, then substring match
    sql = text("""
        SELECT id, category, query, intent, priority
        FROM autocomplete_entries
        WHERE active = true
          AND unaccent(lower(query)) LIKE unaccent(lower(:prefix_pattern))
        ORDER BY
          CASE WHEN unaccent(lower(query)) LIKE unaccent(lower(:exact_prefix)) THEN 0 ELSE 1 END,
          priority DESC,
          length(query) ASC
        LIMIT :lim
    """)

    result = await db.execute(sql, {
        "prefix_pattern": f"%{q_normalized}%",
        "exact_prefix": f"{q_normalized}%",
        "lim": limit,
    })
    rows = result.all()

    suggestions = [
        {"query": r[2], "category": r[1], "intent": r[3]}
        for r in rows
    ]

    # Cache results
    _cache.put(cache_key, suggestions)
    return suggestions


async def get_default_suggestions(db: AsyncSession, limit: int = 8) -> list[dict]:
    """Return popular/curated suggestions for empty input (on focus)."""
    cache_key = "__default__"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(AutocompleteEntry.query, AutocompleteEntry.category, AutocompleteEntry.intent)
        .where(AutocompleteEntry.active == True, AutocompleteEntry.category.in_(["curated", "popular"]))
        .order_by(AutocompleteEntry.priority.desc())
        .limit(limit)
    )
    rows = result.all()
    suggestions = [{"query": r[0], "category": r[1], "intent": r[2]} for r in rows]
    _cache.put(cache_key, suggestions)
    return suggestions

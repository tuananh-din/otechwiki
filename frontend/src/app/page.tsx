"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Search, Clock, ArrowRight, TrendingUp } from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  product: "Sản phẩm",
  curated: "Gợi ý",
  popular: "Phổ biến",
  faq: "FAQ",
};

const CATEGORY_ICONS: Record<string, typeof Search> = {
  product: Search,
  curated: TrendingUp,
  popular: TrendingUp,
};

// Client-side suggestion cache
const _clientCache = new Map<string, { ts: number; data: any[] }>();
const CACHE_TTL = 60_000; // 1 min

function getCached(key: string): any[] | null {
  const entry = _clientCache.get(key);
  if (entry && Date.now() - entry.ts < CACHE_TTL) return entry.data;
  _clientCache.delete(key);
  return null;
}
function setCache(key: string, data: any[]) {
  _clientCache.set(key, { ts: Date.now(), data });
  if (_clientCache.size > 64) {
    const oldest = _clientCache.keys().next().value;
    if (oldest) _clientCache.delete(oldest);
  }
}

function highlightMatch(text: string, query: string) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <strong style={{ color: "var(--color-primary)", fontWeight: 700 }}>{text.slice(idx, idx + query.length)}</strong>
      {text.slice(idx + query.length)}
    </>
  );
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [recentSearches, setRecentSearches] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);

  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Load recent searches on mount
  useEffect(() => {
    api.recentSearches().then(setRecentSearches).catch(() => {});
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Fetch suggestions with debounce
  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      return;
    }
    const key = q.trim().toLowerCase();
    const cached = getCached(key);
    if (cached) {
      setSuggestions(cached);
      setActiveIndex(-1);
      return;
    }
    setLoading(true);
    try {
      const data = await api.autocomplete(q);
      setSuggestions(data);
      setCache(key, data);
      setActiveIndex(-1);
    } catch { setSuggestions([]); }
    finally { setLoading(false); }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    setShowDropdown(true);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(val), 200);
  };

  const handleSearch = (searchQuery?: string) => {
    const q = (searchQuery || query).trim();
    if (!q) return;
    setShowDropdown(false);
    router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeIndex >= 0 && activeIndex < suggestions.length) {
      handleSearch(suggestions[activeIndex].query);
    } else {
      handleSearch();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return;
    const items = query.trim() ? suggestions : recentSearches;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex(prev => Math.min(prev + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      const item = items[activeIndex];
      handleSearch(item.query);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  };

  const handleFocus = () => {
    setShowDropdown(true);
    if (!query.trim() && recentSearches.length === 0) {
      // Load default curated suggestions
      const cached = getCached("__default__");
      if (cached) { setSuggestions(cached); return; }
      api.autocomplete("").then(data => {
        setSuggestions(data);
        setCache("__default__", data);
      }).catch(() => {});
    }
  };

  // Determine what to show in dropdown
  const showRecent = !query.trim() && recentSearches.length > 0;
  const dropdownItems = showRecent ? recentSearches : suggestions;
  const hasItems = dropdownItems.length > 0;

  return (
    <AppLayout>
      <div style={{ maxWidth: 720, margin: "0 auto", paddingTop: "6vh", textAlign: "center" }}>
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: "linear-gradient(135deg, var(--color-primary), var(--color-secondary))",
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto 1.25rem", color: "white",
        }}>
          <Search size={28} />
        </div>

        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
          Tra cứu kiến thức sản phẩm
        </h1>
        <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem", fontSize: "0.9375rem" }}>
          Nhập câu hỏi hoặc từ khóa để tìm kiếm thông tin nhanh
        </p>

        <form onSubmit={handleSubmit} style={{ position: "relative" }}>
          <div className="search-bar-wrapper" style={{ margin: "0 auto" }}>
            <div className="search-bar-icon"><Search size={20} /></div>
            <input
              ref={inputRef}
              className="search-bar"
              type="text"
              value={query}
              onChange={handleInputChange}
              onFocus={handleFocus}
              onKeyDown={handleKeyDown}
              placeholder="Ví dụ: Roborock F25 có bảo hành bao lâu?"
              autoFocus
              autoComplete="off"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {showDropdown && hasItems && (
            <div
              ref={dropdownRef}
              style={{
                position: "absolute", top: "100%", left: 0, right: 0,
                marginTop: 4, background: "white", borderRadius: "var(--radius-md)",
                border: "1px solid var(--color-border)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
                zIndex: 100, overflow: "hidden", textAlign: "left",
                maxHeight: 400, overflowY: "auto",
              }}
            >
              {/* Section header */}
              {showRecent && (
                <div style={{
                  padding: "0.5rem 0.875rem 0.25rem", fontSize: "0.6875rem",
                  fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em",
                  color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "0.375rem",
                }}>
                  <Clock size={12} /> Tìm kiếm gần đây
                </div>
              )}
              {!showRecent && suggestions.length > 0 && (
                <div style={{
                  padding: "0.5rem 0.875rem 0.25rem", fontSize: "0.6875rem",
                  fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em",
                  color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "0.375rem",
                }}>
                  <Search size={12} /> Gợi ý tìm kiếm
                </div>
              )}

              {dropdownItems.map((item, i) => {
                const isActive = i === activeIndex;
                const Icon = CATEGORY_ICONS[item.category] || Search;
                return (
                  <div
                    key={`${item.query}-${i}`}
                    onMouseDown={(e) => { e.preventDefault(); handleSearch(item.query); }}
                    onMouseEnter={() => setActiveIndex(i)}
                    style={{
                      padding: "0.625rem 0.875rem",
                      display: "flex", alignItems: "center", gap: "0.625rem",
                      cursor: "pointer", fontSize: "0.875rem",
                      background: isActive ? "var(--color-primary-light)" : "transparent",
                      transition: "background 0.1s",
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, borderRadius: "var(--radius-sm)",
                      background: isActive ? "var(--color-primary)" : "var(--color-surface-hover)",
                      color: isActive ? "white" : "var(--color-text-muted)",
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}>
                      {showRecent ? <Clock size={14} /> : <Icon size={14} />}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: isActive ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {showRecent ? item.query : highlightMatch(item.query, query)}
                      </div>
                    </div>
                    {item.category && !showRecent && (
                      <span style={{
                        fontSize: "0.6875rem", padding: "0.125rem 0.5rem",
                        borderRadius: 12, background: "var(--color-surface-hover)",
                        color: "var(--color-text-muted)", flexShrink: 0,
                      }}>
                        {CATEGORY_LABELS[item.category] || item.category}
                      </span>
                    )}
                    <ArrowRight size={14} style={{ color: "var(--color-text-muted)", flexShrink: 0, opacity: isActive ? 1 : 0.3 }} />
                  </div>
                );
              })}

              {/* Search raw query */}
              {query.trim() && (
                <div
                  onMouseDown={(e) => { e.preventDefault(); handleSearch(); }}
                  style={{
                    padding: "0.625rem 0.875rem", borderTop: "1px solid var(--color-border)",
                    display: "flex", alignItems: "center", gap: "0.625rem",
                    cursor: "pointer", fontSize: "0.8125rem", color: "var(--color-primary)",
                    fontWeight: 500,
                  }}
                >
                  <Search size={14} />
                  Tìm kiếm với: &quot;{query}&quot;
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary btn-lg" type="submit">
              <Search size={18} />
              <span>Tìm kiếm</span>
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
}

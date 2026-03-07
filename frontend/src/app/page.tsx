"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Search, Clock, ArrowRight } from "lucide-react";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState<any[]>([]);
  const router = useRouter();

  useEffect(() => {
    api.recentSearches().then(setRecentSearches).catch(() => {});
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

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

        <form onSubmit={handleSearch}>
          <div className="search-bar-wrapper" style={{ margin: "0 auto" }}>
            <div className="search-bar-icon"><Search size={20} /></div>
            <input
              className="search-bar"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ví dụ: Máy giặt LG có bảo hành bao lâu?"
              autoFocus
            />
          </div>
          <div style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary btn-lg" type="submit">
              <Search size={18} />
              <span>Tìm kiếm</span>
            </button>
          </div>
        </form>

        {recentSearches.length > 0 && (
          <div style={{ marginTop: "3rem", textAlign: "left" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <Clock size={16} style={{ color: "var(--color-text-muted)" }} />
              <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 500 }}>
                Tìm kiếm gần đây
              </span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {recentSearches.slice(0, 8).map((s, i) => (
                <button
                  key={i}
                  className="btn btn-ghost btn-sm"
                  onClick={() => router.push(`/search?q=${encodeURIComponent(s.query)}`)}
                >
                  {s.query}
                  <ArrowRight size={14} />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

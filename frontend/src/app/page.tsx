"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";

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
      <div style={{ maxWidth: 800, margin: "0 auto", paddingTop: "8vh", textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.5rem" }}>
          Tra cứu kiến thức sản phẩm
        </h1>
        <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
          Nhập câu hỏi hoặc từ khóa để tìm kiếm thông tin nhanh
        </p>

        <form onSubmit={handleSearch}>
          <input
            className="search-bar"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ví dụ: Máy giặt LG có bảo hành bao lâu?"
            autoFocus
          />
          <div style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary" type="submit" style={{ padding: "0.75rem 2rem" }}>
              🔍 Tìm kiếm
            </button>
          </div>
        </form>

        {recentSearches.length > 0 && (
          <div style={{ marginTop: "3rem", textAlign: "left" }}>
            <h3 style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
              🕐 Tìm kiếm gần đây
            </h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {recentSearches.slice(0, 8).map((s, i) => (
                <button
                  key={i}
                  className="btn btn-ghost"
                  onClick={() => router.push(`/search?q=${encodeURIComponent(s.query)}`)}
                  style={{ fontSize: "0.8125rem" }}
                >
                  {s.query}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

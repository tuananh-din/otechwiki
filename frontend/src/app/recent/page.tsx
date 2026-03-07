"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";

export default function RecentPage() {
  const [searches, setSearches] = useState<any[]>([]);
  useEffect(() => { api.recentSearches().then(setSearches).catch(() => {}); }, []);

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>🕐 Tìm kiếm gần đây</h1>
      {searches.length === 0 ? (
        <div className="no-result"><div className="no-result-icon">🕐</div>Chưa có lịch sử tìm kiếm</div>
      ) : (
        <div>
          {searches.map((s, i) => (
            <a key={i} href={`/search?q=${encodeURIComponent(s.query)}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="result-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 500 }}>{s.query}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                  {new Date(s.created_at).toLocaleString("vi")}
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

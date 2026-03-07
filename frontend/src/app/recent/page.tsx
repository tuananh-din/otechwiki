"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Clock, ArrowRight, Search as SearchIcon } from "lucide-react";

export default function RecentPage() {
  const [searches, setSearches] = useState<any[]>([]);
  useEffect(() => { api.recentSearches().then(setSearches).catch(() => {}); }, []);

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Tìm kiếm gần đây</h1>
        <p>Lịch sử các truy vấn tìm kiếm của bạn</p>
      </div>

      {searches.length === 0 ? (
        <div className="empty-state">
          <Clock size={48} />
          <p>Chưa có lịch sử tìm kiếm</p>
        </div>
      ) : (
        <div>
          {searches.map((s, i) => (
            <a key={i} href={`/search?q=${encodeURIComponent(s.query)}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="result-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                  <SearchIcon size={16} style={{ color: "var(--color-text-muted)" }} />
                  <span style={{ fontWeight: 500 }}>{s.query}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                    {new Date(s.created_at).toLocaleString("vi")}
                  </span>
                  <ArrowRight size={14} style={{ color: "var(--color-text-muted)" }} />
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

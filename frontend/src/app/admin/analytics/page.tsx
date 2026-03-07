"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";

export default function AdminAnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(() => { api.getAnalytics().then(setAnalytics).catch(() => {}); }, []);

  if (!analytics) return <AppLayout><div className="spinner" /></AppLayout>;

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>📈 Analytics</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <div className="stat-card"><div className="stat-value">{analytics.total_searches}</div><div className="stat-label">Tổng tìm kiếm</div></div>
        <div className="stat-card"><div className="stat-value">{analytics.total_documents}</div><div className="stat-label">Tài liệu</div></div>
        <div className="stat-card"><div className="stat-value">{analytics.total_chunks}</div><div className="stat-label">Đoạn nội dung</div></div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>📊 Lượt tìm kiếm theo ngày</h3>
        {analytics.searches_by_day.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Chưa có dữ liệu</p>
        ) : (
          <div style={{ display: "flex", gap: "0.25rem", alignItems: "flex-end", height: 120 }}>
            {analytics.searches_by_day.map((d: any, i: number) => {
              const max = Math.max(...analytics.searches_by_day.map((x: any) => x.count));
              const height = max > 0 ? (d.count / max) * 100 : 0;
              return (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.25rem" }}>
                  <div style={{ width: "100%", height: `${height}%`, background: "var(--color-primary)", borderRadius: "4px 4px 0 0", minHeight: 2 }} title={`${d.count} lượt`} />
                  <span style={{ fontSize: "0.5rem", color: "var(--color-text-muted)", transform: "rotate(-45deg)", whiteSpace: "nowrap" }}>
                    {new Date(d.date).toLocaleDateString("vi", { day: "2-digit", month: "2-digit" })}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>🔥 Top 20 truy vấn</h3>
          {analytics.top_queries.map((q: any, i: number) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)", fontSize: "0.875rem" }}>
              <span>{i + 1}. {q.query}</span>
              <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>{q.count}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>❌ Truy vấn không có kết quả</h3>
          {analytics.no_result_queries.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Không có truy vấn nào thất bại 🎉</p>
          ) : analytics.no_result_queries.map((q: any, i: number) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)", fontSize: "0.875rem" }}>
              <span>{q.query}</span>
              <span style={{ fontWeight: 600, color: "var(--color-error)" }}>{q.count}</span>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}

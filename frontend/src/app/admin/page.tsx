"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(() => { api.getAnalytics().then(setAnalytics).catch(() => {}); }, []);

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>📊 Admin Dashboard</h1>

      {!analytics ? <div className="spinner" /> : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
            <div className="stat-card"><div className="stat-value">{analytics.total_searches}</div><div className="stat-label">Tổng lượt tìm kiếm</div></div>
            <div className="stat-card"><div className="stat-value">{analytics.total_documents}</div><div className="stat-label">Tài liệu đã xử lý</div></div>
            <div className="stat-card"><div className="stat-value">{analytics.total_chunks}</div><div className="stat-label">Đoạn nội dung</div></div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div className="card">
              <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>🔥 Từ khóa phổ biến</h3>
              {analytics.top_queries.length === 0 ? <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Chưa có dữ liệu</p> : (
                <div>
                  {analytics.top_queries.slice(0, 10).map((q: any, i: number) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)" }}>
                      <span style={{ fontSize: "0.875rem" }}>{q.query}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{q.count} lần</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>❌ Không có kết quả</h3>
              {analytics.no_result_queries.length === 0 ? <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Tất cả truy vấn đều có kết quả 🎉</p> : (
                <div>
                  {analytics.no_result_queries.slice(0, 10).map((q: any, i: number) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)" }}>
                      <span style={{ fontSize: "0.875rem" }}>{q.query}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-error)" }}>{q.count} lần</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}

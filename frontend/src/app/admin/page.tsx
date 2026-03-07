"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Search as SearchIcon, FileText, Layers, TrendingUp, AlertTriangle } from "lucide-react";

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(() => { api.getAnalytics().then(setAnalytics).catch(() => {}); }, []);

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Admin Dashboard</h1>
        <p>Tổng quan hệ thống tra cứu kiến thức</p>
      </div>

      {!analytics ? <div className="spinner" /> : (
        <>
          <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "var(--color-primary-light)", color: "var(--color-primary)" }}>
                <SearchIcon size={22} />
              </div>
              <div className="stat-value">{analytics.total_searches}</div>
              <div className="stat-label">Tổng lượt tìm kiếm</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "#D1FAE5", color: "#065F46" }}>
                <FileText size={22} />
              </div>
              <div className="stat-value">{analytics.total_documents}</div>
              <div className="stat-label">Tài liệu đã xử lý</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "#FEF3C7", color: "#92400E" }}>
                <Layers size={22} />
              </div>
              <div className="stat-value">{analytics.total_chunks}</div>
              <div className="stat-label">Đoạn nội dung</div>
            </div>
          </div>

          <div className="grid-2" style={{ gap: "1.5rem" }}>
            <div className="card">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
                <TrendingUp size={18} style={{ color: "var(--color-primary)" }} />
                <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Từ khóa phổ biến</h3>
              </div>
              {analytics.top_queries.length === 0 ? (
                <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Chưa có dữ liệu</p>
              ) : (
                <div>
                  {analytics.top_queries.slice(0, 10).map((q: any, i: number) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)" }}>
                      <span style={{ fontSize: "0.875rem" }}>{q.query}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-primary)", fontWeight: 600 }}>{q.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
                <AlertTriangle size={18} style={{ color: "var(--color-error)" }} />
                <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Không có kết quả</h3>
              </div>
              {analytics.no_result_queries.length === 0 ? (
                <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Tất cả truy vấn đều có kết quả</p>
              ) : (
                <div>
                  {analytics.no_result_queries.slice(0, 10).map((q: any, i: number) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)" }}>
                      <span style={{ fontSize: "0.875rem" }}>{q.query}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-error)", fontWeight: 600 }}>{q.count}</span>
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

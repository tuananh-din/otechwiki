"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Search as SearchIcon, FileText, Layers, BarChart3, TrendingUp, AlertTriangle } from "lucide-react";

export default function AdminAnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(() => { api.getAnalytics().then(setAnalytics).catch(() => {}); }, []);

  if (!analytics) return <AppLayout><div className="spinner" style={{ margin: "3rem auto" }} /></AppLayout>;

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Analytics</h1>
        <p>Chi tiết phân tích hoạt động tìm kiếm</p>
      </div>

      <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "var(--color-primary-light)", color: "var(--color-primary)" }}>
            <SearchIcon size={22} />
          </div>
          <div className="stat-value">{analytics.total_searches}</div>
          <div className="stat-label">Tổng tìm kiếm</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#D1FAE5", color: "#065F46" }}>
            <FileText size={22} />
          </div>
          <div className="stat-value">{analytics.total_documents}</div>
          <div className="stat-label">Tài liệu</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#FEF3C7", color: "#92400E" }}>
            <Layers size={22} />
          </div>
          <div className="stat-value">{analytics.total_chunks}</div>
          <div className="stat-label">Đoạn nội dung</div>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
          <BarChart3 size={18} style={{ color: "var(--color-primary)" }} />
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Lượt tìm kiếm theo ngày</h3>
        </div>
        {analytics.searches_by_day.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Chưa có dữ liệu</p>
        ) : (
          <div style={{ display: "flex", gap: "3px", alignItems: "flex-end", height: 140, padding: "0.5rem 0" }}>
            {analytics.searches_by_day.map((d: any, i: number) => {
              const max = Math.max(...analytics.searches_by_day.map((x: any) => x.count));
              const height = max > 0 ? (d.count / max) * 100 : 0;
              return (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.375rem" }}>
                  <span style={{ fontSize: "0.625rem", color: "var(--color-text-muted)" }}>{d.count}</span>
                  <div style={{
                    width: "100%", height: `${height}%`,
                    background: "linear-gradient(180deg, var(--color-primary) 0%, var(--color-secondary) 100%)",
                    borderRadius: "4px 4px 0 0", minHeight: 2, transition: "height 0.3s ease",
                  }} title={`${d.count} lượt`} />
                  <span style={{ fontSize: "0.5rem", color: "var(--color-text-muted)", transform: "rotate(-45deg)", whiteSpace: "nowrap" }}>
                    {new Date(d.date).toLocaleDateString("vi", { day: "2-digit", month: "2-digit" })}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid-2" style={{ gap: "1.5rem" }}>
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <TrendingUp size={18} style={{ color: "var(--color-primary)" }} />
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Top 20 truy vấn</h3>
          </div>
          {analytics.top_queries.map((q: any, i: number) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--color-border)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "var(--color-text-muted)", fontSize: "0.75rem", width: 20 }}>{i + 1}.</span>
                {q.query}
              </span>
              <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>{q.count}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <AlertTriangle size={18} style={{ color: "var(--color-error)" }} />
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Truy vấn không có kết quả</h3>
          </div>
          {analytics.no_result_queries.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Không có truy vấn nào thất bại</p>
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

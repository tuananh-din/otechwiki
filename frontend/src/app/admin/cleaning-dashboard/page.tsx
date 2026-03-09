"use client";

import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Loader2, RefreshCw, CheckCircle2, AlertCircle, BarChart3, FileText, Layers, Search as SearchIcon } from "lucide-react";

interface CleaningStats {
  total_documents: number;
  total_chunks: number;
  searchable_chunks: number;
  non_searchable_chunks: number;
  cleaning_breakdown: Record<string, number>;
  page_type_breakdown: Record<string, number>;
  mapping_coverage: {
    mapped: number;
    unmapped: number;
    percentage: number;
  };
}

const statusColors: Record<string, { bg: string; color: string }> = {
  cleaned: { bg: "#D1FAE5", color: "#065F46" },
  legacy: { bg: "#FEF3C7", color: "#92400E" },
  error: { bg: "#FEE2E2", color: "#991B1B" },
  pending: { bg: "#F1F5F9", color: "#475569" },
  unknown: { bg: "#F1F5F9", color: "#475569" },
};

const pageTypeLabels: Record<string, string> = {
  product_detail: "Trang sản phẩm",
  collection: "Bộ sưu tập",
  homepage: "Trang chủ",
  other: "Khác",
  unknown: "Chưa phân loại",
};

export default function CleaningDashboardPage() {
  const [stats, setStats] = useState<CleaningStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [reprocessing, setReprocessing] = useState(false);
  const [result, setResult] = useState<any>(null);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await api.cleaningStats();
      setStats(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { loadStats(); }, []);

  const handleReprocessAll = async () => {
    if (!confirm("Reprocess tất cả web documents qua V2 pipeline? Quá trình này có thể mất vài phút.")) return;
    setReprocessing(true);
    setResult(null);
    try {
      const res = await api.reprocessAll();
      setResult(res);
      await loadStats();
    } catch (e: any) {
      setResult({ error: e.message });
    }
    setReprocessing(false);
  };

  if (loading && !stats) {
    return <AppLayout><div className="spinner" style={{ margin: "3rem auto" }} /></AppLayout>;
  }

  return (
    <AppLayout>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <BarChart3 size={26} style={{ color: "var(--color-primary)" }} />
            Cleaning Dashboard
          </h1>
          <p>Pipeline V2 — Rule-based cleaning + Heading-aware chunking</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn btn-ghost" onClick={loadStats} disabled={loading}>
            <RefreshCw size={16} className={loading ? "spinner" : ""} />
            <span>Refresh</span>
          </button>
          <button className="btn btn-primary" onClick={handleReprocessAll} disabled={reprocessing}>
            {reprocessing ? <Loader2 size={16} className="spinner" /> : <RefreshCw size={16} />}
            <span>{reprocessing ? "Đang xử lý..." : "Reprocess All"}</span>
          </button>
        </div>
      </div>

      {result && (
        <div className="card" style={{
          marginBottom: "1.5rem",
          background: result.error ? "#FEF2F2" : "#F0FDF4",
          borderColor: result.error ? "#FECACA" : "#BBF7D0",
        }}>
          {result.error ? (
            <p style={{ color: "#991B1B", display: "flex", alignItems: "center", gap: "0.5rem", margin: 0 }}>
              <AlertCircle size={18} /> {result.error}
            </p>
          ) : (
            <p style={{ color: "#065F46", display: "flex", alignItems: "center", gap: "0.5rem", margin: 0 }}>
              <CheckCircle2 size={18} />
              Đã xử lý {result.processed}/{result.total} documents ({result.errors} lỗi). {result.aliases_created} aliases tạo.
            </p>
          )}
        </div>
      )}

      {stats && (
        <>
          {/* Summary Cards */}
          <div className="grid-3" style={{ marginBottom: "1.5rem", gridTemplateColumns: "repeat(4, 1fr)" }}>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "var(--color-primary-light)", color: "var(--color-primary)" }}>
                <FileText size={22} />
              </div>
              <div className="stat-value">{stats.total_documents}</div>
              <div className="stat-label">Documents</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "#FEF3C7", color: "#92400E" }}>
                <Layers size={22} />
              </div>
              <div className="stat-value">{stats.total_chunks}</div>
              <div className="stat-label">Total Chunks</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "#D1FAE5", color: "#065F46" }}>
                <SearchIcon size={22} />
              </div>
              <div className="stat-value">{stats.searchable_chunks}</div>
              <div className="stat-label">Searchable</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "#FEE2E2", color: "#991B1B" }}>
                <AlertCircle size={22} />
              </div>
              <div className="stat-value">{stats.non_searchable_chunks}</div>
              <div className="stat-label">Non-Searchable</div>
            </div>
          </div>

          {/* Detail Cards */}
          <div className="grid-3">
            {/* Cleaning Status */}
            <div className="card">
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, marginBottom: "1rem" }}>Cleaning Status</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {Object.entries(stats.cleaning_breakdown).map(([status, count]) => {
                  const colors = statusColors[status] || statusColors.unknown;
                  return (
                    <div key={status} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span className="badge" style={{ background: colors.bg, color: colors.color }}>
                        {status}
                      </span>
                      <span style={{ fontWeight: 600, fontFamily: "'Poppins', sans-serif" }}>{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Page Types */}
            <div className="card">
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, marginBottom: "1rem" }}>Page Types</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {Object.entries(stats.page_type_breakdown).map(([type, count]) => (
                  <div key={type} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                      {pageTypeLabels[type] || type}
                    </span>
                    <span style={{ fontWeight: 600, fontFamily: "'Poppins', sans-serif" }}>{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Mapping Coverage */}
            <div className="card">
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, marginBottom: "1rem" }}>Mapping Coverage</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.875rem", color: "var(--color-success)" }}>Mapped</span>
                  <span style={{ fontWeight: 600, color: "var(--color-success)" }}>{stats.mapping_coverage.mapped}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.875rem", color: "var(--color-error)" }}>Unmapped</span>
                  <span style={{ fontWeight: 600, color: "var(--color-error)" }}>{stats.mapping_coverage.unmapped}</span>
                </div>
                <div style={{
                  width: "100%", height: 10, borderRadius: 5,
                  background: "var(--color-border)", overflow: "hidden",
                }}>
                  <div style={{
                    width: `${stats.mapping_coverage.percentage}%`, height: "100%",
                    borderRadius: 5, background: "var(--color-success)",
                    transition: "width 0.5s ease",
                  }} />
                </div>
                <p style={{
                  textAlign: "center", fontSize: "0.875rem", fontWeight: 600,
                  color: "var(--color-text)", margin: 0,
                }}>
                  {stats.mapping_coverage.percentage}% coverage
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}

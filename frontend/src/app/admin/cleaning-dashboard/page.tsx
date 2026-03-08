"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Loader2, RefreshCw, CheckCircle2, AlertCircle, BarChart3 } from "lucide-react";

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

  const statusColors: Record<string, string> = {
    cleaned: "bg-green-100 text-green-800",
    legacy: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    pending: "bg-gray-100 text-gray-600",
  };

  const pageTypeIcons: Record<string, string> = {
    product_detail: "🛍️",
    collection: "📁",
    homepage: "🏠",
    other: "📄",
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <BarChart3 size={28} className="text-blue-600" />
            Cleaning Dashboard
          </h1>
          <p className="text-gray-500 mt-1">Pipeline V2 — Rule-based cleaning + Heading-aware chunking</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={loadStats} disabled={loading} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button onClick={handleReprocessAll} disabled={reprocessing} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
            {reprocessing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            {reprocessing ? "Đang xử lý..." : "Reprocess All"}
          </button>
        </div>
      </div>

      {result && (
        <div className={`p-4 rounded-xl border ${result.error ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
          {result.error ? (
            <p className="text-red-700 flex items-center gap-2"><AlertCircle size={18} /> {result.error}</p>
          ) : (
            <div className="text-green-700 flex items-center gap-2">
              <CheckCircle2 size={18} />
              <span>Đã xử lý {result.processed}/{result.total} documents ({result.errors} lỗi). {result.aliases_created} aliases tạo.</span>
            </div>
          )}
        </div>
      )}

      {loading && !stats ? (
        <div className="flex justify-center py-12"><Loader2 size={32} className="animate-spin text-blue-500" /></div>
      ) : stats && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
              <p className="text-sm text-gray-500">Documents</p>
              <p className="text-3xl font-bold text-gray-800">{stats.total_documents}</p>
            </div>
            <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
              <p className="text-sm text-gray-500">Total Chunks</p>
              <p className="text-3xl font-bold text-gray-800">{stats.total_chunks}</p>
            </div>
            <div className="bg-white rounded-xl p-5 border border-green-200 shadow-sm">
              <p className="text-sm text-green-600">Searchable</p>
              <p className="text-3xl font-bold text-green-700">{stats.searchable_chunks}</p>
            </div>
            <div className="bg-white rounded-xl p-5 border border-red-200 shadow-sm">
              <p className="text-sm text-red-500">Non-Searchable</p>
              <p className="text-3xl font-bold text-red-600">{stats.non_searchable_chunks}</p>
            </div>
          </div>

          {/* Cleaning Status + Page Types */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Cleaning Status */}
            <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
              <h3 className="font-semibold text-gray-700 mb-3">Cleaning Status</h3>
              <div className="space-y-2">
                {Object.entries(stats.cleaning_breakdown).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${statusColors[status] || "bg-gray-100 text-gray-600"}`}>
                      {status}
                    </span>
                    <span className="font-mono text-gray-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Page Types */}
            <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
              <h3 className="font-semibold text-gray-700 mb-3">Page Types</h3>
              <div className="space-y-2">
                {Object.entries(stats.page_type_breakdown).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      {pageTypeIcons[type] || "📄"} {type}
                    </span>
                    <span className="font-mono text-gray-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Mapping Coverage */}
            <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
              <h3 className="font-semibold text-gray-700 mb-3">Mapping Coverage</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-green-600">Mapped</span>
                  <span className="font-mono text-green-700">{stats.mapping_coverage.mapped}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-red-500">Unmapped</span>
                  <span className="font-mono text-red-600">{stats.mapping_coverage.unmapped}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-green-500 h-3 rounded-full transition-all"
                    style={{ width: `${stats.mapping_coverage.percentage}%` }}
                  />
                </div>
                <p className="text-center text-sm font-semibold text-gray-700">
                  {stats.mapping_coverage.percentage}% coverage
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

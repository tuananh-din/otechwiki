"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import {
  Brain, FileJson, CheckCircle2, XCircle, Archive, ChevronDown, ChevronUp,
  RefreshCw, Eye, Loader2, AlertTriangle, FileCheck, Package,
} from "lucide-react";

interface Draft {
  file: string;
  type: string;
  path: string;
  product_name: string;
  status: string;
  size_bytes: number;
}

interface Inventory {
  total_files: number;
  layers: Record<string, { total: number; categories: Record<string, { count: number }> }>;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "#f59e0b",
  canonical: "#10b981",
  rejected: "#ef4444",
  archived: "#6b7280",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Bản nháp",
  canonical: "Chính thức",
  rejected: "Từ chối",
  archived: "Lưu trữ",
};

const TYPE_LABELS: Record<string, string> = {
  product_specs: "Thông số SP",
  pricing: "Giá bán",
  faq_pairs: "FAQ",
  policies: "Chính sách",
  compare: "So sánh",
  error_codes: "Mã lỗi",
};

export default function KnowledgePage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [expandedDraft, setExpandedDraft] = useState<string | null>(null);
  const [draftContent, setDraftContent] = useState<any>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [d, inv] = await Promise.all([
        api.getKnowledgeDrafts(filterType || undefined),
        api.getKnowledgeInventory(),
      ]);
      setDrafts(d.drafts || []);
      setInventory(inv);
    } catch (e: any) {
      setMessage({ text: e.message, type: "error" });
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [filterType]);

  const filteredDrafts = drafts.filter((d) => {
    if (filterStatus && d.status !== filterStatus) return false;
    return true;
  });

  const toggleDraft = async (draft: Draft) => {
    const key = `${draft.type}/${draft.file}`;
    if (expandedDraft === key) {
      setExpandedDraft(null);
      setDraftContent(null);
      return;
    }
    setExpandedDraft(key);
    setLoadingContent(true);
    try {
      const result = await api.getKnowledgeDraft(draft.type, draft.file);
      setDraftContent(result.data);
    } catch (e: any) {
      setMessage({ text: e.message, type: "error" });
    }
    setLoadingContent(false);
  };

  const handlePromote = async (draft: Draft) => {
    setActionLoading(`promote-${draft.file}`);
    try {
      const result = await api.promoteKnowledgeDraft(draft.type, draft.file);
      setMessage({ text: `✓ ${result.message}`, type: "success" });
      fetchData();
    } catch (e: any) {
      setMessage({ text: e.message, type: "error" });
    }
    setActionLoading(null);
  };

  const handleReject = async (draft: Draft) => {
    const reason = prompt("Lý do từ chối:");
    if (reason === null) return;
    setActionLoading(`reject-${draft.file}`);
    try {
      await api.rejectKnowledgeDraft(draft.type, draft.file, reason);
      setMessage({ text: `Đã từ chối: ${draft.file}`, type: "success" });
      fetchData();
    } catch (e: any) {
      setMessage({ text: e.message, type: "error" });
    }
    setActionLoading(null);
  };

  const handleArchive = async (draft: Draft) => {
    setActionLoading(`archive-${draft.file}`);
    try {
      await api.archiveKnowledgeDraft(draft.type, draft.file);
      setMessage({ text: `Đã lưu trữ: ${draft.file}`, type: "success" });
      fetchData();
    } catch (e: any) {
      setMessage({ text: e.message, type: "error" });
    }
    setActionLoading(null);
  };

  // Stats
  const statusCounts = drafts.reduce((acc, d) => {
    acc[d.status] = (acc[d.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const typeCounts = drafts.reduce((acc, d) => {
    acc[d.type] = (acc[d.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <AppLayout>
      <div style={{ padding: "2rem", maxWidth: 1200, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
          <Brain size={28} color="var(--color-accent)" />
          <div>
            <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700 }}>Knowledge Base</h1>
            <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
              Quản lý dữ liệu đã trích xuất — xem, duyệt, từ chối bản nháp
            </p>
          </div>
          <button
            onClick={fetchData}
            style={{
              marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.5rem",
              padding: "0.5rem 1rem", borderRadius: 8, border: "1px solid var(--color-border)",
              background: "var(--color-surface)", cursor: "pointer", color: "var(--color-text)",
            }}
          >
            <RefreshCw size={16} /> Làm mới
          </button>
        </div>

        {/* Message */}
        {message && (
          <div
            style={{
              padding: "0.75rem 1rem", borderRadius: 8, marginBottom: "1rem",
              background: message.type === "success" ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
              border: `1px solid ${message.type === "success" ? "#10b981" : "#ef4444"}`,
              color: message.type === "success" ? "#10b981" : "#ef4444",
              display: "flex", alignItems: "center", gap: "0.5rem",
            }}
            onClick={() => setMessage(null)}
          >
            {message.type === "success" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            {message.text}
          </div>
        )}

        {/* Stats Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
          <div className="card" style={{ padding: "1rem", textAlign: "center" }}>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-accent)" }}>{drafts.length}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Tổng records</div>
          </div>
          {Object.entries(statusCounts).map(([status, count]) => (
            <div
              key={status}
              className="card"
              style={{ padding: "1rem", textAlign: "center", cursor: "pointer", border: filterStatus === status ? `2px solid ${STATUS_COLORS[status]}` : undefined }}
              onClick={() => setFilterStatus(filterStatus === status ? "" : status)}
            >
              <div style={{ fontSize: "1.75rem", fontWeight: 700, color: STATUS_COLORS[status] }}>{count}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{STATUS_LABELS[status] || status}</div>
            </div>
          ))}
          {inventory && (
            <div className="card" style={{ padding: "1rem", textAlign: "center" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#8b5cf6" }}>{inventory.total_files}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Files trên disk</div>
            </div>
          )}
        </div>

        {/* Filter Tabs */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <button
            onClick={() => setFilterType("")}
            className={`card`}
            style={{
              padding: "0.4rem 0.8rem", cursor: "pointer", fontSize: "0.8rem", fontWeight: 500,
              border: !filterType ? "2px solid var(--color-accent)" : "1px solid var(--color-border)",
              borderRadius: 6, background: "var(--color-surface)", color: "var(--color-text)",
            }}
          >
            Tất cả
          </button>
          {Object.entries(typeCounts).map(([type, count]) => (
            <button
              key={type}
              onClick={() => setFilterType(filterType === type ? "" : type)}
              className={`card`}
              style={{
                padding: "0.4rem 0.8rem", cursor: "pointer", fontSize: "0.8rem", fontWeight: 500,
                border: filterType === type ? "2px solid var(--color-accent)" : "1px solid var(--color-border)",
                borderRadius: 6, background: "var(--color-surface)", color: "var(--color-text)",
              }}
            >
              {TYPE_LABELS[type] || type} ({count})
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "3rem", color: "var(--color-text-muted)" }}>
            <Loader2 size={24} className="spin" style={{ animation: "spin 1s linear infinite" }} />
            <p>Đang tải...</p>
          </div>
        ) : (
          /* Draft List */
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {filteredDrafts.length === 0 ? (
              <div className="card" style={{ padding: "2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                Không có dữ liệu phù hợp
              </div>
            ) : filteredDrafts.map((draft) => {
              const key = `${draft.type}/${draft.file}`;
              const isExpanded = expandedDraft === key;
              return (
                <div key={key} className="card" style={{ overflow: "hidden" }}>
                  {/* Row header */}
                  <div
                    onClick={() => toggleDraft(draft)}
                    style={{
                      padding: "0.75rem 1rem", display: "flex", alignItems: "center", gap: "0.75rem",
                      cursor: "pointer", transition: "background 0.15s",
                    }}
                  >
                    <FileJson size={18} color={STATUS_COLORS[draft.status]} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{draft.product_name || draft.file}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", display: "flex", gap: "0.75rem" }}>
                        <span>{TYPE_LABELS[draft.type] || draft.type}</span>
                        <span>{(draft.size_bytes / 1024).toFixed(1)} KB</span>
                        <span>{draft.file}</span>
                      </div>
                    </div>
                    <span
                      style={{
                        padding: "0.2rem 0.6rem", borderRadius: 12, fontSize: "0.7rem", fontWeight: 600,
                        background: `${STATUS_COLORS[draft.status]}20`, color: STATUS_COLORS[draft.status],
                      }}
                    >
                      {STATUS_LABELS[draft.status] || draft.status}
                    </span>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div style={{ borderTop: "1px solid var(--color-border)", padding: "1rem" }}>
                      {loadingContent ? (
                        <div style={{ textAlign: "center", padding: "1rem", color: "var(--color-text-muted)" }}>
                          <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} /> Đang tải...
                        </div>
                      ) : draftContent ? (
                        <>
                          {/* Action buttons */}
                          {draft.status === "draft" && (
                            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
                              <button
                                onClick={(e) => { e.stopPropagation(); handlePromote(draft); }}
                                disabled={actionLoading === `promote-${draft.file}`}
                                style={{
                                  display: "flex", alignItems: "center", gap: "0.3rem",
                                  padding: "0.4rem 0.8rem", borderRadius: 6, border: "none",
                                  background: "#10b981", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                                }}
                              >
                                <CheckCircle2 size={14} /> Duyệt → Canonical
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleReject(draft); }}
                                disabled={actionLoading === `reject-${draft.file}`}
                                style={{
                                  display: "flex", alignItems: "center", gap: "0.3rem",
                                  padding: "0.4rem 0.8rem", borderRadius: 6, border: "1px solid #ef4444",
                                  background: "transparent", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                                }}
                              >
                                <XCircle size={14} /> Từ chối
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleArchive(draft); }}
                                disabled={actionLoading === `archive-${draft.file}`}
                                style={{
                                  display: "flex", alignItems: "center", gap: "0.3rem",
                                  padding: "0.4rem 0.8rem", borderRadius: 6, border: "1px solid var(--color-border)",
                                  background: "transparent", color: "var(--color-text-muted)", cursor: "pointer", fontSize: "0.8rem",
                                }}
                              >
                                <Archive size={14} /> Lưu trữ
                              </button>
                            </div>
                          )}

                          {/* JSON viewer */}
                          <pre
                            style={{
                              background: "var(--color-bg)", padding: "1rem", borderRadius: 8,
                              fontSize: "0.75rem", overflow: "auto", maxHeight: 400, lineHeight: 1.5,
                              border: "1px solid var(--color-border)", margin: 0,
                            }}
                          >
                            {JSON.stringify(draftContent, null, 2)}
                          </pre>
                        </>
                      ) : (
                        <div style={{ color: "var(--color-text-muted)" }}>Không có dữ liệu</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <style jsx>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </AppLayout>
  );
}

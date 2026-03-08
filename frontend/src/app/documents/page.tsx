"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { FileText, Calendar, CheckCircle2, AlertCircle, Trash2, CheckSquare, Square, Loader2 } from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [toast, setToast] = useState("");

  const loadDocs = () => {
    setLoading(true);
    api.getDocuments().then(setDocuments).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadDocs(); }, []);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === documents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(documents.map((d) => d.id)));
    }
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    setDeleting(true);
    try {
      await api.deleteDocuments(Array.from(selectedIds));
      showToast(`Đã xoá ${selectedIds.size} tài liệu`);
      setSelectedIds(new Set());
      loadDocs();
    } catch (e: any) {
      showToast(`Lỗi: ${e.message}`);
    } finally {
      setDeleting(false);
      setShowConfirm(false);
    }
  };

  const handleDeleteSingle = async (id: number, title: string) => {
    if (!confirm(`Xoá tài liệu "${title}" và tất cả dữ liệu liên quan?`)) return;
    try {
      await api.deleteDocument(id);
      showToast(`Đã xoá "${title}"`);
      setSelectedIds((prev) => { const next = new Set(prev); next.delete(id); return next; });
      loadDocs();
    } catch (e: any) {
      showToast(`Lỗi: ${e.message}`);
    }
  };

  const allSelected = documents.length > 0 && selectedIds.size === documents.length;

  return (
    <AppLayout>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1>Tài liệu</h1>
          <p>Tất cả tài liệu đã được xử lý trong hệ thống ({documents.length})</p>
        </div>
        {selectedIds.size > 0 && (
          <button
            className="btn btn-danger"
            onClick={() => setShowConfirm(true)}
            disabled={deleting}
            style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}
          >
            {deleting ? <Loader2 size={16} className="spinner" /> : <Trash2 size={16} />}
            Xoá {selectedIds.size} đã chọn
          </button>
        )}
      </div>

      {/* Confirm dialog */}
      {showConfirm && (
        <div className="confirm-overlay" onClick={() => setShowConfirm(false)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>⚠️ Xác nhận xoá</h3>
            <p style={{ margin: "0 0 1rem", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
              Bạn sắp xoá <strong>{selectedIds.size}</strong> tài liệu cùng toàn bộ chunks và dữ liệu liên quan.
              Hành động này không thể hoàn tác.
            </p>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button className="btn" onClick={() => setShowConfirm(false)}>Huỷ</button>
              <button className="btn btn-danger" onClick={handleDeleteSelected} disabled={deleting}>
                {deleting ? <Loader2 size={14} className="spinner" /> : null}
                Xoá vĩnh viễn
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="toast">{toast}</div>
      )}

      {loading ? <div className="spinner" /> : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} />
          <p>Chưa có tài liệu nào</p>
        </div>
      ) : (
        <div>
          {/* Select all header */}
          <div
            className="result-item"
            style={{ padding: "0.75rem 1.25rem", display: "flex", alignItems: "center", gap: "0.75rem", cursor: "pointer", background: selectedIds.size > 0 ? "var(--color-primary-light)" : undefined }}
            onClick={toggleAll}
          >
            {allSelected ? <CheckSquare size={18} style={{ color: "var(--color-primary)" }} /> : <Square size={18} style={{ color: "var(--color-text-muted)" }} />}
            <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--color-text-muted)" }}>
              {selectedIds.size > 0 ? `Đã chọn ${selectedIds.size} / ${documents.length}` : "Chọn tất cả"}
            </span>
          </div>

          {documents.map((d) => (
            <div key={d.id} className="result-item" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              {/* Checkbox */}
              <div
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleSelect(d.id); }}
                style={{ cursor: "pointer", flexShrink: 0 }}
              >
                {selectedIds.has(d.id)
                  ? <CheckSquare size={18} style={{ color: "var(--color-primary)" }} />
                  : <Square size={18} style={{ color: "var(--color-text-muted)" }} />}
              </div>

              {/* Document info */}
              <Link href={`/documents/${d.id}`} style={{ textDecoration: "none", color: "inherit", flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", minWidth: 0 }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                      background: d.source_type === "pdf" ? "#FEF3C7" : "#D1FAE5",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: d.source_type === "pdf" ? "#92400E" : "#065F46",
                    }}>
                      <FileText size={18} />
                    </div>
                    <span style={{ fontWeight: 600, fontSize: "0.9375rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.title}</span>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexShrink: 0 }}>
                    <span className={`badge ${d.source_type === "pdf" ? "badge-pdf" : "badge-web"}`}>
                      {d.source_type.toUpperCase()}
                    </span>
                    <span className="badge" style={{
                      background: d.status === "ready" ? "#D1FAE5" : "#FEF3C7",
                      color: d.status === "ready" ? "#065F46" : "#92400E",
                      display: "inline-flex", alignItems: "center", gap: "0.25rem",
                    }}>
                      {d.status === "ready" ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                      {d.status}
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <Calendar size={12} />
                  {d.document_type || "–"} {d.page_count ? `• ${d.page_count} trang` : ""} • {new Date(d.created_at).toLocaleDateString("vi")}
                </div>
              </Link>

              {/* Delete button */}
              <button
                onClick={(e) => { e.preventDefault(); handleDeleteSingle(d.id, d.title); }}
                className="icon-btn-danger"
                title="Xoá tài liệu"
                style={{ flexShrink: 0 }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

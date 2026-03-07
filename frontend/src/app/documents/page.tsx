"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { FileText, Calendar, CheckCircle2, AlertCircle } from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDocuments().then(setDocuments).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Tài liệu</h1>
        <p>Tất cả tài liệu đã được xử lý trong hệ thống</p>
      </div>

      {loading ? <div className="spinner" /> : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} />
          <p>Chưa có tài liệu nào</p>
        </div>
      ) : (
        <div>
          {documents.map((d) => (
            <Link key={d.id} href={`/documents/${d.id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="result-item">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8,
                      background: d.source_type === "pdf" ? "#FEF3C7" : "#D1FAE5",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: d.source_type === "pdf" ? "#92400E" : "#065F46", flexShrink: 0,
                    }}>
                      <FileText size={18} />
                    </div>
                    <span style={{ fontWeight: 600, fontSize: "0.9375rem" }}>{d.title}</span>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
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
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

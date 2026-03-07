"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDocuments().then(setDocuments).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>📄 Tài liệu</h1>

      {loading ? <div className="spinner" /> : documents.length === 0 ? (
        <div className="no-result"><div className="no-result-icon">📄</div>Chưa có tài liệu nào</div>
      ) : (
        <div>
          {documents.map((d) => (
            <Link key={d.id} href={`/documents/${d.id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="result-item">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600 }}>{d.title}</span>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className={`badge ${d.source_type === "pdf" ? "badge-pdf" : "badge-web"}`}>
                      {d.source_type.toUpperCase()}
                    </span>
                    <span className={`badge ${d.status === "ready" ? "badge-web" : "badge-pdf"}`}>
                      {d.status}
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.375rem" }}>
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

"use client";
import { useState, useEffect, use } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, FileText, ExternalLink } from "lucide-react";

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDocument(Number(id)).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <AppLayout><div className="spinner" style={{ margin: "3rem auto" }} /></AppLayout>;
  if (!data) return (
    <AppLayout>
      <div className="empty-state"><FileText size={48} /><p>Tài liệu không tồn tại</p></div>
    </AppLayout>
  );

  const doc = data.document;

  return (
    <AppLayout>
      <div style={{ maxWidth: 900 }}>
        <Link href="/documents" style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.375rem" }}>
          <ArrowLeft size={14} /> Quay lại danh sách
        </Link>

        <div style={{ marginTop: "1rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "0 0 0.5rem" }}>{doc.title}</h1>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <span className={`badge ${doc.source_type === "pdf" ? "badge-pdf" : "badge-web"}`}>{doc.source_type.toUpperCase()}</span>
            {doc.document_type && <span className="badge badge-primary">{doc.document_type}</span>}
            {doc.page_count && <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{doc.page_count} trang</span>}
          </div>
        </div>

        {doc.source_url && (
          <p style={{ fontSize: "0.875rem", marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <ExternalLink size={14} style={{ color: "var(--color-text-muted)" }} />
            <a href={doc.source_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary)" }}>
              {doc.source_url}
            </a>
          </p>
        )}

        <div style={{ marginTop: "2rem" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>
            Nội dung ({data.chunks.length} đoạn)
          </h2>
          {data.chunks.map((chunk: any) => (
            <div key={chunk.id} className="card" style={{ marginBottom: "0.75rem" }}>
              {chunk.page_number && (
                <div style={{ fontSize: "0.6875rem", color: "var(--color-text-muted)", marginBottom: "0.5rem", textTransform: "uppercase", fontWeight: 600 }}>
                  Trang {chunk.page_number} {chunk.section_title ? `• ${chunk.section_title}` : ""}
                </div>
              )}
              <p style={{ fontSize: "0.875rem", lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap" }}>
                {chunk.content}
              </p>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}

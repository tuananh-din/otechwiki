"use client";
import { useState, useEffect, use } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, Package, FileText, Search } from "lucide-react";

export default function ProductDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProduct(slug).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <AppLayout><div className="spinner" style={{ margin: "3rem auto" }} /></AppLayout>;
  if (!data) return (
    <AppLayout>
      <div className="empty-state"><Package size={48} /><p>Sản phẩm không tồn tại</p></div>
    </AppLayout>
  );

  return (
    <AppLayout>
      <div style={{ maxWidth: 900 }}>
        <Link href="/products" style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.375rem" }}>
          <ArrowLeft size={14} /> Quay lại danh sách
        </Link>

        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "1rem 0 0.5rem" }}>
          {data.product.name}
        </h1>
        {data.product.category && <span className="badge badge-primary">{data.product.category}</span>}
        {data.product.description && (
          <p style={{ color: "var(--color-text-muted)", marginTop: "1rem", lineHeight: 1.6 }}>
            {data.product.description}
          </p>
        )}

        <div style={{ marginTop: "2rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <FileText size={18} style={{ color: "var(--color-primary)" }} />
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>Tài liệu liên quan</h2>
          </div>
          {data.documents.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)" }}>Chưa có tài liệu nào</p>
          ) : (
            data.documents.map((d: any) => (
              <Link key={d.id} href={`/documents/${d.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                <div className="result-item">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                    <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>{d.title}</span>
                    <span className={`badge ${d.source_type === "pdf" ? "badge-pdf" : "badge-web"}`}>
                      {d.source_type.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.375rem" }}>
                    {d.document_type} {d.page_count ? `• ${d.page_count} trang` : ""}
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>

        <div style={{ marginTop: "2rem" }}>
          <Link href={`/search?q=${encodeURIComponent(data.product.name)}`}>
            <button className="btn btn-primary">
              <Search size={16} /> Tìm kiếm về {data.product.name}
            </button>
          </Link>
        </div>
      </div>
    </AppLayout>
  );
}

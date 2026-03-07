"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { Package, FileText, ArrowRight } from "lucide-react";

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProducts().then((data) => { setProducts(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Sản phẩm</h1>
        <p>Danh sách sản phẩm và tài liệu liên quan</p>
      </div>

      {loading ? (
        <div className="spinner" />
      ) : products.length === 0 ? (
        <div className="empty-state">
          <Package size={48} />
          <p>Chưa có sản phẩm nào</p>
        </div>
      ) : (
        <div className="grid-auto">
          {products.map((p) => (
            <Link key={p.slug} href={`/products/${p.slug}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="card card-hover" style={{ height: "100%" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10,
                    background: "var(--color-primary-light)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "var(--color-primary)", flexShrink: 0,
                  }}>
                    <Package size={20} />
                  </div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>{p.name}</h3>
                </div>
                {p.category && <span className="badge badge-primary" style={{ marginBottom: "0.5rem" }}>{p.category}</span>}
                <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", margin: "0.5rem 0 0", lineHeight: 1.5 }}>
                  {p.description || "Chưa có mô tả"}
                </p>
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "1rem",
                  paddingTop: "0.75rem", borderTop: "1px solid var(--color-border)",
                }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                    <FileText size={14} /> {p.document_count} tài liệu
                  </span>
                  <ArrowRight size={14} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

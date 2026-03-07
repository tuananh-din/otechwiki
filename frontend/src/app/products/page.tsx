"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProducts().then((data) => { setProducts(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>📦 Sản phẩm</h1>

      {loading ? (
        <div className="spinner" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: "1rem" }}>
          {products.map((p) => (
            <Link key={p.slug} href={`/products/${p.slug}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="card" style={{ cursor: "pointer" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.5rem" }}>{p.name}</h3>
                {p.category && <span className="badge badge-web" style={{ marginBottom: "0.5rem" }}>{p.category}</span>}
                <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", margin: "0.5rem 0 0" }}>
                  {p.description || "Chưa có mô tả"}
                </p>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.75rem" }}>
                  📄 {p.document_count} tài liệu
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppLayout>
  );
}

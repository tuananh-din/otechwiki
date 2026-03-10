"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Grid3x3, RefreshCw, Loader2, CheckCircle2, XCircle, Package, FileText, Layers, AlertTriangle, ShieldCheck } from "lucide-react";

const PAGE_TYPE_LABELS: Record<string, string> = {
  product_detail: "Chi tiết SP",
  collection: "Danh mục",
  other: "Bài viết",
  homepage: "Trang chủ",
};

const MATCH_LABELS: Record<string, string> = {
  shopify_url: "Shopify URL",
  title_exact: "Tiêu đề",
  title_contains: "Tiêu đề (chứa)",
  url_slug: "URL Slug",
  content_extract: "Nội dung",
};

export default function ProductMappingPage() {
  const [matrix, setMatrix] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [mapping, setMapping] = useState(false);
  const [message, setMessage] = useState("");
  const [tooltip, setTooltip] = useState<{ product: string; type: string; docs: any[] } | null>(null);

  const loadMatrix = async () => {
    setLoading(true);
    try {
      const data = await api.getProductMatrix();
      setMatrix(data);
    } catch (err: any) { setMessage(`error:${err.message}`); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadMatrix(); }, []);

  const handleAutoMap = async () => {
    setMapping(true); setMessage("");
    try {
      const res = await api.autoMap();
      setMessage(`✅ Tạo ${res.products_created} sản phẩm, map ${res.documents_mapped} tài liệu.`);
      await loadMatrix();
    } catch (err: any) { setMessage(`error:${err.message}`); }
    finally { setMapping(false); }
  };

  const isError = message.startsWith("error:");
  const displayMsg = isError ? message.slice(6) : message;

  if (loading) return <AppLayout><div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}><Loader2 size={32} className="spinner" /></div></AppLayout>;

  const products = matrix?.products || [];
  const docTypes = matrix?.doc_types || [];
  const totalMapped = products.reduce((s: number, p: any) => s + p.total_docs, 0);
  const totalHighConf = products.reduce((s: number, p: any) => s + (p.high_confidence_docs || 0), 0);

  return (
    <AppLayout>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1>Product Mapping</h1>
          <p>Ma trận coverage: sản phẩm × loại trang</p>
        </div>
        <button className="btn btn-primary" onClick={handleAutoMap} disabled={mapping}>
          {mapping ? <><Loader2 size={16} className="spinner" /> Đang phân tích...</> : <><RefreshCw size={16} /> Auto-Map</>}
        </button>
      </div>

      {message && (
        <div className="card" style={{
          marginBottom: "1.5rem",
          background: isError ? "#FEF2F2" : "#F0FDF4",
          borderColor: isError ? "#FECACA" : "#BBF7D0",
          display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem",
        }}>
          {isError ? <XCircle size={16} style={{ color: "var(--color-error)" }} /> : <CheckCircle2 size={16} style={{ color: "var(--color-success)" }} />}
          {displayMsg}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "var(--color-primary-light)", color: "var(--color-primary)" }}><Package size={22} /></div>
          <div className="stat-value">{products.length}</div>
          <div className="stat-label">Sản phẩm</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#D1FAE5", color: "#065F46" }}><FileText size={22} /></div>
          <div className="stat-value">{totalMapped}</div>
          <div className="stat-label">Tài liệu đã map</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#DBEAFE", color: "#1E40AF" }}><ShieldCheck size={22} /></div>
          <div className="stat-value">{totalHighConf}</div>
          <div className="stat-label">Độ tin cậy cao</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#FEF3C7", color: "#92400E" }}><AlertTriangle size={22} /></div>
          <div className="stat-value">{matrix?.unmapped_docs || 0}</div>
          <div className="stat-label">Chưa map</div>
        </div>
      </div>

      {/* Matrix Table */}
      {products.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <Grid3x3 size={48} style={{ color: "var(--color-text-muted)", marginBottom: "1rem" }} />
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1.125rem" }}>Chưa có sản phẩm</h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            Bấm <strong>Auto-Map</strong> để tự động trích xuất sản phẩm từ tên tài liệu
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
              <thead>
                <tr style={{ background: "var(--color-surface-hover)" }}>
                  <th style={{ padding: "0.75rem 1rem", textAlign: "left", position: "sticky", left: 0, background: "var(--color-surface-hover)", zIndex: 1, borderRight: "2px solid var(--color-border)", minWidth: 180 }}>
                    Sản phẩm
                  </th>
                  <th style={{ padding: "0.75rem 0.5rem", textAlign: "right", fontSize: "0.7rem", fontWeight: 600, minWidth: 90 }}>
                    Giá
                  </th>
                  {docTypes.map((dt: string) => (
                    <th key={dt} style={{ padding: "0.75rem 0.5rem", textAlign: "center", fontSize: "0.7rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", minWidth: 70 }}>
                      {PAGE_TYPE_LABELS[dt] || dt}
                    </th>
                  ))}
                  <th style={{ padding: "0.75rem 0.5rem", textAlign: "center", fontWeight: 600, borderLeft: "2px solid var(--color-border)", minWidth: 50 }}>Docs</th>
                  <th style={{ padding: "0.75rem 0.5rem", textAlign: "center", fontWeight: 600, minWidth: 55 }}>Chunks</th>
                  <th style={{ padding: "0.75rem 0.5rem", textAlign: "center", fontWeight: 600, minWidth: 65 }}>Tin cậy</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p: any) => {
                  const hasProductDetail = p.coverage["product_detail"] > 0;
                  const confPct = p.total_docs > 0 ? Math.round(p.high_confidence_docs / p.total_docs * 100) : 0;
                  const rowBg = !hasProductDetail ? "#FEF2F2" : p.total_docs <= 1 ? "#FFFBEB" : "transparent";
                  return (
                    <tr key={p.id} style={{ background: rowBg, borderBottom: "1px solid var(--color-border)" }}>
                      <td style={{
                        padding: "0.625rem 1rem", fontWeight: 500, position: "sticky", left: 0,
                        background: rowBg || "white", zIndex: 1, borderRight: "2px solid var(--color-border)",
                        display: "flex", alignItems: "center", gap: "0.5rem",
                      }}>
                        <span style={{
                          display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                          background: p.category === "robot" ? "var(--color-primary)" : "#F59E0B",
                        }} />
                        {p.name.replace("Roborock ", "")}
                      </td>
                      <td style={{ padding: "0.5rem", textAlign: "right", fontSize: "0.75rem", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                        {p.price !== "N/A" ? p.price : "—"}
                      </td>
                      {docTypes.map((dt: string) => {
                        const count = p.coverage[dt];
                        const details = p.doc_details[dt] || [];
                        return (
                          <td
                            key={dt}
                            style={{ padding: "0.5rem", textAlign: "center", cursor: count > 0 ? "pointer" : "default", position: "relative" }}
                            onMouseEnter={() => count > 0 && setTooltip({ product: p.name, type: dt, docs: details })}
                            onMouseLeave={() => setTooltip(null)}
                          >
                            {count > 0 ? (
                              <span style={{
                                display: "inline-flex", alignItems: "center", justifyContent: "center",
                                width: 28, height: 28, borderRadius: "var(--radius-sm)",
                                background: dt === "product_detail" ? "#DBEAFE" : "#D1FAE5",
                                color: dt === "product_detail" ? "#1E40AF" : "#065F46",
                                fontWeight: 700, fontSize: "0.75rem",
                              }}>
                                {count > 1 ? count : "✓"}
                              </span>
                            ) : (
                              <span style={{
                                display: "inline-flex", alignItems: "center", justifyContent: "center",
                                width: 28, height: 28, borderRadius: "var(--radius-sm)",
                                background: dt === "product_detail" ? "#FEE2E2" : "#F3F4F6",
                                color: dt === "product_detail" ? "#DC2626" : "#9CA3AF",
                                fontSize: "0.7rem",
                              }}>
                                {dt === "product_detail" ? "✕" : "—"}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td style={{ padding: "0.5rem", textAlign: "center", borderLeft: "2px solid var(--color-border)", fontWeight: 600, color: "var(--color-primary)" }}>{p.total_docs}</td>
                      <td style={{ padding: "0.5rem", textAlign: "center", color: "var(--color-text-muted)" }}>{p.total_chunks}</td>
                      <td style={{ padding: "0.5rem", textAlign: "center" }}>
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: "0.7rem", fontWeight: 600,
                          background: confPct >= 80 ? "#D1FAE5" : confPct >= 50 ? "#FEF3C7" : "#FEE2E2",
                          color: confPct >= 80 ? "#065F46" : confPct >= 50 ? "#92400E" : "#DC2626",
                        }}>
                          {confPct}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div style={{
            padding: "0.75rem 1rem", background: "var(--color-surface-hover)", borderTop: "1px solid var(--color-border)",
            display: "flex", gap: "1.5rem", alignItems: "center", fontSize: "0.75rem", color: "var(--color-text-muted)", flexWrap: "wrap",
          }}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: "#DBEAFE", display: "inline-block" }} />
              Trang sản phẩm
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: "#D1FAE5", display: "inline-block" }} />
              Có tài liệu
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: "#FEE2E2", display: "inline-block" }} />
              Thiếu trang SP
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-primary)", display: "inline-block" }} />
              Robot
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#F59E0B", display: "inline-block" }} />
              Cầm tay
            </span>
            <span style={{ marginLeft: "auto" }}>
              Tin cậy = % tài liệu match ≥ 0.9
            </span>
          </div>
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: "fixed", bottom: 20, right: 20, background: "white", border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)", padding: "0.75rem 1rem", boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          maxWidth: 360, zIndex: 1000, fontSize: "0.8125rem",
        }}>
          <div style={{ fontWeight: 600, marginBottom: "0.375rem" }}>{tooltip.product} — {PAGE_TYPE_LABELS[tooltip.type] || tooltip.type}</div>
          {tooltip.docs.slice(0, 8).map((d: any) => (
            <div key={d.id} style={{ padding: "0.25rem 0", color: "var(--color-text-muted)", fontSize: "0.75rem", display: "flex", gap: "0.5rem" }}>
              <span style={{
                display: "inline-block", padding: "1px 4px", borderRadius: 3, fontSize: "0.625rem", fontWeight: 600,
                background: (d.confidence || 0) >= 0.9 ? "#D1FAE5" : "#FEF3C7",
                color: (d.confidence || 0) >= 0.9 ? "#065F46" : "#92400E",
                whiteSpace: "nowrap", lineHeight: 1.4,
              }}>
                {MATCH_LABELS[d.matched_by] || d.matched_by}
              </span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.title}</span>
            </div>
          ))}
          {tooltip.docs.length > 8 && (
            <div style={{ padding: "0.25rem 0", color: "var(--color-text-muted)", fontSize: "0.7rem", fontStyle: "italic" }}>
              +{tooltip.docs.length - 8} tài liệu khác...
            </div>
          )}
        </div>
      )}
    </AppLayout>
  );
}

"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";

function SearchContent() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const [query, setQuery] = useState(q);
  const [aiAnswer, setAiAnswer] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [askLoading, setAskLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [productFilter, setProductFilter] = useState("");
  const [products, setProducts] = useState<any[]>([]);

  useEffect(() => {
    api.getProducts().then(setProducts).catch(() => {});
  }, []);

  useEffect(() => {
    if (q) {
      setQuery(q);
      doSearch(q);
      doAsk(q);
    }
  }, [q]);

  const doSearch = async (searchQuery: string) => {
    setLoading(true);
    try {
      const res = await api.search(searchQuery, { product_filter: productFilter || undefined });
      setResults(res.results);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const doAsk = async (searchQuery: string) => {
    setAskLoading(true);
    try {
      const res = await api.ask(searchQuery, { product_filter: productFilter || undefined });
      setAiAnswer(res);
    } catch (err) {
      console.error(err);
    } finally {
      setAskLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    window.history.pushState({}, "", `/search?q=${encodeURIComponent(query.trim())}`);
    doSearch(query.trim());
    doAsk(query.trim());
  };

  const copyAnswer = () => {
    if (aiAnswer?.answer) {
      navigator.clipboard.writeText(aiAnswer.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AppLayout>
      <div style={{ maxWidth: 900 }}>
        {/* Search bar */}
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
          <input
            className="search-bar"
            style={{ fontSize: "1rem", padding: "0.75rem 1.25rem" }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nhập câu hỏi hoặc từ khóa..."
          />
          <select className="filter-select" value={productFilter} onChange={(e) => setProductFilter(e.target.value)}>
            <option value="">Tất cả sản phẩm</option>
            {products.map((p: any) => (
              <option key={p.slug} value={p.slug}>{p.name}</option>
            ))}
          </select>
          <button className="btn btn-primary" type="submit">Tìm</button>
        </form>

        {/* AI Answer */}
        {askLoading && (
          <div className="ai-answer-card" style={{ textAlign: "center" }}>
            <div className="spinner" style={{ margin: "0 auto" }} />
            <p style={{ color: "var(--color-text-muted)", marginTop: "0.5rem", fontSize: "0.875rem" }}>
              Đang tạo câu trả lời...
            </p>
          </div>
        )}

        {aiAnswer && !askLoading && (
          <div className="ai-answer-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
              <h3 style={{ margin: 0, fontSize: "0.9375rem", fontWeight: 600 }}>
                ✨ Trả lời AI
              </h3>
              <button className={`copy-btn ${copied ? "copied" : ""}`} onClick={copyAnswer}>
                {copied ? "✓ Đã copy" : "📋 Copy"}
              </button>
            </div>
            <div className="answer-text">{aiAnswer.answer}</div>

            {aiAnswer.citations?.length > 0 && (
              <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {aiAnswer.citations.map((c: any, i: number) => (
                  <Link key={i} href={`/documents/${c.document_id}`}>
                    <span className="citation-badge">
                      📄 {c.document_title}{c.page_number ? `, tr.${c.page_number}` : ""}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Search Results */}
        <h3 style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
          {loading ? "Đang tìm..." : results.length > 0 ? `${results.length} kết quả` : q ? "Không tìm thấy kết quả" : ""}
        </h3>

        {loading && <div className="spinner" />}

        {results.map((r: any) => (
          <div key={r.id} className="result-item">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <Link href={`/documents/${r.document_id}`} style={{ fontWeight: 600, color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9375rem" }}>
                {r.document_title}
              </Link>
              <span className={`badge ${r.source_type === "pdf" ? "badge-pdf" : "badge-web"}`}>
                {r.source_type.toUpperCase()}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", lineHeight: 1.6, margin: 0 }}>
              {r.content.length > 300 ? r.content.slice(0, 300) + "..." : r.content}
            </p>
            {r.page_number && (
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.5rem", display: "inline-block" }}>
                Trang {r.page_number}
              </span>
            )}
          </div>
        ))}
      </div>
    </AppLayout>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="spinner" style={{ margin: "4rem auto" }} />}>
      <SearchContent />
    </Suspense>
  );
}

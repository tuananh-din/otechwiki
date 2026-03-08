"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import Link from "next/link";
import { Search, Sparkles, Copy, Check, FileText, Loader2, MessageCircleQuestion, BarChart3, Lightbulb } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") || "";
  const [query, setQuery] = useState(q);
  const [aiAnswer, setAiAnswer] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [askLoading, setAskLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [productFilter, setProductFilter] = useState("");
  const [products, setProducts] = useState<any[]>([]);

  useEffect(() => { api.getProducts().then(setProducts).catch(() => {}); }, []);

  useEffect(() => {
    if (q) { setQuery(q); doSearch(q); doAsk(q); }
  }, [q]);

  const doSearch = async (searchQuery: string) => {
    setLoading(true);
    try {
      const res = await api.search(searchQuery, { product_filter: productFilter || undefined });
      setResults(res.results);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const doAsk = async (searchQuery: string) => {
    setAskLoading(true);
    try {
      const res = await api.ask(searchQuery, { product_filter: productFilter || undefined });
      setAiAnswer(res);
    } catch { /* ignore */ } finally { setAskLoading(false); }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    window.history.pushState({}, "", `/search?q=${encodeURIComponent(query.trim())}`);
    doSearch(query.trim());
    doAsk(query.trim());
  };

  const handleFollowUp = (question: string) => {
    setQuery(question);
    setAiAnswer(null);
    setResults([]);
    router.push(`/search?q=${encodeURIComponent(question)}`);
  };

  const copyAnswer = () => {
    if (aiAnswer?.answer) {
      navigator.clipboard.writeText(aiAnswer.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const answerTypeLabel = (type: string) => {
    if (type === "comparison") return { icon: <BarChart3 size={16} />, label: "So sánh sản phẩm" };
    if (type === "recommendation") return { icon: <Lightbulb size={16} />, label: "Tư vấn chọn model" };
    return { icon: <Sparkles size={18} />, label: "Trả lời AI" };
  };

  return (
    <AppLayout>
      <div style={{ maxWidth: 900 }}>
        <form onSubmit={handleSearch} className="search-form-row" style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          <div className="search-bar-wrapper" style={{ flex: 1, minWidth: 200 }}>
            <div className="search-bar-icon"><Search size={20} /></div>
            <input
              className="search-bar"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nhập câu hỏi hoặc từ khóa..."
            />
          </div>
          <select className="filter-select" value={productFilter} onChange={(e) => setProductFilter(e.target.value)}>
            <option value="">Tất cả sản phẩm</option>
            {products.map((p: any) => (
              <option key={p.slug} value={p.slug}>{p.name}</option>
            ))}
          </select>
          <button className="btn btn-primary" type="submit">
            <Search size={16} />
            <span>Tìm</span>
          </button>
        </form>

        {askLoading && (
          <div className="ai-answer-card" style={{ textAlign: "center", padding: "2rem" }}>
            <Loader2 size={24} className="spinner" style={{ margin: "0 auto" }} />
            <p style={{ color: "var(--color-text-muted)", marginTop: "0.75rem", fontSize: "0.875rem" }}>
              Đang tạo câu trả lời AI...
            </p>
          </div>
        )}

        {aiAnswer && !askLoading && (
          <>
            <div className="ai-answer-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {answerTypeLabel(aiAnswer.answer_type).icon}
                  <h3 style={{ margin: 0, fontSize: "0.9375rem", fontWeight: 600 }}>
                    {answerTypeLabel(aiAnswer.answer_type).label}
                  </h3>
                  {aiAnswer.answer_type !== "standard" && (
                    <span className="answer-type-badge">{aiAnswer.answer_type === "comparison" ? "So sánh" : "Tư vấn"}</span>
                  )}
                </div>
                <button className={`copy-btn ${copied ? "copied" : ""}`} onClick={copyAnswer}>
                  {copied ? <><Check size={14} /><span>Đã copy</span></> : <><Copy size={14} /><span>Copy</span></>}
                </button>
              </div>
              <div className="answer-text" style={{ whiteSpace: "pre-wrap" }}>{aiAnswer.answer}</div>

              {aiAnswer.citations?.length > 0 && (
                <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {aiAnswer.citations.map((c: any, i: number) => (
                    <Link key={i} href={`/documents/${c.document_id}`} className="citation-badge">
                      <FileText size={12} />
                      {c.document_title}{c.page_number ? `, tr.${c.page_number}` : ""}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Follow-up questions */}
            {aiAnswer.follow_up_questions?.length > 0 && (
              <div className="follow-up-section">
                <div className="follow-up-header">
                  <MessageCircleQuestion size={16} />
                  <span>Bạn có thể hỏi thêm</span>
                </div>
                <div className="follow-up-list">
                  {aiAnswer.follow_up_questions.map((question: string, i: number) => (
                    <button
                      key={i}
                      className="follow-up-chip"
                      onClick={() => handleFollowUp(question)}
                    >
                      {question}
                      <span className="follow-up-arrow">→</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 500 }}>
            {loading ? "Đang tìm..." : results.length > 0 ? `${results.length} kết quả` : q ? "Không tìm thấy kết quả" : ""}
          </span>
        </div>

        {loading && <Loader2 size={24} className="spinner" />}

        {results.map((r: any) => (
          <div key={r.id} className="result-item">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem", gap: "0.5rem", flexWrap: "wrap" }}>
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

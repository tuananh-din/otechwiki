"use client";
import { useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Search, Loader2, Zap, Database, Brain } from "lucide-react";

export default function SearchDebugPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runDebug = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await api.searchDebug(query);
      setResult(data);
    } catch (e: any) {
      setResult({ error: e.message });
    }
    setLoading(false);
  };

  return (
    <AppLayout>
      <div style={{ padding: "2rem", maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
          <Zap size={28} color="var(--color-accent)" />
          <div>
            <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700 }}>Search Debug</h1>
            <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
              Kiểm tra canonical vs legacy search hit
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runDebug()}
            placeholder="Nhập câu hỏi test, ví dụ: Giá Roborock F25 Ultra?"
            style={{
              flex: 1, padding: "0.75rem 1rem", borderRadius: 8,
              border: "1px solid var(--color-border)", background: "var(--color-surface)",
              color: "var(--color-text)", fontSize: "0.9rem",
            }}
          />
          <button
            onClick={runDebug}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: "0.4rem",
              padding: "0.75rem 1.5rem", borderRadius: 8, border: "none",
              background: "var(--color-accent)", color: "#fff",
              cursor: "pointer", fontSize: "0.9rem", fontWeight: 600,
            }}
          >
            {loading ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <Search size={16} />}
            Debug
          </button>
        </div>

        {/* Results */}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {result.error ? (
              <div className="card" style={{ padding: "1rem", color: "#ef4444" }}>Error: {result.error}</div>
            ) : (
              <>
                {/* Query Analysis */}
                <div className="card" style={{ padding: "1rem" }}>
                  <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Search size={16} /> Query Analysis
                  </h3>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.5rem", fontSize: "0.8rem" }}>
                    <div><strong>Intent:</strong> <span style={{ color: "var(--color-accent)" }}>{result.analysis?.intent}</span></div>
                    <div><strong>Corrected:</strong> {result.analysis?.corrected_query || "—"}</div>
                    <div><strong>Products:</strong> {result.analysis?.detected_products?.join(", ") || "—"}</div>
                    <div><strong>Keywords:</strong> {result.analysis?.expanded_keywords?.slice(0, 5).join(", ")}</div>
                  </div>
                </div>

                {/* Canonical Hit */}
                <div className="card" style={{ padding: "1rem", border: result.canonical?.hit ? "2px solid #10b981" : "1px solid var(--color-border)" }}>
                  <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Brain size={16} color={result.canonical?.hit ? "#10b981" : "var(--color-text-muted)"} />
                    Canonical (Structured JSON)
                    <span style={{
                      padding: "0.15rem 0.5rem", borderRadius: 10, fontSize: "0.7rem", fontWeight: 700,
                      background: result.canonical?.hit ? "rgba(16,185,129,0.15)" : "rgba(107,114,128,0.15)",
                      color: result.canonical?.hit ? "#10b981" : "#6b7280",
                    }}>
                      {result.canonical?.hit ? "HIT" : "MISS"}
                    </span>
                  </h3>
                  {result.canonical?.data && (
                    <div style={{ fontSize: "0.8rem" }}>
                      <div><strong>Product:</strong> {result.canonical.data.product}</div>
                      <div><strong>Intent matched:</strong> {result.canonical.data.intent}</div>
                      <div><strong>Context length:</strong> {result.canonical.data.context_length} chars</div>
                      <pre style={{
                        marginTop: "0.5rem", padding: "0.75rem", borderRadius: 6,
                        background: "var(--color-bg)", fontSize: "0.7rem", overflow: "auto",
                        maxHeight: 200, border: "1px solid var(--color-border)",
                      }}>
                        {result.canonical.data.preview}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Legacy Chunks */}
                <div className="card" style={{ padding: "1rem" }}>
                  <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Database size={16} color="#f59e0b" />
                    Legacy (Vector + Keyword)
                    <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", fontWeight: 400 }}>
                      {result.legacy?.chunk_count} chunks
                    </span>
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {result.legacy?.chunks?.map((chunk: any, i: number) => (
                      <div key={i} style={{
                        padding: "0.5rem 0.75rem", borderRadius: 6, fontSize: "0.75rem",
                        background: "var(--color-bg)", border: "1px solid var(--color-border)",
                      }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                          <strong>{chunk.document_title}</strong>
                          <span style={{ color: "#f59e0b", fontWeight: 600 }}>RRF: {chunk.score}</span>
                        </div>
                        <div style={{ color: "var(--color-text-muted)" }}>{chunk.snippet}...</div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        <style jsx>{`
          @keyframes spin { to { transform: rotate(360deg); } }
        `}</style>
      </div>
    </AppLayout>
  );
}

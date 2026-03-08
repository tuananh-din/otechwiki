"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Settings, Loader2, CheckCircle2, RefreshCw, Save, Database } from "lucide-react";

export default function AutocompleteConfigPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [jsonText, setJsonText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [message, setMessage] = useState("");

  const loadEntries = async () => {
    setLoading(true);
    try {
      const data = await api.getAutocompleteEntries();
      setEntries(data);
      setJsonText(JSON.stringify(data.map((e: any) => ({
        category: e.category, query: e.query, intent: e.intent || "", priority: e.priority,
      })), null, 2));
    } catch (err: any) { setMessage(`❌ ${err.message}`); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadEntries(); }, []);

  const handleSave = async () => {
    setSaving(true); setMessage("");
    try {
      const parsed = JSON.parse(jsonText);
      if (!Array.isArray(parsed)) throw new Error("Must be a JSON array");
      const res = await api.saveAutocompleteEntries(parsed);
      setMessage(`✅ Đã lưu ${res.saved} entries`);
      await loadEntries();
    } catch (err: any) { setMessage(`❌ ${err.message}`); }
    finally { setSaving(false); }
  };

  const handleSeed = async () => {
    setSeeding(true); setMessage("");
    try {
      const res = await api.seedAutocomplete();
      setMessage(`✅ Đã tạo ${res.entries_created} entries từ ${res.products} sản phẩm`);
      await loadEntries();
    } catch (err: any) { setMessage(`❌ ${err.message}`); }
    finally { setSeeding(false); }
  };

  if (loading) return <AppLayout><div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}><Loader2 size={32} className="spinner" /></div></AppLayout>;

  return (
    <AppLayout>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1>Autocomplete Config</h1>
          <p>Quản lý gợi ý tìm kiếm (0 token cost)</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-ghost" onClick={handleSeed} disabled={seeding}>
            {seeding ? <><Loader2 size={16} className="spinner" /> Seeding...</> : <><Database size={16} /> Seed từ sản phẩm</>}
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? <><Loader2 size={16} className="spinner" /> Đang lưu...</> : <><Save size={16} /> Lưu</>}
          </button>
        </div>
      </div>

      {message && (
        <div className="card" style={{
          marginBottom: "1rem", fontSize: "0.875rem",
          background: message.startsWith("✅") ? "#F0FDF4" : "#FEF2F2",
          borderColor: message.startsWith("✅") ? "#BBF7D0" : "#FECACA",
        }}>
          {message}
        </div>
      )}

      {/* Stats */}
      <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
        {["curated", "product", "popular"].map(cat => {
          const count = entries.filter(e => e.category === cat).length;
          return (
            <div className="stat-card" key={cat}>
              <div className="stat-value">{count}</div>
              <div className="stat-label">{cat === "curated" ? "Gợi ý" : cat === "product" ? "Sản phẩm" : "Phổ biến"}</div>
            </div>
          );
        })}
      </div>

      {/* JSON Editor */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Settings size={16} />
          <strong style={{ fontSize: "0.875rem" }}>Entries JSON</strong>
          <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginLeft: "auto" }}>
            {entries.length} entries
          </span>
        </div>
        <textarea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          style={{
            width: "100%", minHeight: 400, padding: "1rem",
            fontFamily: "monospace", fontSize: "0.8125rem",
            border: "none", outline: "none", resize: "vertical",
            background: "var(--color-surface)",
          }}
          spellCheck={false}
        />
      </div>

      <div style={{ marginTop: "1rem", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
        <strong>Format:</strong> {`[{"category": "curated|product|popular", "query": "text", "intent": "gia_ban|bao_hanh|so_sanh|tinh_nang|thong_so|mua_hang", "priority": 1-10}]`}
      </div>
    </AppLayout>
  );
}

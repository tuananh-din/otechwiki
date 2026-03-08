"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Upload, Globe, Search as SearchIcon, Loader2, CheckCircle2, Radar, RefreshCw } from "lucide-react";

export default function DataSourcesPage() {
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfTitle, setPdfTitle] = useState("");
  const [pdfDocType, setPdfDocType] = useState("product_spec");
  const [webUrl, setWebUrl] = useState("");
  const [webTitle, setWebTitle] = useState("");
  const [webDocType, setWebDocType] = useState("company_info");
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [message, setMessage] = useState("");
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProducts, setSelectedProducts] = useState<string>("");
  const [discoverUrl, setDiscoverUrl] = useState("");
  const [discoveredItems, setDiscoveredItems] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);
  const [scanDepth, setScanDepth] = useState(2);

  // Background import state
  const [importJobId, setImportJobId] = useState<string | null>(null);
  const [importProgress, setImportProgress] = useState<any>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => { api.getProducts().then(setProducts).catch(() => {}); }, []);

  // Cleanup polling on unmount
  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current); }; }, []);

  const docTypes = ["product_spec", "faq", "policy", "company_info", "troubleshooting", "warranty", "comparison", "manual"];

  const handleUploadPdf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfFile || !pdfTitle) return;
    setUploading(true); setMessage("");
    try {
      const form = new FormData();
      form.append("file", pdfFile); form.append("title", pdfTitle);
      form.append("document_type", pdfDocType); form.append("product_ids", selectedProducts);
      const res = await api.uploadPdf(form);
      setMessage(`Upload thành công! ${res.chunks_created} đoạn nội dung đã được tạo.`);
      setPdfFile(null); setPdfTitle("");
    } catch (err: any) { setMessage(`error:${err.message}`); } finally { setUploading(false); }
  };

  const handleIngestWeb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webUrl || !webTitle) return;
    setIngesting(true); setMessage("");
    try {
      const form = new FormData();
      form.append("url", webUrl); form.append("title", webTitle);
      form.append("document_type", webDocType); form.append("product_ids", selectedProducts);
      const res = await api.ingestWeb(form);
      setMessage(`Ingest thành công! ${res.chunks_created} đoạn nội dung đã được tạo.`);
      setWebUrl(""); setWebTitle("");
    } catch (err: any) { setMessage(`error:${err.message}`); } finally { setIngesting(false); }
  };

  const handleScanUrls = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!discoverUrl) return;
    setScanning(true); setDiscoveredItems([]); setMessage("");
    try {
      const form = new FormData();
      form.append("homepage_url", discoverUrl); form.append("limit", "200"); form.append("depth", scanDepth.toString());
      const res = await api.scanUrls(form);
      setDiscoveredItems(res.map((item: any) => ({ ...item, selected: !item.exists })));
      if (res.length === 0) setMessage("Không tìm thấy sub-pages nào.");
    } catch (err: any) { setMessage(`error:Lỗi quét URL: ${err.message}`); } finally { setScanning(false); }
  };

  const pollImportJob = useCallback((jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const job = await api.getImportJob(jobId);
        setImportProgress(job);
        if (job.status === "done") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          const successCount = job.results.filter((r: any) => r.status === "success").length;
          const errorCount = job.errors.length;
          setMessage(`Import hoàn tất! ✅ ${successCount} thành công${errorCount > 0 ? `, ❌ ${errorCount} lỗi` : ""}.`);
          setImportJobId(null);
          setDiscoveredItems([]);
          setDiscoverUrl("");
        }
      } catch { /* ignore polling errors */ }
    }, 2000);
  }, []);

  const handleBulkImport = async () => {
    const toImport = discoveredItems.filter(item => item.selected).map(item => item.url);
    if (toImport.length === 0) return;
    setMessage("");
    try {
      const res = await api.startImport({
        urls: toImport,
        document_type: webDocType,
        product_ids: selectedProducts ? selectedProducts.split(",").map(id => parseInt(id.trim())) : [],
        reimport: true,
      });
      setImportJobId(res.job_id);
      setImportProgress({ status: "running", total: res.total, completed: 0, current_url: "", results: [], errors: [] });
      pollImportJob(res.job_id);
    } catch (err: any) { setMessage(`error:Lỗi bắt đầu import: ${err.message}`); }
  };

  const toggleSelect = (url: string) => {
    setDiscoveredItems(prev => prev.map(item => item.url === url ? { ...item, selected: !item.selected } : item));
  };

  const toggleSelectAll = () => {
    const selectableItems = discoveredItems.filter(i => !i.exists);
    const allSelected = selectableItems.every(i => i.selected);
    setDiscoveredItems(prev => prev.map(item => item.exists ? item : { ...item, selected: !allSelected }));
  };

  const isError = message.startsWith("error:");
  const displayMsg = isError ? message.slice(6) : message;
  const selectedCount = discoveredItems.filter(i => i.selected).length;
  const isImporting = !!importJobId;

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Nguồn dữ liệu</h1>
        <p>Upload tài liệu hoặc crawl trang web để nạp vào hệ thống</p>
      </div>

      {message && (
        <div className="card" style={{
          marginBottom: "1.5rem",
          background: isError ? "#FEF2F2" : "#F0FDF4",
          borderColor: isError ? "#FECACA" : "#BBF7D0",
          display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem",
        }}>
          {isError ? <span style={{ color: "var(--color-error)" }}>✕</span> : <CheckCircle2 size={16} style={{ color: "var(--color-success)" }} />}
          {displayMsg}
        </div>
      )}

      <div className="grid-2" style={{ gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* Upload PDF */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <Upload size={18} style={{ color: "var(--color-primary)" }} />
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Upload Tài liệu</h3>
          </div>
          <form onSubmit={handleUploadPdf}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Tiêu đề *</label>
              <input className="input" value={pdfTitle} onChange={(e) => setPdfTitle(e.target.value)} placeholder="Tên tài liệu" required />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>File (PDF, PPTX) *</label>
              <input className="input" type="file" accept=".pdf,.pptx" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} required style={{ padding: "0.5rem" }} />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Loại tài liệu</label>
              <select className="filter-select" style={{ width: "100%" }} value={pdfDocType} onChange={(e) => setPdfDocType(e.target.value)}>
                {docTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" type="submit" disabled={uploading} style={{ width: "100%", justifyContent: "center" }}>
              {uploading ? <><Loader2 size={16} className="spinner" /> Đang xử lý...</> : <><Upload size={16} /> Upload & Ingest</>}
            </button>
          </form>
        </div>

        {/* Ingest Web */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <Globe size={18} style={{ color: "var(--color-primary)" }} />
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Ingest Web Page</h3>
          </div>
          <form onSubmit={handleIngestWeb}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Tiêu đề *</label>
              <input className="input" value={webTitle} onChange={(e) => setWebTitle(e.target.value)} placeholder="Tên trang web" required />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>URL *</label>
              <input className="input" type="url" value={webUrl} onChange={(e) => setWebUrl(e.target.value)} placeholder="https://..." required />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Loại tài liệu</label>
              <select className="filter-select" style={{ width: "100%" }} value={webDocType} onChange={(e) => setWebDocType(e.target.value)}>
                {docTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" type="submit" disabled={ingesting} style={{ width: "100%", justifyContent: "center" }}>
              {ingesting ? <><Loader2 size={16} className="spinner" /> Đang xử lý...</> : <><Globe size={16} /> Crawl & Ingest</>}
            </button>
          </form>
        </div>
      </div>

      {/* Bulk Discovery */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <Radar size={18} style={{ color: "var(--color-primary)" }} />
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Web Discovery & Bulk Import</h3>
        </div>
        <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginBottom: "1rem" }}>
          Nhập trang chủ website để tự động tìm tối đa 200 trang con. URL đã có sẽ tự động xoá &amp; re-import.
        </p>

        <form onSubmit={handleScanUrls} className="search-form-row" style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Trang chủ URL</label>
            <input className="input" type="url" value={discoverUrl} onChange={(e) => setDiscoverUrl(e.target.value)} placeholder="https://example.com" required />
          </div>
          <div style={{ width: 130 }}>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Độ sâu</label>
            <select className="filter-select" style={{ width: "100%" }} value={scanDepth} onChange={(e) => setScanDepth(parseInt(e.target.value))}>
              <option value={1}>1 (Nhanh)</option>
              <option value={2}>2 (Sâu)</option>
              <option value={3}>3 (Rất sâu)</option>
            </select>
          </div>
          <button className="btn btn-primary" type="submit" disabled={scanning || isImporting}>
            {scanning ? <><Loader2 size={16} className="spinner" /> Đang quét...</> : <><SearchIcon size={16} /> Quét Website</>}
          </button>
        </form>

        {/* Import Progress Bar */}
        {isImporting && importProgress && (
          <div style={{ marginBottom: "1.5rem", padding: "1rem", background: "var(--color-surface-hover)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "0.875rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Loader2 size={16} className="spinner" /> Đang import...
              </span>
              <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--color-primary)" }}>
                {importProgress.completed}/{importProgress.total}
              </span>
            </div>
            <div style={{ width: "100%", height: "8px", background: "var(--color-border)", borderRadius: "4px", overflow: "hidden" }}>
              <div style={{
                width: `${(importProgress.completed / importProgress.total) * 100}%`,
                height: "100%",
                background: "var(--color-primary)",
                borderRadius: "4px",
                transition: "width 0.3s ease",
              }} />
            </div>
            {importProgress.current_url && (
              <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.5rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                → {importProgress.current_url}
              </p>
            )}
          </div>
        )}

        {discoveredItems.length > 0 && (
          <div style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
            <div style={{ maxHeight: 400, overflowY: "auto" }}>
              {discoveredItems.map((item) => (
                <div key={item.url} style={{
                  display: "flex", alignItems: "center", gap: "0.75rem",
                  padding: "0.625rem 0.75rem", borderBottom: "1px solid var(--color-border)",
                  fontSize: "0.8125rem", background: item.exists ? "var(--color-surface-hover)" : "transparent",
                }}>
                  <input
                    type="checkbox" checked={item.selected}
                    disabled={isImporting}
                    onChange={() => toggleSelect(item.url)}
                    style={{ cursor: "pointer" }}
                  />
                  <span style={{ flex: 1, color: item.exists ? "var(--color-text-muted)" : "inherit", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.url}
                  </span>
                  {item.exists ? (
                    <span className="badge" style={{ background: "#FEF3C7", color: "#92400E", fontSize: "0.7rem" }}>
                      <RefreshCw size={10} style={{ marginRight: "2px" }} /> Re-import
                    </span>
                  ) : (
                    <span className="badge badge-primary">Mới</span>
                  )}
                </div>
              ))}
            </div>
            <div style={{
              padding: "0.75rem 1rem", background: "var(--color-surface-hover)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <label style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <input type="checkbox" onChange={toggleSelectAll} checked={discoveredItems.filter(i => !i.exists).every(i => i.selected) && discoveredItems.filter(i => !i.exists).length > 0} disabled={isImporting} />
                  Chọn tất cả
                </label>
                <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                  Đã chọn {selectedCount} trang
                </span>
              </div>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleBulkImport}
                disabled={isImporting || selectedCount === 0}
              >
                {isImporting ? <><Loader2 size={14} className="spinner" /> Đang Import...</> : `Import ${selectedCount} trang`}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

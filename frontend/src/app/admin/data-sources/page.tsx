"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";

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
  
  // Bulk Web Ingestion State
  const [discoverUrl, setDiscoverUrl] = useState("");
  const [discoveredItems, setDiscoveredItems] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);
  const [bulkIngesting, setBulkIngesting] = useState(false);
  const [bulkProgress, setBulkProgress] = useState({ current: 0, total: 0 });
  const [scanDepth, setScanDepth] = useState(2);

  useEffect(() => { api.getProducts().then(setProducts).catch(() => {}); }, []);

  const docTypes = ["product_spec", "faq", "policy", "company_info", "troubleshooting", "warranty", "comparison", "manual"];

  const handleUploadPdf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfFile || !pdfTitle) return;
    setUploading(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", pdfFile);
      form.append("title", pdfTitle);
      form.append("document_type", pdfDocType);
      form.append("product_ids", selectedProducts);
      const res = await api.uploadPdf(form);
      setMessage(`✅ Upload thành công! ${res.chunks_created} đoạn nội dung đã được tạo.`);
      setPdfFile(null);
      setPdfTitle("");
    } catch (err: any) {
      setMessage(`❌ Lỗi: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleIngestWeb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webUrl || !webTitle) return;
    setIngesting(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("url", webUrl);
      form.append("title", webTitle);
      form.append("document_type", webDocType);
      form.append("product_ids", selectedProducts);
      const res = await api.ingestWeb(form);
      setMessage(`✅ Ingest thành công! ${res.chunks_created} đoạn nội dung đã được tạo.`);
      setWebUrl("");
      setWebTitle("");
    } catch (err: any) {
      setMessage(`❌ Lỗi: ${err.message}`);
    } finally {
      setIngesting(false);
    }
  };

  const handleScanUrls = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!discoverUrl) return;
    setScanning(true);
    setDiscoveredItems([]);
    setMessage("");
    try {
      const form = new FormData();
      form.append("homepage_url", discoverUrl);
      form.append("limit", "60");
      form.append("depth", scanDepth.toString());
      const res = await api.scanUrls(form);
      setDiscoveredItems(res.map(item => ({ ...item, selected: !item.exists })));
      if (res.length === 0) setMessage("ℹ️ Không tìm thấy sub-pages nào.");
    } catch (err: any) {
      setMessage(`❌ Lỗi quét URL: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  const handleBulkIngest = async () => {
    const toIngest = discoveredItems.filter(item => item.selected).map(item => item.url);
    if (toIngest.length === 0) return;

    setBulkIngesting(true);
    setMessage("");
    setBulkProgress({ current: 0, total: toIngest.length });

    try {
      const res = await api.bulkIngestWeb({
        urls: toIngest,
        document_type: webDocType,
        product_ids: selectedProducts ? selectedProducts.split(",").map(id => parseInt(id.trim())) : []
      });
      setMessage(`✅ Đã xử lý xong! Thành công: ${res.success}/${res.processed}.`);
      setDiscoveredItems([]);
      setDiscoverUrl("");
    } catch (err: any) {
      setMessage(`❌ Lỗi Bulk Ingest: ${err.message}`);
    } finally {
      setBulkIngesting(false);
    }
  };

  const toggleSelect = (url: string) => {
    setDiscoveredItems(prev => prev.map(item => 
      item.url === url ? { ...item, selected: !item.selected } : item
    ));
  };

  return (
    <AppLayout>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1.5rem" }}>📁 Nguồn dữ liệu</h1>

      {message && (
        <div className="card" style={{ marginBottom: "1.5rem", background: message.startsWith("✅") ? "#f0fdf4" : "#fef2f2" }}>
          {message}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Upload Document */}
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>📄 Upload Tài liệu</h3>
          <form onSubmit={handleUploadPdf}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Tiêu đề *</label>
              <input className="input" value={pdfTitle} onChange={(e) => setPdfTitle(e.target.value)} placeholder="Tên tài liệu" required />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>File (PDF, PPTX) *</label>
              <input type="file" accept=".pdf,.pptx" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} required />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Loại tài liệu</label>
              <select className="filter-select" style={{ width: "100%" }} value={pdfDocType} onChange={(e) => setPdfDocType(e.target.value)}>
                {docTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" type="submit" disabled={uploading} style={{ width: "100%", justifyContent: "center" }}>
              {uploading ? "Đang xử lý..." : "Upload & Ingest"}
            </button>
          </form>
        </div>

        {/* Ingest Web */}
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>🌐 Ingest Web Page</h3>
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
              {ingesting ? "Đang xử lý..." : "Crawl & Ingest"}
            </button>
          </form>
        </div>
      </div>

      {/* Web Discovery Section */}
      <div className="card" style={{ marginTop: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>🔍 Web Discovery & Bulk Ingest</h3>
        <p style={{ fontSize: "0.8125rem", color: "#6b7280", marginBottom: "1rem" }}>
          Nhập trang chủ website để tự động tìm các trang con và chọn trang cần nạp vào dữ liệu.
        </p>
        
        <form onSubmit={handleScanUrls} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Trang chủ URL</label>
            <input 
              className="input" 
              type="url" 
              value={discoverUrl} 
              onChange={(e) => setDiscoverUrl(e.target.value)} 
              placeholder="https://example.com" 
              required 
              style={{ width: "100%" }}
            />
          </div>
          <div style={{ width: "120px" }}>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.375rem" }}>Độ sâu (Depth)</label>
            <select 
              className="filter-select" 
              style={{ width: "100%" }} 
              value={scanDepth} 
              onChange={(e) => setScanDepth(parseInt(e.target.value))}
            >
              <option value={1}>1 (Nhanh)</option>
              <option value={2}>2 (Sâu)</option>
              <option value={3}>3 (Rất sâu)</option>
            </select>
          </div>
          <button className="btn btn-secondary" type="submit" disabled={scanning || bulkIngesting}>
            {scanning ? "Đang quét..." : "Quét Website"}
          </button>
        </form>

        {discoveredItems.length > 0 && (
          <div style={{ border: "1px solid #e5e7eb", borderRadius: "0.5rem", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
              <thead style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <tr>
                  <th style={{ padding: "0.75rem", textAlign: "left", width: "40px" }}>Chọn</th>
                  <th style={{ padding: "0.75rem", textAlign: "left" }}>URL</th>
                  <th style={{ padding: "0.75rem", textAlign: "left", width: "100px" }}>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {discoveredItems.map((item) => (
                  <tr key={item.url} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "0.75rem", textAlign: "center" }}>
                      <input 
                        type="checkbox" 
                        checked={item.selected} 
                        disabled={item.exists || bulkIngesting}
                        onChange={() => toggleSelect(item.url)}
                      />
                    </td>
                    <td style={{ padding: "0.75rem", color: item.exists ? "#9ca3af" : "inherit" }}>{item.url}</td>
                    <td style={{ padding: "0.75rem" }}>
                      {item.exists ? <span style={{ color: "#10b981" }}>Đã có</span> : <span style={{ color: "#6b7280" }}>Mới</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ padding: "1rem", background: "#f9fafb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>
                Đã chọn {discoveredItems.filter(i => i.selected).length} trang
              </div>
              <button 
                className="btn btn-primary" 
                onClick={handleBulkIngest} 
                disabled={bulkIngesting || discoveredItems.filter(i => i.selected).length === 0}
              >
                {bulkIngesting ? `Đang Ingest...` : "Bắt đầu Bulk Ingest"}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

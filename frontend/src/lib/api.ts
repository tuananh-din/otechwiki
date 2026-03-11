const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }

  return res.json();
}

// Auth
export const api = {
  login: (username: string, password: string) =>
    apiFetch<{ access_token: string; user: any }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getMe: () => apiFetch<any>("/api/auth/me"),

  // Search
  search: (query: string, filters?: { product_filter?: string; doc_type_filter?: string }) =>
    apiFetch<any>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, search_type: "hybrid", limit: 10, ...filters }),
    }),

  ask: (query: string, filters?: { product_filter?: string; doc_type_filter?: string }) =>
    apiFetch<any>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ query, ...filters }),
    }),

  recentSearches: () => apiFetch<any[]>("/api/recent-searches"),

  // Products
  getProducts: () => apiFetch<any[]>("/api/products"),
  getProduct: (slug: string) => apiFetch<any>(`/api/products/${slug}`),

  // Documents
  getDocuments: () => apiFetch<any[]>("/api/documents"),
  getDocument: (id: number) => apiFetch<any>(`/api/documents/${id}`),

  // Admin
  uploadPdf: (form: FormData) =>
    apiFetch<any>("/api/admin/upload-document", { method: "POST", body: form }),

  ingestWeb: (form: FormData) =>
    apiFetch<any>("/api/admin/ingest-web", { method: "POST", body: form }),

  getAnalytics: () => apiFetch<any>("/api/admin/analytics"),

  scanUrls: (form: FormData) =>
    apiFetch<any[]>("/api/admin/scan-urls", { method: "POST", body: form }),

  bulkIngestWeb: (data: { urls: string[]; document_type?: string; product_ids?: number[] }) =>
    apiFetch<any>("/api/admin/bulk-ingest-web", { method: "POST", body: JSON.stringify(data) }),

  createProduct: (data: { name: string; slug: string; description?: string; category?: string }) =>
    apiFetch<any>("/api/products", { method: "POST", body: JSON.stringify(data) }),

  createUser: (data: { username: string; password: string; full_name?: string; is_admin?: boolean }) =>
    apiFetch<any>("/api/auth/users", { method: "POST", body: JSON.stringify(data) }),

  deleteDocument: (id: number) =>
    apiFetch<any>(`/api/documents/${id}`, { method: "DELETE" }),

  deleteDocuments: (ids: number[]) =>
    apiFetch<any>("/api/documents/bulk-delete", { method: "POST", body: JSON.stringify({ ids }) }),

  startImport: (data: { urls: string[]; document_type?: string; product_ids?: number[]; reimport?: boolean }) =>
    apiFetch<{ job_id: string; total: number }>("/api/admin/start-import", { method: "POST", body: JSON.stringify(data) }),

  getImportJob: (jobId: string) =>
    apiFetch<any>(`/api/admin/import-job/${jobId}`),

  autoMap: () =>
    apiFetch<any>("/api/admin/auto-map", { method: "POST" }),

  getProductMatrix: () =>
    apiFetch<any>("/api/admin/product-matrix"),

  autocomplete: (q: string) =>
    apiFetch<any[]>(`/api/autocomplete?q=${encodeURIComponent(q)}`),

  getAutocompleteEntries: () =>
    apiFetch<any[]>("/api/admin/autocomplete-entries"),

  saveAutocompleteEntries: (entries: any[]) =>
    apiFetch<any>("/api/admin/autocomplete-entries", {
      method: "POST",
      body: JSON.stringify({ entries }),
    }),

  seedAutocomplete: () =>
    apiFetch<any>("/api/admin/seed-autocomplete", { method: "POST" }),

  // V2 Pipeline
  cleaningStats: () =>
    apiFetch<any>("/api/admin/cleaning-stats"),

  reprocessDocument: (docId: number) =>
    apiFetch<any>(`/api/admin/reprocess/${docId}`, { method: "POST" }),

  reprocessAll: () =>
    apiFetch<any>("/api/admin/reprocess-all", { method: "POST" }),

  // Knowledge Architecture V1
  extractKnowledge: (productId: number, types: string = "specs,pricing,faq") =>
    apiFetch<any>(`/api/admin/knowledge/extract?product_id=${productId}&extract_types=${types}`, { method: "POST" }),

  batchExtractKnowledge: (productIds: number[], types: string = "specs,pricing,faq") =>
    apiFetch<any>("/api/admin/knowledge/batch-extract?extract_types=" + types, {
      method: "POST", body: JSON.stringify(productIds),
    }),

  getKnowledgeDrafts: (docType?: string) =>
    apiFetch<any>(`/api/admin/knowledge/drafts${docType ? `?doc_type=${docType}` : ""}`),

  getKnowledgeDraft: (docType: string, filename: string) =>
    apiFetch<any>(`/api/admin/knowledge/draft/${docType}/${filename}`),

  promoteKnowledgeDraft: (docType: string, filename: string) =>
    apiFetch<any>(`/api/admin/knowledge/promote/${docType}/${filename}`, { method: "POST" }),

  rejectKnowledgeDraft: (docType: string, filename: string, reason: string = "") =>
    apiFetch<any>(`/api/admin/knowledge/reject/${docType}/${filename}?reason=${encodeURIComponent(reason)}`, { method: "POST" }),

  archiveKnowledgeDraft: (docType: string, filename: string) =>
    apiFetch<any>(`/api/admin/knowledge/archive/${docType}/${filename}`, { method: "POST" }),

  getKnowledgeInventory: () =>
    apiFetch<any>("/api/admin/knowledge/inventory"),
};

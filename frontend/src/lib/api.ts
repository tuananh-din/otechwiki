const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
};

"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { BookOpen, ArrowRight, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(username, password);
      setToken(res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-branding">
        <div style={{
          width: 72, height: 72, borderRadius: 16,
          background: "rgba(255,255,255,0.15)", backdropFilter: "blur(12px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: "1.5rem",
        }}>
          <BookOpen size={36} />
        </div>
        <h1>Knowledge Search</h1>
        <p>Hệ thống tra cứu kiến thức sản phẩm nội bộ dành cho Customer Service. Tìm kiếm nhanh, trả lời thông minh.</p>
      </div>

      <div className="login-form-section">
        <div className="login-form-card">
          <div style={{ marginBottom: "2rem" }}>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.375rem" }}>Đăng nhập</h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
              Nhập thông tin tài khoản để truy cập
            </p>
          </div>

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: "1.25rem" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "var(--color-text)" }}>
                Tên đăng nhập
              </label>
              <input
                className="input"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập tên đăng nhập"
                required
                autoFocus
              />
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "var(--color-text)" }}>
                Mật khẩu
              </label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu"
                required
              />
            </div>

            {error && (
              <div style={{
                color: "var(--color-error)", fontSize: "0.875rem",
                marginBottom: "1rem", padding: "0.75rem",
                background: "#FEF2F2", borderRadius: 8, textAlign: "center",
              }}>
                {error}
              </div>
            )}

            <button className="btn btn-primary btn-lg" type="submit" disabled={loading} style={{ width: "100%" }}>
              {loading ? <Loader2 size={20} className="spinner" /> : <><span>Đăng nhập</span><ArrowRight size={18} /></>}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

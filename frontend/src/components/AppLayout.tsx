"use client";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { clearToken } from "@/lib/api";

const navItems = [
  { href: "/", label: "🔍 Tìm kiếm", icon: "search" },
  { href: "/products", label: "📦 Sản phẩm", icon: "products" },
  { href: "/documents", label: "📄 Tài liệu", icon: "documents" },
  { href: "/recent", label: "🕐 Gần đây", icon: "recent" },
];

const adminItems = [
  { href: "/admin", label: "📊 Dashboard", icon: "dashboard" },
  { href: "/admin/data-sources", label: "📁 Nguồn dữ liệu", icon: "data" },
  { href: "/admin/analytics", label: "📈 Analytics", icon: "analytics" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    const u = localStorage.getItem("user");
    if (u) setUser(JSON.parse(u));
  }, [router]);

  const handleLogout = () => {
    clearToken();
    localStorage.removeItem("user");
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div>
      <div className="sidebar">
        <div style={{ padding: "0 1.5rem", marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: 0 }}>🔍 Knowledge</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", margin: "0.25rem 0 0" }}>Tra cứu sản phẩm</p>
        </div>

        <nav>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${pathname === item.href ? "active" : ""}`}
            >
              {item.label}
            </Link>
          ))}

          {user.is_admin && (
            <>
              <div style={{ margin: "1.5rem 1.5rem 0.5rem", fontSize: "0.6875rem", textTransform: "uppercase", color: "var(--color-text-muted)", fontWeight: 600, letterSpacing: "0.05em" }}>
                Admin
              </div>
              {adminItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-link ${pathname === item.href ? "active" : ""}`}
                >
                  {item.label}
                </Link>
              ))}
            </>
          )}
        </nav>

        <div style={{ position: "absolute", bottom: "1rem", left: 0, right: 0, padding: "0 1.5rem" }}>
          <div style={{ fontSize: "0.8125rem", fontWeight: 500 }}>{user.full_name || user.username}</div>
          <button onClick={handleLogout} style={{ background: "none", border: "none", color: "var(--color-text-muted)", fontSize: "0.75rem", cursor: "pointer", padding: 0, marginTop: "0.25rem" }}>
            Đăng xuất
          </button>
        </div>
      </div>

      <div className="main-content">{children}</div>
    </div>
  );
}

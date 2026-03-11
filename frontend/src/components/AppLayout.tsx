"use client";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { clearToken } from "@/lib/api";
import {
  Search, Package, FileText, Clock, LayoutDashboard,
  Database, BarChart3, LogOut, Menu, X, BookOpen, Grid3x3, Sparkles, Paintbrush, Brain,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Tìm kiếm", icon: Search },
  { href: "/products", label: "Sản phẩm", icon: Package },
  { href: "/documents", label: "Tài liệu", icon: FileText },
  { href: "/recent", label: "Gần đây", icon: Clock },
];

const adminItems = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/data-sources", label: "Nguồn dữ liệu", icon: Database },
  { href: "/admin/product-mapping", label: "Product Mapping", icon: Grid3x3 },
  { href: "/admin/cleaning-dashboard", label: "Cleaning Pipeline", icon: Paintbrush },
  { href: "/admin/knowledge", label: "Knowledge Base", icon: Brain },
  { href: "/admin/autocomplete-config", label: "Autocomplete", icon: Sparkles },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    const u = localStorage.getItem("user");
    if (u) setUser(JSON.parse(u));
  }, [router]);

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  useEffect(() => {
    if (menuOpen) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  const handleLogout = () => {
    clearToken();
    localStorage.removeItem("user");
    router.push("/login");
  };

  if (!user) return null;

  const initials = (user.full_name || user.username || "U").split(" ").map((s: string) => s[0]).join("").slice(0, 2).toUpperCase();

  const SidebarContent = () => (
    <>
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <BookOpen size={20} />
        </div>
        <div>
          <h2>Knowledge</h2>
          <p>Tra cứu sản phẩm</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className={`sidebar-link ${pathname === item.href ? "active" : ""}`}>
              <Icon size={20} />
              {item.label}
            </Link>
          );
        })}

        {user.is_admin && (
          <>
            <div className="sidebar-section-label">Admin</div>
            {adminItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className={`sidebar-link ${pathname === item.href ? "active" : ""}`}>
                  <Icon size={20} />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-avatar">{initials}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">{user.full_name || user.username}</div>
        </div>
        <button onClick={handleLogout} className="sidebar-logout" title="Đăng xuất">
          <LogOut size={18} />
        </button>
      </div>
    </>
  );

  return (
    <div>
      {/* Mobile topbar */}
      <div className="mobile-topbar">
        <button className="mobile-menu-btn" onClick={() => setMenuOpen(true)}>
          <Menu size={22} />
        </button>
        <div className="sidebar-logo-icon" style={{ width: 32, height: 32 }}>
          <BookOpen size={16} />
        </div>
        <h2 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Knowledge</h2>
      </div>

      {/* Overlay */}
      <div className={`sidebar-overlay ${menuOpen ? "active" : ""}`} onClick={() => setMenuOpen(false)} />

      {/* Sidebar */}
      <div className={`sidebar ${menuOpen ? "open" : ""}`}>
        <button
          onClick={() => setMenuOpen(false)}
          style={{
            display: menuOpen ? "flex" : "none",
            position: "absolute", top: "1rem", right: "1rem",
            background: "none", border: "none", cursor: "pointer",
            color: "var(--color-text-muted)", padding: 4,
          }}
        >
          <X size={20} />
        </button>
        <SidebarContent />
      </div>

      <div className="main-content">{children}</div>
    </div>
  );
}

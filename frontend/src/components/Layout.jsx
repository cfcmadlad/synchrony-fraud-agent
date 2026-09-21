import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { BarChart3, LogOut, Menu, ShieldHalf, ListChecks, X } from "lucide-react";
import { useAuth } from "../lib/auth";

export default function Layout() {
  const { session, role, signOut } = useAuth();
  const email = session?.user?.email || "";
  const initials = email.slice(0, 2).toUpperCase();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-layout">
      <div className="mobile-topbar">
        <Link to="/queue" className="brand" onClick={() => setMobileOpen(false)}>
          <div className="brand-mark">
            <ShieldHalf size={13} />
          </div>
          <div className="brand-text">Solaris</div>
        </Link>
        <button className="icon-btn mobile-menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open menu">
          <Menu />
        </button>
      </div>
      {mobileOpen && <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <button className="icon-btn mobile-close-btn" onClick={() => setMobileOpen(false)} aria-label="Close menu">
          <X />
        </button>
        <Link to="/queue" className="brand" onClick={() => setMobileOpen(false)}>
          <div className="brand-mark">
            <ShieldHalf size={13} />
          </div>
          <div className="brand-text">
            Solaris
            <small>Real-time risk review · Synchrony hackathon</small>
          </div>
        </Link>
        <nav className="nav-links">
          <NavLink to="/queue" className={({ isActive }) => (isActive ? "active" : "")} onClick={() => setMobileOpen(false)}>
            <ListChecks />
            Risk Queue
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => (isActive ? "active" : "")} onClick={() => setMobileOpen(false)}>
            <BarChart3 />
            Analytics
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <div className="user-row">
            <div className="user-avatar">{initials}</div>
            <div className="user-meta">
              <div className="user-email">{email}</div>
              {role && <span className={`role-pill ${role === "admin" ? "admin" : ""}`}>{role}</span>}
            </div>
          </div>
          <button className="icon-btn" onClick={signOut}>
            <LogOut />
            Sign out
          </button>
        </div>
      </aside>
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
}

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Layout() {
  const { session, role, signOut } = useAuth();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          Synchrony Fraud Agent
          <small>Real-time risk review</small>
        </div>
        <nav className="nav-links">
          <NavLink to="/queue" className={({ isActive }) => (isActive ? "active" : "")}>
            Risk Queue
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => (isActive ? "active" : "")}>
            Analytics
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          {role && <span className="role-pill">{role}</span>}
          <span>{session?.user?.email}</span>
          <button onClick={signOut}>Sign out</button>
        </div>
      </aside>
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
}

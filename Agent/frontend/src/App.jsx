import React from "react";
import {
  Navigate,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { SessionProvider, useSession } from "./context/SessionContext.jsx";
import IdentityPage from "./pages/IdentityPage.jsx";
import UserHome from "./pages/UserHome.jsx";
import AdminHome from "./pages/AdminHome.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";

function RequireRole({ role, children }) {
  const { session, adminOpenAccess } = useSession();
  if (role === "admin" && adminOpenAccess) {
    return children;
  }
  if (role === "user" && adminOpenAccess) {
    return children;
  }
  if (!session || session.role !== role) {
    return <Navigate to="/" replace />;
  }
  return children;
}

function AppHeader() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get("tab") || "overview";
  const { session, logout, adminOpenAccess } = useSession();
  const navigate = useNavigate();

  React.useEffect(() => {
    if (currentTab === "overview") {
      document.title = "Nora - Risk Management";
    } else if (currentTab === "bots") {
      document.title = "Nora - Bot List";
    } else if (currentTab === "analyze") {
      document.title = "Nora - Analyze Bot";
    } else if (currentTab === "bot") {
      const code = searchParams.get("code") || "";
      document.title = code ? `Nora - Risk Management · ${code}` : "Nora - Risk Management";
    } else {
      document.title = "Nora - Risk Management";
    }
  }, [currentTab, searchParams]);

  const roleLabel = session
    ? session.role === "admin"
      ? "Admin"
      : "User"
    : adminOpenAccess
      ? "Admin"
      : "";

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  function handleTabClick(tabKey) {
    setSearchParams({ tab: tabKey });
  }

  return (
    <header className="top-header">
      <div className="header-left">
        {/* Brand & Monogram Logo */}
        <div className="brand" onClick={() => handleTabClick("overview")} style={{ cursor: "pointer" }}>
          <div className="brand-logo-box">
            {/* OKX-inspired geometric matrix glyph */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="3" width="7" height="7" rx="1.5" fill="currentColor" fillOpacity="0.95" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" fill="#38BDF8" />
            </svg>
          </div>
          <div className="brand-title-wrap">
            <div className="brand-name-row">
              <span className="brand-name">NORABT</span>
              <span className="brand-badge-fintech">AI ENGINE</span>
            </div>
            <span className="brand-sub">OKX QUANT RISK PROTOCOL</span>
          </div>
        </div>

        <div className="header-divider" />

        {/* OKX-style Segmented Control Navigation Tabs */}
        <nav className="header-nav-tabs">
          <button
            type="button"
            className={`header-tab ${currentTab === "overview" ? "on" : ""}`}
            onClick={() => handleTabClick("overview")}
          >
            <svg className="tab-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
            </svg>
            <span>Overview</span>
          </button>

          <button
            type="button"
            className={`header-tab ${currentTab === "bots" || currentTab === "bot" ? "on" : ""}`}
            onClick={() => handleTabClick("bots")}
          >
            <svg className="tab-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
            <span>Bot List</span>
          </button>

          <button
            type="button"
            className={`header-tab ${currentTab === "analyze" ? "on" : ""}`}
            onClick={() => handleTabClick("analyze")}
          >
            <svg className="tab-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <span>Analyze Bot</span>
          </button>
        </nav>
      </div>

      {/* Header Right Actions */}
      {/* Header Right Actions */}
      <div className="header-actions">

        {roleLabel && (
          <div className="user-badge-capsule">
            <span className="user-badge-pulse" />
            <span className="user-badge-label">
              {session?.userRef
                ? session.userRef
                : adminOpenAccess && !session
                  ? "ADMIN"
                  : roleLabel.toUpperCase()}
            </span>
          </div>
        )}

        <ThemeToggle />

        {session && (
          <button
            type="button"
            className="btn-logout"
            onClick={handleLogout}
            title="Log out"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span className="btn-logout-text">Log out</span>
          </button>
        )}
      </div>
    </header>
  );
}

function AppRoutes() {
  const { adminOpenAccess, configLoaded } = useSession();

  if (!configLoaded) {
    return (
      <div className="msg" style={{ marginTop: 60 }}>
        Initializing system...
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          adminOpenAccess ? <Navigate to="/admin" replace /> : <IdentityPage />
        }
      />
      <Route
        path="/user"
        element={
          <RequireRole role="user">
            <UserHome />
          </RequireRole>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireRole role="admin">
            <AdminHome />
          </RequireRole>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <SessionProvider>
      <div className="app-shell">
        <AppHeader />
        <main className="main-content">
          <AppRoutes />
        </main>
      </div>
    </SessionProvider>
  );
}

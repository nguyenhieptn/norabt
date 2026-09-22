import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext.jsx";

export default function AdminLoginPage() {
  const { session, login, adminOpenAccess } = useSession();
  const navigate = useNavigate();

  const [adminKey, setAdminKey] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // If already logged in as admin, redirect to admin console
  if (session && session.role === "admin") {
    return <Navigate to="/admin" replace />;
  }

  async function handleLogin(keyToUse) {
    const trimmed = (keyToUse || adminKey).trim();
    if (!trimmed) {
      setError("Please enter an Admin Key to continue.");
      return;
    }
    setBusy(true);
    setError(null);

    const result = await login(trimmed);
    setBusy(false);

    if (!result.ok) {
      setError(result.message || "Invalid Admin Key. Please check it and try again.");
      return;
    }

    if (result.session?.role === "admin") {
      navigate("/admin", { replace: true });
    } else {
      setError("This key does not have Admin privileges.");
    }
  }

  function handleFormSubmit(e) {
    e.preventDefault();
    handleLogin(adminKey);
  }

  function handleQuickDevAccess() {
    handleLogin("admin");
  }

  return (
    <div className="admin-login-page">
      <div className="admin-login-bg-glow" />

      <div className="admin-login-card">
        {/* Top Header & Security Badge */}
        <div className="admin-login-header">
          <div className="admin-login-brand-row">
            <div className="admin-login-logo-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="7" height="7" rx="1.5" fill="currentColor" fillOpacity="0.95" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" fill="#38BDF8" />
              </svg>
            </div>
            <div className="admin-login-brand-text">
              <span className="admin-login-brand-name">NORABT</span>
              <span className="admin-login-brand-tag">AI ENGINE</span>
            </div>
          </div>

          <div className="admin-login-badge">
            <span className="admin-login-badge-dot" />
            <span>RESTRICTED ACCESS · ADMIN CONSOLE</span>
          </div>

          <h1 className="admin-login-title">Admin Gateway</h1>
          <p className="admin-login-desc">
            A secure area reserved for system administrators to monitor quantitative risk, review verdicts, and manage OKX bots.
          </p>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="admin-login-error" role="alert">
            <span className="admin-login-error-icon">⚠️</span>
            <span className="admin-login-error-text">{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form className="admin-login-form" onSubmit={handleFormSubmit}>
          <div className="admin-login-field">
            <label htmlFor="adminKey">Admin Secret Key</label>
            <div className="admin-login-input-wrap">
              <span className="admin-login-input-icon">🔑</span>
              <input
                id="adminKey"
                type={showPassword ? "text" : "password"}
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                placeholder="Enter the admin key (Admin Key)..."
                disabled={busy}
                autoComplete="current-password"
                autoFocus
              />
              <button
                type="button"
                className="admin-login-toggle-pw"
                onClick={() => setShowPassword((prev) => !prev)}
                title={showPassword ? "Hide password" : "Show password"}
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="admin-login-submit-btn"
            disabled={busy || !adminKey.trim()}
          >
            {busy ? (
              <span className="admin-login-loading-row">
                <span className="admin-login-spinner" />
                <span>Authenticating...</span>
              </span>
            ) : (
              <span>Log in to Admin Console →</span>
            )}
          </button>

          {/* Quick Dev Access button if adminOpenAccess is true */}
          {adminOpenAccess && (
            <button
              type="button"
              className="admin-login-dev-btn"
              onClick={handleQuickDevAccess}
              disabled={busy}
            >
              ⚡ Quick Admin Access (Open Access Mode)
            </button>
          )}
        </form>

        {/* Informational Disclaimer for Users */}
        <div className="admin-login-disclaimer">
          <div className="admin-login-disclaimer-icon">ℹ️</div>
          <div className="admin-login-disclaimer-text">
            <strong>Reserved for administrators:</strong> Users &amp; investors view reports directly through a link containing the bot code &amp; contract, with no login required.
          </div>
        </div>
      </div>
    </div>
  );
}

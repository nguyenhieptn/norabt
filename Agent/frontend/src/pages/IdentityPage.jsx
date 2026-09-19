import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext.jsx";

/** "/" -- the one-field identity gate (task's màn hình 1). Accepts EITHER a
 * wallet address (0x + 40 hex) or the admin key -- app.py's own
 * POST /api/session tells the two apart server-side; this screen never
 * guesses which one was typed.
 */
export default function IdentityPage() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [identity, setIdentity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = identity.trim();
    if (!trimmed) {
      setError("Enter a wallet address or admin key first.");
      return;
    }
    setBusy(true);
    setError(null);
    const result = await login(trimmed);
    setBusy(false);
    if (!result.ok) {
      // Server's own Vietnamese message, verbatim -- never swallowed, never
      // replaced by a generic "đăng nhập thất bại" here (task's explicit
      // requirement).
      setError(result.message);
      return;
    }
    navigate(result.session.role === "admin" ? "/admin" : "/user", {
      replace: true,
    });
  }

  return (
    <div className="page">
      <header className="app-header">
        <h1 className="app-title">Agent</h1>
      </header>

      <div className="notice notice-warning">
        <strong>Note:</strong> the wallet address is a self-declared identity
        entered in the field below -- the system has NOT VERIFIED this is
        actually your wallet (there is no signature step). Do not enter any
        secret key/private key here, only enter your public WALLET ADDRESS
        (0x...).
      </div>

      {error ? <div className="notice notice-danger">{error}</div> : null}

      <form className="card" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="identity">Wallet address or admin key</label>
          <input
            id="identity"
            type="text"
            value={identity}
            onChange={(event) => setIdentity(event.target.value)}
            placeholder="0x1234... or admin key"
            disabled={busy}
            autoComplete="off"
            autoFocus
          />
        </div>
        <button type="submit" disabled={busy}>
          {busy ? "Checking..." : "Continue"}
        </button>
      </form>
    </div>
  );
}

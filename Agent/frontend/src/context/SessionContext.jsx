import React, { createContext, useContext, useEffect, useState } from "react";
import { getJson, postJson } from "../api/client.js";

// The ACTUAL authorization boundary is the HttpOnly session cookie
// POST /api/session sets server-side (see Agent/backend/web/access.py) --
// this context is UI-convenience state only (which screen to show, whose
// name to greet), never a security control. Losing it (private-window
// storage block, a cleared tab) just means the person sees the identity
// screen again; it never grants or revokes any actual access, so a
// best-effort sessionStorage mirror (wrapped in try/catch, per the browser-
// storage caution that applies to any client code, not just Artifacts) is
// all this needs -- it only has to survive a same-tab page reload.
const STORAGE_KEY = "agent.session.v1";

const SessionContext = createContext(null);

function readStoredSession() {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && (parsed.role === "user" || parsed.role === "admin")) {
      return parsed;
    }
  } catch {
    // Private browsing / blocked storage / corrupt value -- treat exactly
    // like "never logged in", never crash the app over this.
  }
  return null;
}

function writeStoredSession(session) {
  try {
    if (session) {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Best-effort only -- see module docstring.
  }
}

export function SessionProvider({ children }) {
  const [session, setSession] = useState(() => readStoredSession());
  // Việc 2 -- project owner's explicit, temporary "bỏ bước nhập định danh"
  // decision: GET /api/config's `admin_open_access` tells this SPA whether
  // the server currently serves GET /admin (and, by the same switch, GET
  // /api/bots's normal open-to-everyone shape) with no credential at all.
  // When true, App.jsx skips IdentityPage entirely and treats every visitor
  // as already on the admin screen -- no session cookie is minted for this
  // (POST /api/session is never called), since GET /api/bots itself needs
  // none. `configLoaded` gates that redirect so a visitor is never bounced
  // to IdentityPage for one render just because this fetch has not
  // resolved yet.
  const [adminOpenAccess, setAdminOpenAccess] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { ok, data } = await getJson("/api/config");
      if (cancelled) return;
      setAdminOpenAccess(ok && data && data.admin_open_access === true);
      setConfigLoaded(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    writeStoredSession(session);
  }, [session]);

  // POST /api/session -- see Agent/backend/web/app.py's own docstring for
  // the exact contract: `identity` matching the admin key -> role "admin";
  // shaped like "0x" + 40 hex -> role "user" with a derived `user_ref`;
  // anything else -> 400 with a Vietnamese explanation of BOTH accepted
  // shapes. Returns `{ok, message}` -- never throws -- so the caller
  // (IdentityPage) can show the server's own message verbatim on failure.
  async function login(identity) {
    const { ok, data } = await postJson("/api/session", { identity });
    if (!ok || data.status !== "OK") {
      return { ok: false, message: data.message || "Login failed." };
    }
    const next = {
      role: data.role,
      userRef: data.user_ref || null,
      identity,
    };
    setSession(next);
    return { ok: true, session: next };
  }

  async function logout() {
    await postJson("/api/session/logout");
    setSession(null);
  }

  return (
    <SessionContext.Provider
      value={{ session, login, logout, adminOpenAccess, configLoaded }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession() must be called inside <SessionProvider>");
  }
  return ctx;
}

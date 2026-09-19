// Thin fetch wrapper shared by every screen. Deliberately does NOT throw on
// a non-2xx HTTP response: every route in Agent/backend/web/app.py answers
// an error case with a clean JSON body ({"status": "ERROR", "message":
// "<câu tiếng Việt>"}), and the whole point of that design (see app.py's
// own module docstring on never leaking a bare traceback) is that the exact
// server-authored Vietnamese message should reach the screen verbatim,
// never be swallowed by a generic "request failed" catch block here.
//
// Every call is same-origin (this SPA is served by the very same app.py
// process at "/", see Agent/backend/web/app.py's index route) and the
// session cookie POST /api/session sets is HttpOnly + SameSite=Lax, so it
// rides along automatically with `credentials: "same-origin"` -- no token
// handling needed on this side at all.

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    // No response at all (offline, DNS, CORS misconfiguration, ...) -- the
    // one case this module DOES synthesize its own Vietnamese message for,
    // since there is no server response to relay.
    return {
      ok: false,
      status: 0,
      data: {
        status: "ERROR",
        message:
          "Could not connect to the server -- check your network and try again.",
      },
    };
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // A non-JSON body (should not happen for this backend, see its own
    // "always clean JSON" contract, but a reverse proxy or a 502 page could
    // still hand back HTML) -- degrade to a generic message rather than
    // crash the caller.
    data = {
      status: "ERROR",
      message: `Server returned an unreadable response (HTTP ${response.status}).`,
    };
  }
  return { ok: response.ok, status: response.status, data };
}

export function postJson(path, body) {
  return request(path, { method: "POST", body: JSON.stringify(body ?? {}) });
}

export function getJson(path) {
  return request(path, { method: "GET" });
}

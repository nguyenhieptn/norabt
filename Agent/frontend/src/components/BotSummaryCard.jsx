import React from "react";

// Semantic colors for a per-asset trading state (task's "danh sách tài sản
// kèm trạng thái"). Reuses the SAME shared verdict tokens
// (Agent/frontend/tokens.css) an asset-state color would otherwise duplicate --
// there is no dedicated "--asset-state-*" token because the task's design-
// token scope is specifically the 4-tier verdict classification, and these
// three states map onto that same green/red/grey semantic directly (see
// Agent/backend/web/report_page.py's own ASSET_STATE_COLOR for the
// server's independent but semantically identical choice: this SPA does
// not import that Python dict, only the same underlying CSS variables it
// is itself now derived from).
const ASSET_STATE_VAR = {
  TRADING: "var(--verdict-positive)",
  "HOLDING ONLY": "var(--verdict-danger)",
  EXITED: "var(--verdict-unknown)",
};

function formatNumber(value, digits = 0) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatMoney(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `${formatNumber(value, 0)} USDT`;
}

function formatPercent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, 1)}%`;
}

/** Read-only summary card for one POST /api/lookup result -- the "tìm ra
 * thôi, chưa phân tích" step of the task's mandatory two-step flow. Renders
 * name/AUM/PnL/hạng/số người copy/danh sách tài sản kèm trạng thái, exactly
 * the field list the task names explicitly. Never runs the scoring engine
 * itself -- this is purely a view of whatever `lookup` already contains.
 */
export default function BotSummaryCard({ lookup }) {
  const profile = lookup.profile || {};
  const assets = Array.isArray(lookup.assets) ? lookup.assets : [];
  const isPnlPositive = typeof profile.pnl === "number" && profile.pnl >= 0;

  return (
    <div className="bot-summary-panel">
      {/* OKX AI Agent Profile Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "16px", marginBottom: "20px" }}>
        <div
          style={{
            width: "48px",
            height: "48px",
            borderRadius: "var(--radius-md, 12px)",
            background: "var(--ink, #0f172a)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--panel, #ffffff)",
            fontSize: "18px",
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {String(lookup.name || lookup.code || "?").trim().charAt(0).toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginBottom: "4px" }}>
            <h3 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "var(--ink)" }}>
              {lookup.name || lookup.code}
            </h3>
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: "10.5px",
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: "var(--radius-xs, 4px)",
                background: "rgba(59, 130, 246, 0.12)",
                color: "var(--s1, #3b82f6)",
                border: "1px solid rgba(59, 130, 246, 0.25)",
                textTransform: "uppercase",
              }}
            >
              OKX CEX · Copy Trading
            </span>
          </div>
          <p className="muted" style={{ margin: 0, fontSize: "12.5px" }}>
            Bot code: <span className="num" style={{ color: "var(--ink)", fontWeight: 600 }}>{lookup.code}</span>
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="label">Total assets (AUM)</div>
          <div className="value num">{formatMoney(profile.aum)}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Closed PnL</div>
          <div className={`value num ${isPnlPositive ? "up" : "down"}`}>
            {formatMoney(profile.pnl)}
            {typeof profile.pnl_ratio === "number" ? (
              <span style={{ fontSize: "12.5px", fontWeight: 500, marginLeft: "4px" }}>
                ({formatPercent(profile.pnl_ratio)})
              </span>
            ) : null}
          </div>
        </div>
        <div className="stat-tile">
          <div className="label">Exchange rank</div>
          <div className="value num" style={{ color: "var(--amber)" }}>
            {profile.rank != null ? `#${formatNumber(profile.rank)}` : "—"}
          </div>
        </div>
        <div className="stat-tile">
          <div className="label">Copy traders</div>
          <div className="value num">{formatNumber(profile.copy_traders)}</div>
        </div>
      </div>

      <div className="field" style={{ marginTop: "20px" }}>
        <label>Traded assets ({assets.length} pairs)</label>
        {assets.length === 0 ? (
          <p className="empty-note">No asset data available for this bot yet.</p>
        ) : (
          <ul className="asset-list">
            {assets.map((asset) => (
              <li className="asset-row" key={asset.asset}>
                <span className="num" style={{ fontWeight: 600 }}>{asset.asset}</span>
                <span
                  className="badge"
                  style={{ "--badge-color": ASSET_STATE_VAR[asset.state] }}
                >
                  {asset.state}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {lookup.note ? <p className="empty-note">{lookup.note}</p> : null}
    </div>
  );
}

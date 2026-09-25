import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getJson, postJson } from "../api/client.js";
import AnalyzeFlow from "../components/AnalyzeFlow.jsx";
import AdminOverview from "../components/AdminOverview.jsx";
import BotDetailView from "../components/BotDetailView.jsx";
import PortfolioDetailView from "../components/PortfolioDetailView.jsx";
import { Block, Loading, ErrorBox } from "../components/common.jsx";
import { Pager, usePaged } from "../components/Pager.jsx";
import { VerdictDot, verdictColor } from "../components/verdictUi.jsx";

const VN_OFFSET_MS = 7 * 3_600_000;
const STALE_AFTER_MS = 24 * 3_600_000;

function formatTimestampMs(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return "—";
  const date = new Date(ms + VN_OFFSET_MS);
  if (Number.isNaN(date.getTime())) return "—";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` +
    `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`
  );
}

function isStale(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return false;
  return Date.now() - ms > STALE_AFTER_MS;
}

const SORTABLE_COLUMNS = {
  name: (row) => row.name || row.code || "",
  code: (row) => row.code,
  venue_asset: (row) => row.venue_asset || "",
  verdict: (row) => row.verdict || "",
  risk: (row) => (typeof row.risk === "number" ? row.risk : -Infinity),
  quality: (row) => (typeof row.quality === "number" ? row.quality : -Infinity),
  confidence: (row) =>
    typeof row.confidence === "number" ? row.confidence : -Infinity,
  trade_count: (row) =>
    typeof row.trade_count === "number" ? row.trade_count : -Infinity,
  generated_at_ms: (row) =>
    typeof row.generated_at_ms === "number" ? row.generated_at_ms : -Infinity,
};

// Portfolio verdict as a dot + short label. The raw enum stays in `title`, so
// nothing the backend said is lost -- it is just not shouted in capitals on
// every row. Thresholds live in report/qc/portfolio/service.py.
function renderPortfolioVerdictTag(verdict) {
  const v = (verdict || "").toUpperCase();
  let tone = "mute";
  let label = verdict || "Undetermined";
  if (v.includes("DIVERSIFIED")) {
    tone = "ok";
    label = "Diversified";
  } else if (v.includes("MODERATE")) {
    tone = "warn";
    label = "Moderate co-movement";
  } else if (v.includes("CLUSTER") || v.includes("HIGH")) {
    tone = "bad";
    label = "High correlation";
  } else if (v.includes("INSUFFICIENT")) {
    label = "Insufficient evidence";
  }
  return (
    <span className={`prun-verdict prun-${tone}`} title={verdict || ""}>
      <i />
      {label}
    </span>
  );
}

// Member avatars: one colour per position in the run, first letter of the name.
const PRUN_MEMBER_COLORS = ["#f7931a", "#627eea", "#9945ff", "#3a3f47", "#ba9f33", "#0d9488"];

// Same cut-offs as the verdict (MODERATE_AVG_PEARSON / HIGH_AVG_PEARSON).
function pearsonColor(value) {
  if (typeof value !== "number") return "var(--ink-3)";
  if (value >= 0.6) return "var(--down)";
  if (value >= 0.3) return "var(--amber)";
  return "var(--up)";
}

function riskColor(risk) {
  if (typeof risk !== "number") return "var(--ink-3)";
  if (risk < 30) return "var(--up)";
  if (risk < 70) return "var(--amber)";
  return "var(--down)";
}

export default function AdminHome() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get("tab") || "overview";

  const [rows, setRows] = useState([]);
  const [portfolioRuns, setPortfolioRuns] = useState([]);
  const [loadState, setLoadState] = useState("loading");
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [portfolioQuery, setPortfolioQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [sortKey, setSortKey] = useState("risk");
  const [sortDir, setSortDir] = useState("desc");

  // 2 sub-tabs in the bot list: "individual" (single bots) vs "portfolio" (portfolio run history)
  // Kept in the URL (`list=portfolio`) so "Back to portfolio runs" from a
  // portfolio report lands on the list it came from.
  const botListTab = searchParams.get("list") === "portfolio" ? "portfolio" : "individual";
  const setBotListTab = (value) =>
    setSearchParams(value === "portfolio" ? { tab: "bots", list: "portfolio" } : { tab: "bots" });
  const [selectedPortfolioData, setSelectedPortfolioData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 1. Load the single-bot list
      const { ok, data } = await getJson("/api/bots");
      if (cancelled) return;
      if (!ok) {
        setError(data.message || "Could not load the bot list.");
        setLoadState("error");
        return;
      }
      const rawRows = Array.isArray(data.bots) ? data.bots : [];
      setRows(rawRows.filter((row) => row && typeof row.code === "string"));

      // 2. Load the portfolio run history.
      //
      // An empty list is an empty list. Illustrative sample rows used to be
      // shown here when the endpoint returned nothing -- invented portfolios
      // with invented correlations, rendered exactly like measured ones in an
      // operator's risk console. Nothing about the row said it was a sample.
      try {
        const { ok: pOk, data: pData } = await getJson("/api/portfolios");
        setPortfolioRuns(pOk && Array.isArray(pData?.portfolios) ? pData.portfolios : []);
      } catch (_) {
        setPortfolioRuns([]);
      }

      setLoadState("ready");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const categoryCounts = useMemo(() => {
    return {
      all: rows.length,
      low_good: rows.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: LOW · QUALITY: GOOD"),
      ).length,
      high_good: rows.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: HIGH · QUALITY: GOOD"),
      ).length,
      low_weak: rows.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: LOW · QUALITY: WEAK"),
      ).length,
      high_weak: rows.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: HIGH · QUALITY: WEAK"),
      ).length,
      hidden: rows.filter((r) =>
        (r.verdict || "").includes("HIDDEN RISK"),
      ).length,
      losing: rows.filter(
        (r) => typeof r.total_pnl === "number" && r.total_pnl < 0,
      ).length,
    };
  }, [rows]);

  const visibleRows = useMemo(() => {
    let list = rows;
    if (activeCategory === "low_good") {
      list = list.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: LOW · QUALITY: GOOD"),
      );
    } else if (activeCategory === "high_good") {
      list = list.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: HIGH · QUALITY: GOOD"),
      );
    } else if (activeCategory === "low_weak") {
      list = list.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: LOW · QUALITY: WEAK"),
      );
    } else if (activeCategory === "high_weak") {
      list = list.filter((r) =>
        (r.verdict || "").includes("DRAWDOWN: HIGH · QUALITY: WEAK"),
      );
    } else if (activeCategory === "hidden") {
      list = list.filter((r) =>
        (r.verdict || "").includes("HIDDEN RISK"),
      );
    } else if (activeCategory === "losing") {
      list = list.filter(
        (r) => typeof r.total_pnl === "number" && r.total_pnl < 0,
      );
    }

    const needle = query.trim().toLowerCase();
    const filtered = needle
      ? list.filter(
          (row) =>
            row.code.toLowerCase().includes(needle) ||
            (row.name || "").toLowerCase().includes(needle) ||
            (row.venue_asset || "").toLowerCase().includes(needle) ||
            (row.verdict || "").toLowerCase().includes(needle),
        )
      : list;
    const keyFn = SORTABLE_COLUMNS[sortKey] || SORTABLE_COLUMNS.risk;
    const sorted = [...filtered].sort((a, b) => {
      const av = keyFn(a);
      const bv = keyFn(b);
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [rows, activeCategory, query, sortKey, sortDir]);

  const visiblePortfolioRuns = useMemo(() => {
    const q = portfolioQuery.trim().toLowerCase();
    if (!q) return portfolioRuns;
    return portfolioRuns.filter((run) => {
      if ((run.portfolio_id || "").toLowerCase().includes(q)) return true;
      if ((run.verdict || "").toLowerCase().includes(q)) return true;
      if (run.member_codes?.some((c) => c.toLowerCase().includes(q))) return true;
      if (run.members?.some((m) => (m.name || m.code || "").toLowerCase().includes(q))) return true;
      return false;
    });
  }, [portfolioRuns, portfolioQuery]);

  const { page, pages, slice, setPage, size, setSize } = usePaged(
    visibleRows,
    10,
  );

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function sortIndicator(key) {
    if (sortKey !== key) return null;
    return (
      <span className="sort-arrow">{sortDir === "asc" ? " ▲" : " ▼"}</span>
    );
  }

  function openBot(code) {
    setSearchParams({ tab: "bot", code });
  }

  function openPortfolio(id, pData = null) {
    setSelectedPortfolioData(pData);
    setSearchParams({ tab: "portfolio", id });
  }

  // Một lượt chạy có thể còn số đo trong lịch sử mà không còn trang để mở
  // (tài liệu bị xoá, thư mục dữ liệu bị dọn). Hàng đó vẫn đáng liệt kê,
  // nhưng đưa nó thành link là đưa người đọc tới 404. Vì mỗi hàng mang theo
  // đúng danh sách mã thành viên, dựng lại được bằng chính chúng — và
  // `portfolio_id` suy ra từ TẬP thành viên nên id quay lại y nguyên.
  const [rebuilding, setRebuilding] = useState(null);

  async function rebuildPortfolio(run) {
    const codes = Array.isArray(run.member_codes) ? run.member_codes : [];
    if (codes.length < 2) return;
    setRebuilding(run.portfolio_id);
    try {
      const resp = await postJson("/api/portfolio/analyze", { codes });
      if (resp.ok && resp.data && resp.data.portfolio_id) {
        const { ok, data } = await getJson("/api/portfolios");
        if (ok && Array.isArray(data?.portfolios)) setPortfolioRuns(data.portfolios);
        openPortfolio(resp.data.portfolio_id, resp.data);
        return;
      }
      window.alert(
        (resp.data && (resp.data.limited_reason || resp.data.error)) ||
          "Could not rebuild this portfolio run."
      );
    } catch (err) {
      window.alert(`Could not rebuild this portfolio run: ${err?.message || err}`);
    } finally {
      setRebuilding(null);
    }
  }

  // Re-analyze from a portfolio report: re-run the same booked set (measured
  // members plus any that hid their order book) and refresh the runs list.
  // The report reloads itself once this resolves.
  async function reanalyzePortfolio(id) {
    const run = portfolioRuns.find((r) => r.portfolio_id === id);
    const fromPayload = selectedPortfolioData && selectedPortfolioData.portfolio_id === id ? selectedPortfolioData : null;
    const codes = [
      ...new Set(
        [
          ...(run?.member_codes || fromPayload?.member_codes || []),
          ...(run?.concealed_member_codes || fromPayload?.portfolio?.concealed_member_codes || []),
        ].map(String)
      ),
    ];
    if (codes.length < 2) {
      window.alert("This run does not carry its member codes; run it again from Analyze Bot.");
      return;
    }
    try {
      const resp = await postJson("/api/portfolio/analyze", { codes });
      if (resp.ok && resp.data && resp.data.portfolio_id) {
        const { ok, data } = await getJson("/api/portfolios");
        if (ok && Array.isArray(data?.portfolios)) setPortfolioRuns(data.portfolios);
        if (resp.data.portfolio_id !== id) openPortfolio(resp.data.portfolio_id, resp.data);
        return;
      }
      window.alert(
        (resp.data && (resp.data.limited_reason || resp.data.error)) || "Could not re-analyze this portfolio."
      );
    } catch (err) {
      window.alert(`Could not re-analyze this portfolio: ${err?.message || err}`);
    }
  }

  if (loadState === "loading") {
    return <Loading text="Syncing bot data..." />;
  }

  if (loadState === "error") {
    return <ErrorBox error={error} />;
  }

  return (
    <div className="admin-page">
      {/* ========================================================================= */}
      {/* TAB 1: TỔNG QUAN (OVERVIEW) */}
      {/* ========================================================================= */}
      {currentTab === "overview" && (
        <section className="tab-section tab-overview">
          <AdminOverview
            rows={rows}
            onOpenBot={openBot}
            onFilterVerdict={(verdict) => {
              setQuery(verdict);
              setSearchParams({ tab: "bots" });
            }}
          />
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: BOT LIST (2 SUB-TABS: SINGLE BOTS & PORTFOLIO HISTORY) */}
      {/* ========================================================================= */}
      {currentTab === "bots" && (
        <section className="tab-section tab-bots">
          <div className="catalog-head">
            <h1>Analysis catalog</h1>
            <div className="seg-tabs" role="tablist" aria-label="Catalog">
              <button
                type="button"
                role="tab"
                aria-selected={botListTab === "individual"}
                className={botListTab === "individual" ? "on" : ""}
                onClick={() => setBotListTab("individual")}
              >
                Single Bots <span className="seg-count">{rows.length}</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={botListTab === "portfolio"}
                className={botListTab === "portfolio" ? "on" : ""}
                onClick={() => setBotListTab("portfolio")}
              >
                Portfolio Runs <span className="seg-count">{portfolioRuns.length}</span>
              </button>
            </div>
          </div>

          {/* SUB-TAB 1: SINGLE-BOT LISTING TABLE */}
          {botListTab === "individual" && (
            <Block
              title="Single-Bot Assessment Table"
              note={`${visibleRows.length} / ${rows.length} bot`}
              flush
            >
              {/* OKX AI Category Filter Chips */}
              <div className="filter-chips-row">
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "all" ? "active" : ""}`}
                  onClick={() => setActiveCategory("all")}
                >
                  <span>All</span>
                  <span className="chip-count">{categoryCounts.all}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "low_good" ? "active" : ""}`}
                  onClick={() => setActiveCategory("low_good")}
                >
                  <span style={{ color: verdictColor("DRAWDOWN: LOW · QUALITY: GOOD") }}>●</span>
                  <span>Low Drawdown · Good</span>
                  <span className="chip-count">{categoryCounts.low_good}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "high_good" ? "active" : ""}`}
                  onClick={() => setActiveCategory("high_good")}
                >
                  <span style={{ color: verdictColor("DRAWDOWN: HIGH · QUALITY: GOOD") }}>●</span>
                  <span>High Drawdown · Good</span>
                  <span className="chip-count">{categoryCounts.high_good}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "high_weak" ? "active" : ""}`}
                  onClick={() => setActiveCategory("high_weak")}
                >
                  <span style={{ color: verdictColor("DRAWDOWN: HIGH · QUALITY: WEAK") }}>●</span>
                  <span>High Drawdown · Weak</span>
                  <span className="chip-count">{categoryCounts.high_weak}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "hidden" ? "active" : ""}`}
                  onClick={() => setActiveCategory("hidden")}
                >
                  <span style={{ color: verdictColor("HIDDEN RISK") }}>●</span>
                  <span>Hidden Risk</span>
                  <span className="chip-count">{categoryCounts.hidden}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "losing" ? "active" : ""}`}
                  onClick={() => setActiveCategory("losing")}
                >
                  <span style={{ color: "var(--down)" }}>●</span>
                  <span>Net Losing</span>
                  <span className="chip-count">{categoryCounts.losing}</span>
                </button>
              </div>

              {/* Search & Filter Bar */}
              <div className="tbl-toolbar">
                <div className="tbl-search-box">
                  <svg className="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><line x1="20" y1="20" x2="16.2" y2="16.2" /></svg>
                  <input
                    type="text"
                    placeholder="Search by name, bot code, venue/pair, or verdict..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  {query && (
                    <button
                      type="button"
                      className="btn-clear"
                      onClick={() => setQuery("")}
                      title="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="tbl-note-action">
                  Click any row to view the single bot report
                </div>
              </div>

              {visibleRows.length === 0 ? (
                <div className="msg">
                  No bots found matching the keyword &quot;{query}&quot;.
                </div>
              ) : (
                <div className="tblwrap">
                  <table>
                    <thead>
                      <tr>
                        <th onClick={() => toggleSort("name")} className="sortable">
                          Bot {sortIndicator("name")}
                        </th>
                        <th onClick={() => toggleSort("code")} className="sortable">
                          Code {sortIndicator("code")}
                        </th>
                        <th onClick={() => toggleSort("venue_asset")} className="sortable">
                          Pair {sortIndicator("venue_asset")}
                        </th>
                        <th onClick={() => toggleSort("verdict")} className="sortable">
                          Verdict {sortIndicator("verdict")}
                        </th>
                        <th onClick={() => toggleSort("risk")} className="n sortable">
                          Risk {sortIndicator("risk")}
                        </th>
                        <th onClick={() => toggleSort("quality")} className="n sortable">
                          Quality {sortIndicator("quality")}
                        </th>
                        <th onClick={() => toggleSort("confidence")} className="n sortable">
                          Confidence {sortIndicator("confidence")}
                        </th>
                        <th onClick={() => toggleSort("trade_count")} className="n sortable">
                          Trades {sortIndicator("trade_count")}
                        </th>
                        <th onClick={() => toggleSort("generated_at_ms")} className="n sortable">
                          Scored {sortIndicator("generated_at_ms")}
                        </th>
                        <th style={{ textAlign: "center" }} aria-label="Report" />
                      </tr>
                    </thead>
                    <tbody>
                      {slice.map((row) => {
                        const stale = isStale(row.generated_at_ms);
                        return (
                          <tr
                            key={row.code}
                            className={`rowlink ${stale ? "row-stale" : ""}`}
                            onClick={() => openBot(row.code)}
                            title={`View bot ${row.code} details`}
                          >
                            <td
                              data-c="name"
                              style={{
                                fontWeight: 600,
                                maxWidth: 220,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}
                            >
                              {row.name || row.code}
                            </td>
                            <td
                              data-c="code"
                              data-label="Code"
                              className="mono"
                              style={{ color: "var(--amber)", fontWeight: 500 }}
                            >
                              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }} title={row.code}>
                                <span>{row.code && row.code.length > 10 ? `${row.code.slice(0, 8)}…` : row.code}</span>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigator.clipboard?.writeText(row.code);
                                  }}
                                  style={{
                                    background: "transparent",
                                    border: "none",
                                    color: "var(--ink-3)",
                                    cursor: "pointer",
                                    padding: 0,
                                    fontSize: 12,
                                  }}
                                  title="Copy bot code"
                                >
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
                                </button>
                              </span>
                            </td>
                            <td data-c="pair" data-label="Pair" className="mono" title={row.venue_asset || ""}>
                              {row.venue_asset ? row.venue_asset.split("·").pop().trim() : "—"}
                            </td>
                            <td data-c="verdict"><VerdictDot verdict={row.verdict} /></td>
                            <td data-c="risk" className="n mono" style={{ fontWeight: 600 }}>
                              {typeof row.risk === "number" ? (
                                <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "flex-end", gap: 8, width: "100%" }}>
                                  <div style={{ width: 32, height: 4, background: "var(--line, rgba(255,255,255,0.08))", borderRadius: 2, overflow: "hidden", display: "inline-flex" }}>
                                    <div style={{ width: `${Math.min(Math.max(row.risk, 0), 100)}%`, background: riskColor(row.risk) }} />
                                  </div>
                                  <span style={{ color: riskColor(row.risk), minWidth: 24, textAlign: "right" }}>
                                    {row.risk.toFixed(0)}
                                  </span>
                                </div>
                              ) : "—"}
                            </td>
                            <td data-c="meta" data-label="Quality" className="n mono">
                              {typeof row.quality === "number" ? row.quality.toFixed(0) : "—"}
                            </td>
                            <td data-c="meta" data-label="Conf." className="n mono">
                              {typeof row.confidence === "number" ? `${row.confidence.toFixed(0)}%` : "—"}
                            </td>
                            <td data-c="meta" data-label="Trades" className="n mono">
                              {typeof row.trade_count === "number" ? row.trade_count.toLocaleString("en-US") : "—"}
                            </td>
                            <td
                              data-c="meta"
                              data-label="Scored"
                              className="n mono"
                              style={{ color: "var(--ink-2)", fontSize: "12px" }}
                            >
                              <span>{formatTimestampMs(row.generated_at_ms)}</span>
                              {stale && (
                                <span className="stale-tag" title="Scored more than 24 hours ago">
                                  &gt;24h
                                </span>
                              )}
                            </td>
                            <td data-c="go" style={{ textAlign: "center" }}>
                              <button
                                type="button"
                                className="prun-go"
                                aria-label={`View report for bot ${row.code}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openBot(row.code);
                                }}
                              >
                                →
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination Controls */}
              <Pager
                page={page}
                pages={pages}
                total={visibleRows.length}
                setPage={setPage}
                size={size}
                setSize={setSize}
                unit="bot"
              />
            </Block>
          )}

          {/* SUB-TAB 2: PORTFOLIO RUN HISTORY TABLE */}
          {botListTab === "portfolio" && (
            <Block
              title="Multi-Bot Portfolio Run History"
              note={`${visiblePortfolioRuns.length} / ${portfolioRuns.length} portfolios`}
              flush
            >
              {/* Toolbar */}
              <div className="tbl-toolbar">
                <div className="tbl-search-box">
                  <svg className="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><line x1="20" y1="20" x2="16.2" y2="16.2" /></svg>
                  <input
                    type="text"
                    placeholder="Search by portfolio id, bot code, or verdict..."
                    value={portfolioQuery}
                    onChange={(e) => setPortfolioQuery(e.target.value)}
                  />
                  {portfolioQuery && (
                    <button
                      type="button"
                      className="btn-clear"
                      onClick={() => setPortfolioQuery("")}
                      title="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="tbl-note-action">
                  Click a row to see the correlation matrix &amp; joint Monte Carlo simulation
                </div>
              </div>

              {visiblePortfolioRuns.length === 0 ? (
                <div className="msg">
                  No portfolio run matches &quot;{portfolioQuery}&quot;.
                </div>
              ) : (
                <div className="tblwrap">
                  <table>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left" }}>Portfolio</th>
                        <th>Members</th>
                        <th className="n">Bots</th>
                        <th>Verdict</th>
                        <th className="n" title="Average pairwise Pearson correlation of realised PnL">Avg r</th>
                        <th className="n" title="Risk score of the merged book, 0 – 100">Risk</th>
                        <th className="n" title="95th percentile of the simulated joint drawdown">Joint DD (p95)</th>
                        <th className="n">Analyzed</th>
                        <th style={{ textAlign: "center" }} aria-label="Report" />
                      </tr>
                    </thead>
                    <tbody>
                      {visiblePortfolioRuns.map((run) => (
                        <tr
                          key={run.portfolio_id}
                          className="rowlink"
                          onClick={
                            run.report_available === false
                              ? undefined
                              : () => openPortfolio(run.portfolio_id, run)
                          }
                          style={
                            run.report_available === false
                              ? { cursor: "default", opacity: 0.62 }
                              : undefined
                          }
                          title={
                            run.report_available === false
                              ? "The rendered report for this run is no longer on disk. "
                                + "The measurements below are still the ones that were "
                                + "taken; re-run the same bot codes to rebuild the page."
                              : `View portfolio report ${run.portfolio_id}`
                          }
                        >
                          <td data-c="name" style={{ textAlign: "left" }}>
                            <span className="mono prun-id">{run.portfolio_id}</span>
                          </td>
                          <td
                            data-c="members"
                            // Every member stays one hover away: a 6-bot run
                            // used to wrap into a column of six chips per row.
                            title={[
                              ...(run.members || []).map((m) => `${m.name || m.code} (${m.symbol || "—"})`),
                              ...(run.concealed_member_codes || [])
                                .filter((c) => !(run.members || []).some((m) => m.code === c))
                                .map((c) => `${c} (order book hidden, not measured)`),
                            ].join("\n")}
                          >
                            <span className="prun-members">
                              <span className="prun-stack" aria-hidden="true">
                                {(run.members || []).map((m, i) => (
                                  <i
                                    key={m.code || i}
                                    style={{
                                      background: PRUN_MEMBER_COLORS[i % PRUN_MEMBER_COLORS.length],
                                      // Order book hidden on OKX, measured from public
                                      // daily PnL: still a member, ringed so it reads as one.
                                      ...(m.ledger_hidden ? { boxShadow: "0 0 0 1.5px var(--down)" } : {}),
                                    }}
                                  >
                                    {(m.name || m.code || "?").trim().charAt(0).toUpperCase()}
                                  </i>
                                ))}
                                {/* Bot giấu sổ lệnh vẫn là bot bạn đã book: hiện nó trong
                                    chồng chip, đánh dấu viền đỏ, thay vì để nó biến mất khỏi
                                    hàng (phát hiện thật, 2026-09-24). */}
                                {(run.concealed_member_codes || [])
                                  .filter((c) => !(run.members || []).some((m) => m.code === c))
                                  .map((c) => (
                                  <i
                                    key={`concealed-${c}`}
                                    style={{
                                      background: "var(--panel-2)",
                                      color: "var(--down)",
                                      boxShadow: "inset 0 0 0 1.5px var(--down)",
                                    }}
                                  >
                                    {String(c).charAt(0).toUpperCase()}
                                  </i>
                                ))}
                              </span>
                              <span className="prun-first">
                                {run.members?.[0]?.name || run.members?.[0]?.code || "—"}
                              </span>
                              {(() => {
                                const absent = (run.concealed_member_codes || []).filter(
                                  (c) => !(run.members || []).some((m) => m.code === c)
                                ).length;
                                const total = (run.members?.length || 0) + absent;
                                return total > 1 ? <span className="prun-more">+{total - 1}</span> : null;
                              })()}
                            </span>
                          </td>
                          <td data-c="meta" data-label="Bots" className="n mono" style={{ fontWeight: 600 }}>
                            {(() => {
                              /* Một số nguyên, đúng thiết kế (mockup admin: `p.members.length`)
                                 và đúng con số người dùng đã book -- không phải phân số
                                 "đo được/đã gửi". Chi tiết đo được bao nhiêu nằm trong tooltip
                                 và trong tab Members của report ("3 measured · 1 concealed"). */
                              const measured = run.member_count || run.members?.length || 0;
                              const submitted = run.submitted_member_count || measured;
                              if (submitted <= measured && !(run.members || []).some((m) => m.ledger_hidden)) return submitted;
                              const memberCodes = new Set((run.members || []).map((m) => m.code));
                              const concealed = (run.concealed_member_codes || []).filter((c) => !memberCodes.has(c));
                              const publicOnly = (run.members || []).filter((m) => m.ledger_hidden).length;
                              const unreadable = submitted - measured - concealed.length;
                              const parts = [`${measured} measured`];
                              if (publicOnly) parts.push(`${publicOnly} via public daily PnL (order book hidden)`);
                              if (concealed.length) parts.push(`${concealed.length} concealed (${concealed.join(", ")})`);
                              if (unreadable > 0) parts.push(`${unreadable} not readable`);
                              if (typeof run.measurement_coverage_pct === "number") {
                                parts.push(`${run.measurement_coverage_pct.toFixed(0)}% of capital measured`);
                              }
                              return <span title={parts.join(" · ")}>{submitted}</span>;
                            })()}
                          </td>
                          <td data-c="verdict">{renderPortfolioVerdictTag(run.verdict)}</td>
                          <td
                            data-c="meta"
                            data-label="Avg r"
                            className="n mono"
                            style={{
                              fontWeight: 700,
                              color: pearsonColor(run.average_pearson),
                            }}
                          >
                            {typeof run.average_pearson === "number" ? run.average_pearson.toFixed(2) : "—"}
                          </td>
                          <td
                            data-c="meta"
                            data-label="Risk"
                            className="n mono"
                            style={{
                              fontWeight: 700,
                              color: riskColor(run.risk),
                            }}
                          >
                            {/* Một danh mục có đúng MỘT điểm rủi ro: điểm của
                                bản đánh giá gộp, do chính mười lens sinh ra
                                trên sổ lệnh đã trộn. Trường `portfolio_risk_score`
                                cũ là một điểm thứ hai tính song song, đã bỏ. */}
                            {typeof run.risk === "number"
                              ? run.risk.toFixed(0)
                              : "—"}
                          </td>
                          <td data-c="meta" data-label="Joint DD" className="n mono">
                            {typeof run.joint_p95_max_drawdown === "number"
                              ? `${run.joint_p95_max_drawdown.toFixed(1)}%`
                              : "—"}
                          </td>
                          <td data-c="meta" data-label="Analyzed" className="n mono" style={{ color: "var(--ink-2)", fontSize: "12px" }}>
                            {formatTimestampMs(run.timestamp || run.as_of_ms)}
                          </td>
                          <td data-c="go" style={{ textAlign: "center" }}>
                            {run.report_available === false ? (
                              <button
                                type="button"
                                className="prun-rebuild"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  rebuildPortfolio(run);
                                }}
                                disabled={rebuilding === run.portfolio_id}
                                title={
                                  "The rendered page is gone; this re-runs the same "
                                  + "member codes and rebuilds it under the same id"
                                }
                              >
                                {rebuilding === run.portfolio_id ? "Rebuilding…" : "↻ Rebuild"}
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="prun-go"
                                aria-label={`View portfolio report ${run.portfolio_id}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openPortfolio(run.portfolio_id, run);
                                }}
                              >
                                →
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Block>
          )}
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: BOT LOOKUP & ANALYSIS (SINGLE & PORTFOLIO) */}
      {/* ========================================================================= */}
      {currentTab === "analyze" && (
        <section className="tab-section tab-analyze">
          <div className="catalog-head catalog-head-stack">
            <h1>Look up &amp; analyze bot</h1>
            <p>One bot code for a single report · several codes for a portfolio.</p>
          </div>

          <Block
            title="Direct Quantitative Assessment from OKX"
            note="Monte Carlo engine & portfolio risk assessment"
          >
            <AnalyzeFlow
              onOpenBot={openBot}
              onOpenPortfolio={(pId, pData) => {
                setSelectedPortfolioData(pData);
                setSearchParams({ tab: "portfolio", id: pId });
              }}
            />
          </Block>
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: SINGLE BOT DETAIL REPORT (BOT DETAIL VIEW) */}
      {/* ========================================================================= */}
      {currentTab === "bot" && (
        <section className="tab-section tab-bot-detail">
          <BotDetailView
            code={searchParams.get("code")}
            onBack={() => setSearchParams({ tab: "bots" })}
          />
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: MULTI-BOT PORTFOLIO DETAIL REPORT (PORTFOLIO DETAIL VIEW) */}
      {/* ========================================================================= */}
      {currentTab === "portfolio" && (
        <section className="tab-section tab-portfolio-detail">
          <PortfolioDetailView
            portfolioId={searchParams.get("id")}
            initialData={selectedPortfolioData}
            onBack={() => setSearchParams({ tab: "bots", list: "portfolio" })}
            onReanalyze={reanalyzePortfolio}
            onOpenBot={openBot}
          />
        </section>
      )}
    </div>
  );
}

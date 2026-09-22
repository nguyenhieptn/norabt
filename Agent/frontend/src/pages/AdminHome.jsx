import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getJson } from "../api/client.js";
import AnalyzeFlow from "../components/AnalyzeFlow.jsx";
import AdminOverview from "../components/AdminOverview.jsx";
import BotDetailView from "../components/BotDetailView.jsx";
import PortfolioDetailView from "../components/PortfolioDetailView.jsx";
import { Block, Loading, ErrorBox } from "../components/common.jsx";
import { Pager, usePaged } from "../components/Pager.jsx";

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

function renderVerdictTag(verdict) {
  if (!verdict) return <span className="tag stop">INSUFFICIENT EVIDENCE</span>;
  if (verdict.includes("DRAWDOWN: LOW · QUALITY: GOOD")) {
    return <span className="tag trend">{verdict}</span>;
  }
  if (verdict.includes("DRAWDOWN: LOW · QUALITY: WEAK")) {
    return <span className="tag band">{verdict}</span>;
  }
  if (verdict.includes("DRAWDOWN: HIGH · QUALITY: GOOD")) {
    return <span className="tag dca">{verdict}</span>;
  }
  if (verdict.includes("DRAWDOWN: HIGH · QUALITY: WEAK")) {
    return <span className="tag busd">{verdict}</span>;
  }
  if (verdict.includes("HIDDEN RISK")) {
    return <span className="tag purple">{verdict}</span>;
  }
  return <span className="tag stop">{verdict}</span>;
}

function renderPortfolioVerdictTag(verdict) {
  const v = (verdict || "").toUpperCase();
  if (v.includes("DIVERSIFIED")) {
    return <span className="tag trend">✓ DIVERSIFIED (GOOD)</span>;
  }
  if (v.includes("MODERATE")) {
    return <span className="tag band">▲ MODERATE</span>;
  }
  if (v.includes("CLUSTER") || v.includes("HIGH")) {
    return <span className="tag stop">⚠ HIGH CORRELATION (WARNING)</span>;
  }
  return <span className="tag">{verdict || "UNDETERMINED"}</span>;
}

function riskColor(risk) {
  if (typeof risk !== "number") return "var(--ink-3)";
  if (risk < 30) return "var(--up)";
  if (risk < 50) return "var(--amber)";
  if (risk < 70) return "#ea580c";
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
  const [botListTab, setBotListTab] = useState("individual");
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
    15,
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
          <div className="head">
            <div className="crumb">MONITORING SYSTEM · BOT &amp; PORTFOLIO CATALOG</div>
            <div className="head-row">
              <h1>Analysis Catalog</h1>
            </div>
            <p>
              Quantitative monitoring system: see each single bot's analysis, or track portfolio correlation runs.
            </p>
          </div>

          {/* 2 visual SUB-TABS */}
          <div
            style={{
              display: "flex",
              gap: 12,
              marginBottom: 20,
              paddingBottom: 12,
              borderBottom: "1px solid var(--border, rgba(255, 255, 255, 0.08))",
            }}
          >
            <button
              type="button"
              className={`btn ${botListTab === "individual" ? "pri" : ""}`}
              onClick={() => setBotListTab("individual")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 18px",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              <span>🤖</span>
              <span>Single Bots</span>
              <span
                style={{
                  background: botListTab === "individual" ? "rgba(0,0,0,0.25)" : "rgba(255,255,255,0.12)",
                  borderRadius: 10,
                  padding: "2px 8px",
                  fontSize: 12,
                }}
              >
                {rows.length}
              </span>
            </button>

            <button
              type="button"
              className={`btn ${botListTab === "portfolio" ? "pri" : ""}`}
              onClick={() => setBotListTab("portfolio")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 18px",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              <span>🔮</span>
              <span>Portfolio Runs</span>
              <span
                style={{
                  background: botListTab === "portfolio" ? "rgba(0,0,0,0.25)" : "rgba(255,255,255,0.12)",
                  borderRadius: 10,
                  padding: "2px 8px",
                  fontSize: 12,
                }}
              >
                {portfolioRuns.length}
              </span>
            </button>
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
                  <span style={{ color: "#10b981" }}>●</span>
                  <span>Low Drawdown · Good</span>
                  <span className="chip-count">{categoryCounts.low_good}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "high_good" ? "active" : ""}`}
                  onClick={() => setActiveCategory("high_good")}
                >
                  <span style={{ color: "#f59e0b" }}>●</span>
                  <span>High Drawdown · Good</span>
                  <span className="chip-count">{categoryCounts.high_good}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "high_weak" ? "active" : ""}`}
                  onClick={() => setActiveCategory("high_weak")}
                >
                  <span style={{ color: "#f43f5e" }}>●</span>
                  <span>High Drawdown · Weak</span>
                  <span className="chip-count">{categoryCounts.high_weak}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "hidden" ? "active" : ""}`}
                  onClick={() => setActiveCategory("hidden")}
                >
                  <span style={{ color: "#a855f7" }}>●</span>
                  <span>Hidden Risk</span>
                  <span className="chip-count">{categoryCounts.hidden}</span>
                </button>
                <button
                  type="button"
                  className={`filter-chip ${activeCategory === "losing" ? "active" : ""}`}
                  onClick={() => setActiveCategory("losing")}
                >
                  <span style={{ color: "#f43f5e" }}>📉</span>
                  <span>Net Losing</span>
                  <span className="chip-count">{categoryCounts.losing}</span>
                </button>
              </div>

              {/* Search & Filter Bar */}
              <div className="tbl-toolbar">
                <div className="tbl-search-box">
                  <span className="search-icon">🔍</span>
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
                          Bot Name {sortIndicator("name")}
                        </th>
                        <th onClick={() => toggleSort("code")} className="sortable">
                          Bot Code {sortIndicator("code")}
                        </th>
                        <th onClick={() => toggleSort("venue_asset")} className="sortable">
                          Venue / Asset {sortIndicator("venue_asset")}
                        </th>
                        <th onClick={() => toggleSort("verdict")} className="sortable">
                          Verdict {sortIndicator("verdict")}
                        </th>
                        <th onClick={() => toggleSort("risk")} className="n sortable">
                          Risk Score {sortIndicator("risk")}
                        </th>
                        <th onClick={() => toggleSort("quality")} className="n sortable">
                          Quality {sortIndicator("quality")}
                        </th>
                        <th onClick={() => toggleSort("confidence")} className="n sortable">
                          Confidence {sortIndicator("confidence")}
                        </th>
                        <th onClick={() => toggleSort("trade_count")} className="n sortable">
                          Closed Trades {sortIndicator("trade_count")}
                        </th>
                        <th onClick={() => toggleSort("generated_at_ms")} className="n sortable">
                          Scored At {sortIndicator("generated_at_ms")}
                        </th>
                        <th style={{ textAlign: "center" }}>Report</th>
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
                              className="mono"
                              style={{ color: "var(--amber)", fontWeight: 500 }}
                            >
                              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                                <span>{row.code}</span>
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
                                  📋
                                </button>
                              </span>
                            </td>
                            <td>{row.venue_asset || "—"}</td>
                            <td>{renderVerdictTag(row.verdict)}</td>
                            <td
                              className="n mono"
                              style={{
                                fontWeight: 600,
                                color: riskColor(row.risk),
                              }}
                            >
                              {typeof row.risk === "number" ? row.risk.toFixed(0) : "—"}
                            </td>
                            <td className="n mono">
                              {typeof row.quality === "number" ? row.quality.toFixed(0) : "—"}
                            </td>
                            <td className="n mono">
                              {typeof row.confidence === "number" ? `${row.confidence.toFixed(0)}%` : "—"}
                            </td>
                            <td className="n mono">
                              {typeof row.trade_count === "number" ? row.trade_count.toLocaleString("en-US") : "—"}
                            </td>
                            <td
                              className="n mono"
                              style={{ color: "var(--ink-2)", fontSize: "12px" }}
                            >
                              <span>{formatTimestampMs(row.generated_at_ms)}</span>
                              {stale && (
                                <span
                                  className="tag stop"
                                  style={{
                                    marginLeft: 6,
                                    borderColor: "var(--amber)",
                                    color: "var(--amber)",
                                  }}
                                  title="Scored more than 24 hours ago"
                                >
                                  &gt;24h
                                </span>
                              )}
                            </td>
                            <td style={{ textAlign: "center" }}>
                              <button
                                type="button"
                                className="btn-detail"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openBot(row.code);
                                }}
                              >
                                View report →
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
                  <span className="search-icon">🔍</span>
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
                        <th style={{ textAlign: "left" }}>Portfolio ID</th>
                        <th>Member Bots</th>
                        <th className="n">Bot Count</th>
                        <th>Portfolio Verdict</th>
                        <th className="n">Avg. Correlation</th>
                        <th className="n">Portfolio Risk</th>
                        <th className="n">Joint Max DD</th>
                        <th className="n">Analyzed At</th>
                        <th style={{ textAlign: "center" }}>Report</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visiblePortfolioRuns.map((run) => (
                        <tr
                          key={run.portfolio_id}
                          className="rowlink"
                          onClick={() => openPortfolio(run.portfolio_id, run)}
                          title={`View portfolio report ${run.portfolio_id}`}
                        >
                          <td style={{ textAlign: "left" }}>
                            <span className="mono" style={{ fontWeight: 700, color: "#38bdf8" }}>
                              {run.portfolio_id}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                              {run.members?.map((m) => (
                                <span
                                  key={m.code}
                                  className="tag"
                                  style={{
                                    fontSize: 11,
                                    background: "rgba(255, 255, 255, 0.06)",
                                    borderColor: "rgba(255, 255, 255, 0.12)",
                                  }}
                                  title={`${m.name || m.code} (${m.symbol})`}
                                >
                                  {m.name || m.code}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="n mono" style={{ fontWeight: 600 }}>
                            {run.member_count || run.members?.length || 0}
                          </td>
                          <td>{renderPortfolioVerdictTag(run.verdict)}</td>
                          <td
                            className="n mono"
                            style={{
                              fontWeight: 700,
                              color:
                                typeof run.average_pearson === "number"
                                  ? run.average_pearson >= 0.6
                                    ? "#f43f5e"
                                    : run.average_pearson >= 0.3
                                    ? "#f59e0b"
                                    : "#10b981"
                                  : "var(--ink-3)",
                            }}
                          >
                            {typeof run.average_pearson === "number" ? run.average_pearson.toFixed(2) : "—"}
                          </td>
                          <td
                            className="n mono"
                            style={{
                              fontWeight: 700,
                              color: riskColor(run.portfolio_risk_score),
                            }}
                          >
                            {typeof run.portfolio_risk_score === "number"
                              ? run.portfolio_risk_score.toFixed(0)
                              : "—"}
                          </td>
                          <td className="n mono">
                            {typeof run.joint_max_drawdown === "number"
                              ? `${run.joint_max_drawdown.toFixed(1)}%`
                              : "—"}
                          </td>
                          <td className="n mono" style={{ color: "var(--ink-2)", fontSize: "12px" }}>
                            {formatTimestampMs(run.timestamp || run.as_of_ms)}
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <button
                              type="button"
                              className="btn-detail"
                              onClick={(e) => {
                                e.stopPropagation();
                                openPortfolio(run.portfolio_id, run);
                              }}
                            >
                              View portfolio details →
                            </button>
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
          <div className="head">
            <div className="crumb">MONITORING SYSTEM · ASSESSMENT TOOL</div>
            <div className="head-row">
              <h1>Look Up &amp; Analyze Bot</h1>
            </div>
            <p>
              Enter an OKX bot identifier (uniqueCode) for a single analysis, or enter multiple codes separated by commas/spaces to run a portfolio and measure cross-correlation.
            </p>
          </div>

          <Block
            title="Direct Quantitative Assessment from OKX"
            note="Monte Carlo Engine &amp; Portfolio Risk Assessment"
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
            onBack={() => setSearchParams({ tab: "bots" })}
            onOpenBot={openBot}
          />
        </section>
      )}
    </div>
  );
}

import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getJson } from "../api/client.js";
import AnalyzeFlow from "../components/AnalyzeFlow.jsx";
import AdminOverview from "../components/AdminOverview.jsx";
import BotDetailView from "../components/BotDetailView.jsx";
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
  const [loadState, setLoadState] = useState("loading");
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [sortKey, setSortKey] = useState("risk");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { ok, data } = await getJson("/api/bots");
      if (cancelled) return;
      if (!ok) {
        setError(data.message || "Could not load the bot list.");
        setLoadState("error");
        return;
      }
      const rawRows = Array.isArray(data.bots) ? data.bots : [];
      setRows(rawRows.filter((row) => row && typeof row.code === "string"));
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
          {/* KPI Cards, Donut Chart, Risk Distribution Bars & Veto Bars */}
          {/* `onFilterVerdict`: từ biểu đồ tròn nhảy thẳng sang tab Danh sách
              bot ĐÃ LỌC sẵn theo đúng nhóm vừa bấm. Dùng lại chính ô tìm
              kiếm sẵn có (`query` đã so khớp cả `verdict`, xem `visibleRows`)
              nên không đẻ thêm một cơ chế lọc thứ hai phải giữ đồng bộ. */}
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
      {/* TAB 2: LIST BOT (DANH SÁCH BOT) */}
      {/* ========================================================================= */}
      {currentTab === "bots" && (
        <section className="tab-section tab-bots">
          <div className="head">
            <div className="crumb">MONITORING SYSTEM · BOT CATALOG</div>
            <div className="head-row">
              <h1>Analyzed bot list</h1>
            </div>
            <p>
              The full bot catalog with risk score, quality, confidence, and detailed pagination. Click a bot to view its report.
            </p>
          </div>

          <Block
            title="Bot assessment data table"
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
                Click any row to view the full report (Result · Market · Trades)
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
                      <th
                        onClick={() => toggleSort("name")}
                        className="sortable"
                      >
                        Bot Name {sortIndicator("name")}
                      </th>
                      <th
                        onClick={() => toggleSort("code")}
                        className="sortable"
                      >
                        Bot Code {sortIndicator("code")}
                      </th>
                      <th
                        onClick={() => toggleSort("venue_asset")}
                        className="sortable"
                      >
                        Venue / Asset {sortIndicator("venue_asset")}
                      </th>
                      <th
                        onClick={() => toggleSort("verdict")}
                        className="sortable"
                      >
                        Verdict {sortIndicator("verdict")}
                      </th>
                      <th
                        onClick={() => toggleSort("risk")}
                        className="n sortable"
                      >
                        Risk Score {sortIndicator("risk")}
                      </th>
                      <th
                        onClick={() => toggleSort("quality")}
                        className="n sortable"
                      >
                        Quality {sortIndicator("quality")}
                      </th>
                      <th
                        onClick={() => toggleSort("confidence")}
                        className="n sortable"
                      >
                        Confidence {sortIndicator("confidence")}
                      </th>
                      <th
                        onClick={() => toggleSort("trade_count")}
                        className="n sortable"
                      >
                        Closed Trades {sortIndicator("trade_count")}
                      </th>
                      <th
                        onClick={() => toggleSort("generated_at_ms")}
                        className="n sortable"
                      >
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
                          title={`View bot ${row.code} details (switches within this tab)`}
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
                            {typeof row.risk === "number"
                              ? row.risk.toFixed(0)
                              : "—"}
                          </td>
                          <td className="n mono">
                            {typeof row.quality === "number"
                              ? row.quality.toFixed(0)
                              : "—"}
                          </td>
                          <td className="n mono">
                            {typeof row.confidence === "number"
                              ? `${row.confidence.toFixed(0)}%`
                              : "—"}
                          </td>
                          <td className="n mono">
                            {typeof row.trade_count === "number"
                              ? row.trade_count.toLocaleString("en-US")
                              : "—"}
                          </td>
                          <td
                            className="n mono"
                            style={{
                              color: "var(--ink-2)",
                              fontSize: "12px",
                            }}
                          >
                            <span>
                              {formatTimestampMs(row.generated_at_ms)}
                            </span>
                            {stale && (
                              <span
                                className="tag stop"
                                style={{
                                  marginLeft: 6,
                                  borderColor: "var(--amber)",
                                  color: "var(--amber)",
                                }}
                                title="Scored more than 24 hours ago -- open it to run a LIVE analysis"
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
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: TRA CỨU & PHÂN TÍCH BOT */}
      {/* ========================================================================= */}
      {currentTab === "analyze" && (
        <section className="tab-section tab-analyze">
          <div className="head">
            <div className="crumb">MONITORING SYSTEM · ASSESSMENT TOOL</div>
            <div className="head-row">
              <h1>Look up &amp; analyze a new bot</h1>
            </div>
            <p>
              Enter a bot's OKX identifier (uniqueCode) for instant assessment with a multi-dimensional risk model and Monte Carlo simulation.
            </p>
          </div>

          <Block
            title="Live assessment directly from OKX"
            note="Monte Carlo engine &amp; risk assessment"
          >
            <AnalyzeFlow onOpenBot={openBot} />
          </Block>
        </section>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: BÁO CÁO CHI TIẾT BOT (BOT DETAIL REPORT VIEW) */}
      {/* ========================================================================= */}
      {currentTab === "bot" && (
        <section className="tab-section tab-bot-detail">
          <BotDetailView
            code={searchParams.get("code")}
            onBack={() => setSearchParams({ tab: "bots" })}
          />
        </section>
      )}
    </div>
  );
}

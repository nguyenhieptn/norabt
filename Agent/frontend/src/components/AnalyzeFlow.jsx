import React, { useEffect, useRef, useState } from "react";
import { getJson, postJson } from "../api/client.js";
import { useSession } from "../context/SessionContext.jsx";
import BotSummaryCard from "./BotSummaryCard.jsx";

const STEP = {
  INPUT: "input",
  LOOKING_UP: "looking_up",
  SUMMARY: "summary",
  PORTFOLIO_SUMMARY: "portfolio_summary",
  ANALYZING: "analyzing",
  WAITING: "waiting",
  PORTFOLIO_WAITING: "portfolio_waiting",
};

// 4 quantitative steps for single-bot analysis
const PIPELINE_STEPS = [
  {
    id: "ledger",
    title: "Load & verify OKX order book data",
    desc: "Connecting to the OKX API, loading open positions, the last 100 filled orders, checking order book integrity, and computing trading cadence and AUM ratio.",
  },
  {
    id: "markets",
    title: "Related market analysis & volatility correlation",
    desc: "Querying the main pairs being traded (BTC, ETH, SOL...), loading 1H/4H/1D candle data and orderbook depth, measuring the volatility regime, and checking for strategy drift.",
  },
  {
    id: "scoring",
    title: "10-dimension risk scoring & Monte Carlo simulation",
    desc: "Running 10,000 Monte Carlo distribution simulations, bootstrap testing, measuring tail risk (VaR/CVaR), liquidity risk, and max drawdown.",
  },
  {
    id: "decision",
    title: "Verdict synthesis & report generation",
    desc: "Aggregating the safety score, classifying risk (Very Low / Low / Medium / High / Extremely Dangerous), generating a quantitative narrative summary, and saving the record.",
  },
];

// 4 quantitative steps for portfolio analysis
const PORTFOLIO_STEPS = [
  {
    id: "members_ledger",
    title: "Collect & reconcile N bots' order books from OKX",
    desc: "Connecting to the OKX API concurrently, extracting each bot's filled orders, open position state, and trading cadence.",
  },
  {
    id: "timeseries_align",
    title: "Normalize time series & related market analysis",
    desc: "Aligning PnL timelines to common time buckets, measuring exposure overlap and active markets.",
  },
  {
    id: "correlation_matrix",
    title: "Compute the multi-dimensional correlation matrix (Pearson & Spearman)",
    desc: "Measuring the linear correlation coefficient (PnL correlation) and rank volatility, testing p-values, and detecting false-diversification traps.",
  },
  {
    id: "joint_monte_carlo",
    title: "Joint portfolio risk Monte Carlo simulation (10,000 scenarios)",
    desc: "Running the joint distribution simulation, measuring Joint Max Drawdown, Joint VaR/CVaR 95%, and the actual risk reduction ratio (Diversification Benefit).",
  },
];

const POLL_FAST_MS = 1500;
const POLL_SLOW_MS = 3000;
const POLL_SLOW_AFTER_MS = 30000;
const POLL_TIMEOUT_MS = 90000;

function formatDateTime(ms) {
  if (!ms || !Number.isFinite(ms)) return "";
  const d = new Date(ms);
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const date = d.toLocaleDateString("en-US", { day: "2-digit", month: "2-digit", year: "numeric" });
  return `${time} ${date}`;
}

function getLogTime() {
  const d = new Date();
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function parseInputCodes(str) {
  if (!str) return [];
  const items = str.trim().split(/[\s,;\n]+/).map((s) => s.trim()).filter(Boolean);
  return [...new Set(items)];
}

// A fabricated portfolio used to be generated here whenever the API call
// failed, with correlations computed as `0.2 + ((i + j) % 5) * 0.12` and an
// evidence line reading "Observed trade sample size: 95 shared trading
// buckets". It rendered identically to a real assessment. On a tool whose
// entire job is telling someone how much money they can lose, a plausible
// invented number is worse than an error message, because the reader cannot
// tell the two apart. The failure is now surfaced instead.

export default function AnalyzeFlow({ onOpenBot, onOpenPortfolio }) {
  const { session } = useSession();
  const [step, setStep] = useState(STEP.INPUT);
  const [code, setCode] = useState("");
  const [lookup, setLookup] = useState(null);
  const [portfolioLookups, setPortfolioLookups] = useState([]);
  const [portfolioActiveStep, setPortfolioActiveStep] = useState(0);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [preAnalyzed, setPreAnalyzed] = useState(null);
  const [scoredAtMs, setScoredAtMs] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingJob, setPendingJob] = useState(null);

  const detectedCodes = parseInputCodes(code);
  const isMulti = detectedCodes.length > 1;

  function reset() {
    setStep(STEP.INPUT);
    setLookup(null);
    setPortfolioLookups([]);
    setError(null);
    setNotice(null);
    setPendingJob(null);
    setPreAnalyzed(null);
    setScoredAtMs(null);
    setShowConfirmModal(false);
  }

  async function handleLookupSubmit(event) {
    event.preventDefault();
    const codes = parseInputCodes(code);
    if (codes.length === 0) {
      setError("Please enter at least one OKX bot identifier (uniqueCode).");
      return;
    }
    setError(null);
    setNotice(null);
    setPreAnalyzed(null);
    setScoredAtMs(null);
    setShowConfirmModal(false);
    setStep(STEP.LOOKING_UP);

    if (codes.length === 1) {
      // 1 ID -> ordinary single-bot run, same as the original core
      const trimmed = codes[0];
      const { ok, data } = await postJson("/api/lookup", { code: trimmed });
      if (!ok) {
        setError(data.message || "Could not look up this bot code.");
        setStep(STEP.INPUT);
        return;
      }
      if (data.status === "NOT_FOUND") {
        setError(data.note || "No bot with this code was found on OKX.");
        setStep(STEP.INPUT);
        return;
      }
      setLookup(data);

      let isAnalyzed = false;
      let scoredTime = null;
      try {
        const statusResp = await getJson("/api/analyze/status?code=" + encodeURIComponent(trimmed));
        if (statusResp.ok && statusResp.data && statusResp.data.report_ready) {
          isAnalyzed = true;
          if (statusResp.data.scored_at_ms) {
            scoredTime = statusResp.data.scored_at_ms;
          }
        }
      } catch (_) {}
      setPreAnalyzed(isAnalyzed);
      setScoredAtMs(scoredTime);
      setStep(STEP.SUMMARY);
    } else {
      // Multiple IDs -> portfolio run
      try {
        const lookups = await Promise.all(
          codes.map(async (c) => {
            const res = await postJson("/api/lookup", { code: c });
            if (res.ok && res.data && res.data.status !== "NOT_FOUND") {
              return { code: c, ok: true, data: res.data };
            }
            return {
              code: c,
              ok: false,
              error: res.data?.note || res.data?.message || "No bot found on OKX",
            };
          })
        );
        setPortfolioLookups(lookups);
        setStep(STEP.PORTFOLIO_SUMMARY);
      } catch (err) {
        setError("Connection error while looking up the bot list: " + err.message);
        setStep(STEP.INPUT);
      }
    }
  }

  async function handleConfirmAnalyze(forceFresh = false) {
    if (!lookup) return;
    setError(null);
    setNotice(null);
    setShowConfirmModal(false);

    const targetUrl = buildFallbackDetailUrl(session, lookup.code);
    setPendingJob({
      code: lookup.code,
      botName: lookup.name || lookup.code,
      targetUrl,
      forceFresh,
    });
    setStep(STEP.WAITING);

    const payload = { code: lookup.code };
    if (forceFresh) {
      payload.refresh = true;
    }

    try {
      const { ok, data } = await postJson("/api/analyze", payload);
      if (!ok) {
        setError(data.message || "Analysis failed.");
        setPendingJob(null);
        setStep(STEP.SUMMARY);
        return;
      }

      if (data.status !== "PENDING") {
        if (data.report_url) {
          setPendingJob((prev) => (prev ? { ...prev, targetUrl: data.report_url } : null));
        }
      }
    } catch (err) {
      setError("Server connection error: " + (err.message || String(err)));
      setPendingJob(null);
      setStep(STEP.SUMMARY);
    }
  }

  async function handleConfirmAnalyzePortfolio() {
    const validBots = portfolioLookups.filter((b) => b.ok);
    if (validBots.length < 2) {
      setError("At least 2 valid OKX bots are needed to run a portfolio analysis.");
      return;
    }
    setError(null);
    setNotice(null);
    setStep(STEP.PORTFOLIO_WAITING);
    setPortfolioActiveStep(0);

    const validCodes = validBots.map((b) => b.code);

    try {
      const t1 = setTimeout(() => setPortfolioActiveStep(1), 1800);
      const t2 = setTimeout(() => setPortfolioActiveStep(2), 3800);
      const t3 = setTimeout(() => setPortfolioActiveStep(3), 6000);

      const resp = await postJson("/api/portfolio/analyze", { codes: validCodes });
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      // The server returns ONE report for the whole set: the same payload
      // shape a single bot produces, plus a `portfolio` block. `portfolio_id`
      // is what the report page is addressed by.
      const portfolioId = resp.ok && resp.data ? resp.data.portfolio_id : null;
      if (portfolioId) {
        if (onOpenPortfolio) {
          onOpenPortfolio(portfolioId, resp.data);
        } else {
          window.location.hash = `#/user?tab=portfolio&id=${encodeURIComponent(portfolioId)}`;
        }
        return;
      }

      const reason =
        (resp.data && (resp.data.limited_reason || resp.data.error)) ||
        "The portfolio analysis did not return a result.";
      setError(reason);
      setStep(STEP.PORTFOLIO_SUMMARY);
    } catch (err) {
      setError(
        `Could not run the portfolio analysis: ${err?.message || err}. ` +
          "Nothing is shown rather than an estimate, because an invented " +
          "correlation reads exactly like a measured one."
      );
      setStep(STEP.PORTFOLIO_SUMMARY);
    }
  }

  function handleOverlayDismiss() {
    setPendingJob(null);
    setStep(STEP.SUMMARY);
    setNotice(
      "Stopped watching here -- the analysis is still running on the server. " +
        "Click \"Analyze this bot\" again any time to reopen the progress, " +
        "or come back to the report link in a few dozen seconds."
    );
  }

  function handleDoneNavigation(targetCode, targetUrl) {
    if (onOpenBot) {
      onOpenBot(targetCode);
    } else if (window.location.hash.startsWith("#/admin")) {
      window.location.hash = `#/admin?tab=bot&code=${encodeURIComponent(targetCode)}`;
    } else if (window.location.hash.startsWith("#/user")) {
      window.location.hash = `#/user?tab=bot&code=${encodeURIComponent(targetCode)}`;
    } else {
      window.location.href = targetUrl;
    }
  }

  return (
    <div className="analyze-flow-container">
      {error ? <div className="notice notice-danger">{error}</div> : null}
      {!error && notice ? <div className="notice notice-warning">{notice}</div> : null}

      {step === STEP.INPUT || step === STEP.LOOKING_UP ? (
        <form onSubmit={handleLookupSubmit} className="analyze-search-form">
          <div className="analyze-search-bar">
            <div className="analyze-search-input-wrap">
              <span className="analyze-search-icon">🔍</span>
              <input
                id="bot-code"
                type="text"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Enter an OKX bot ID (e.g. EF1CC6F40E834D1A), or multiple IDs separated by commas/spaces..."
                disabled={step === STEP.LOOKING_UP}
                autoComplete="off"
                className="analyze-search-input"
              />
              {code ? (
                <button
                  type="button"
                  className="analyze-search-clear"
                  onClick={() => setCode("")}
                  title="Clear input"
                >
                  ✕
                </button>
              ) : null}
            </div>
            <button
              type="submit"
              className="btn pri analyze-search-btn"
              disabled={step === STEP.LOOKING_UP || !code.trim()}
            >
              {step === STEP.LOOKING_UP ? (
                <>
                  <span
                    className="stepper-spinner"
                    style={{
                      width: 14,
                      height: 14,
                      display: "inline-block",
                      marginRight: 8,
                      verticalAlign: "middle",
                    }}
                  />
                  Looking up...
                </>
              ) : isMulti ? (
                `Look up portfolio (${detectedCodes.length})`
              ) : (
                "Look up bot"
              )}
            </button>
          </div>

          {/* PORTFOLIO GUIDANCE & NOTICE */}
          {isMulti ? (
            <div
              style={{
                marginTop: 12,
                padding: "12px 16px",
                borderRadius: 8,
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.25)",
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
              }}
            >
              <span style={{ fontSize: 20 }}>🔮</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8" }}>
                  PORTFOLIO MODE DETECTED ({detectedCodes.length} BOTS)
                </div>
                <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 2 }}>
                  You entered multiple IDs separated by commas or spaces. Clicking Look Up will switch to <strong>Portfolio Analysis</strong> mode to measure strategy correlation and joint portfolio risk.
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                  {detectedCodes.map((c, i) => (
                    <span
                      key={i}
                      className="mono"
                      style={{
                        fontSize: 11,
                        padding: "3px 8px",
                        borderRadius: 4,
                        background: "rgba(255, 255, 255, 0.08)",
                        color: "var(--amber)",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                      }}
                    >
                      #{i + 1}: {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="analyze-search-hint">
              <span className="analyze-hint-pill">Hint</span>
              <span className="analyze-hint-text">
                Enter <strong>1 ID</strong> for an ordinary single-bot analysis. To run a multi-bot portfolio analysis, enter <strong>multiple IDs</strong> separated by commas (<code>,</code>) or spaces.
              </span>
            </div>
          )}
        </form>
      ) : null}

      {/* MODE 1: SINGLE-BOT SUMMARY (SAME AS THE ORIGINAL CORE) */}
      {step === STEP.SUMMARY && lookup ? (
        <>
          <BotSummaryCard lookup={lookup} />

          {preAnalyzed === true ? (
            <div className="analyze-status-banner banner-existing">
              <span className="banner-icon">ℹ️</span>
              <div className="banner-content">
                <div className="banner-title">THIS BOT HAS ALREADY BEEN ANALYZED</div>
                <div className="banner-desc">
                  The system has a stored quantitative assessment for this bot
                  {scoredAtMs ? ` (last run: ${formatDateTime(scoredAtMs)})` : ""}.
                  Click <strong>Analyze this bot</strong> below to view the existing result or re-scan its order book.
                </div>
              </div>
            </div>
          ) : preAnalyzed === false ? (
            <div className="analyze-status-banner banner-new">
              <span className="banner-icon">✨</span>
              <div className="banner-content">
                <div className="banner-title">NEW BOT — NEVER ANALYZED</div>
                <div className="banner-desc">
                  This bot has no stored data yet. Clicking start will connect directly to OKX to load the full order book, analyze related markets, score all 10 risk dimensions, and run a 10,000-scenario Monte Carlo simulation.
                </div>
              </div>
            </div>
          ) : null}

          <div className="btn-row">
            <button
              type="button"
              className="btn pri"
              onClick={() => {
                if (preAnalyzed === true) {
                  setShowConfirmModal(true);
                } else {
                  handleConfirmAnalyze(false);
                }
              }}
            >
              {preAnalyzed === true ? "⚡ Analyze this bot" : "🚀 Start analyzing this bot"}
            </button>
            <button type="button" className="btn" onClick={reset}>
              Enter a different code
            </button>
          </div>
        </>
      ) : null}

      {/* MODE 2: MULTI-BOT PORTFOLIO SUMMARY */}
      {step === STEP.PORTFOLIO_SUMMARY && (
        <div className="portfolio-summary-block">
          <div
            style={{
              padding: "20px 24px",
              borderRadius: 10,
              background: "linear-gradient(135deg, rgba(56, 189, 248, 0.12) 0%, rgba(20, 20, 24, 0.8) 100%)",
              border: "1px solid rgba(56, 189, 248, 0.35)",
              marginBottom: 24,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 24 }}>🔮</span>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#38bdf8" }}>
                CONFIRM {portfolioLookups.length}-BOT PORTFOLIO RUN
              </h3>
            </div>
            <p style={{ margin: 0, fontSize: 14, color: "var(--ink)", lineHeight: 1.6 }}>
              The system found <strong>{portfolioLookups.filter((b) => b.ok).length}</strong> / {portfolioLookups.length} valid bots on OKX. Click the button below to align time series, compute the multi-dimensional correlation matrix (Pearson &amp; Spearman), and run the joint portfolio Monte Carlo simulation.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 14,
              marginBottom: 24,
            }}
          >
            {portfolioLookups.map((item, idx) => {
              const bot = item.data?.bot || item.data;
              return (
                <div
                  key={idx}
                  className="card"
                  style={{
                    padding: 16,
                    border: item.ok ? "1px solid rgba(255, 255, 255, 0.12)" : "1px solid rgba(244, 63, 94, 0.4)",
                    background: item.ok ? "var(--card-bg)" : "rgba(244, 63, 94, 0.06)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span className="mono" style={{ fontSize: 12, color: "var(--amber)", fontWeight: 600 }}>
                      {item.code}
                    </span>
                    <span className={`tag ${item.ok ? "trend" : "stop"}`} style={{ fontSize: 11 }}>
                      {item.ok ? (item.data?.status || "OK") : "NOT FOUND"}
                    </span>
                  </div>
                  {item.ok ? (
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
                        {item.data?.name || bot?.nick_name || `Bot #${idx + 1}`}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--ink-2)", display: "flex", justifyContent: "space-between" }}>
                        <span>Pair: {item.data?.traded_symbol || bot?.symbol || "OKX"}</span>
                        <span>
                          Win rate: {typeof item.data?.win_rate === "number" ? `${(item.data.win_rate * 100).toFixed(0)}%` : "—"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: "#f43f5e" }}>
                      {item.error || "Could not load this bot's data"}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="btn-row">
            <button
              type="button"
              className="btn pri"
              disabled={portfolioLookups.filter((b) => b.ok).length < 2}
              onClick={handleConfirmAnalyzePortfolio}
            >
              🚀 Run portfolio analysis ({portfolioLookups.filter((b) => b.ok).length} bots)
            </button>
            <button type="button" className="btn" onClick={reset}>
              Enter a different list
            </button>
          </div>
        </div>
      )}

      {/* PORTFOLIO PROGRESS STEPPER */}
      {step === STEP.PORTFOLIO_WAITING && (
        <div className="portfolio-waiting-wrap" style={{ padding: "28px 0" }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <span
              className="stepper-spinner"
              style={{ width: 32, height: 32, margin: "0 auto 16px auto", display: "block" }}
            />
            <h3 style={{ margin: "0 0 8px 0", fontSize: 20, fontWeight: 700 }}>
              Running portfolio analysis for {portfolioLookups.filter((b) => b.ok).length} bots...
            </h3>
            <p style={{ margin: 0, fontSize: 14, color: "var(--ink-2)" }}>
              Loading N bots' order books, aligning PnL timelines, computing the correlation matrix, and running 10,000 joint Monte Carlo scenarios.
            </p>
          </div>

          <div className="stepper-track" style={{ maxWidth: 680, margin: "0 auto" }}>
            {PORTFOLIO_STEPS.map((s, idx) => {
              const isDone = idx < portfolioActiveStep;
              const isCurrent = idx === portfolioActiveStep;
              return (
                <div
                  key={s.id}
                  className={`stepper-node ${isDone ? "node-done" : isCurrent ? "node-active" : "node-pending"}`}
                  style={{ marginBottom: 16 }}
                >
                  <div className="stepper-bullet">
                    {isDone ? "✓" : isCurrent ? <span className="stepper-spinner" style={{ width: 12, height: 12 }} /> : idx + 1}
                  </div>
                  <div className="stepper-node-content">
                    <div className="stepper-node-title" style={{ fontSize: 14, fontWeight: 600 }}>
                      {s.title}
                    </div>
                    <div className="stepper-node-desc" style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 2 }}>
                      {s.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL WHEN THE BOT HAS ALREADY RUN */}
      {showConfirmModal && lookup && (
        <div className="analyze-confirm-backdrop" onClick={() => setShowConfirmModal(false)}>
          <div className="analyze-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="analyze-confirm-head">
              <div className="analyze-confirm-title-row">
                <h4>Confirm bot assessment</h4>
                <button
                  type="button"
                  className="analyze-confirm-close"
                  onClick={() => setShowConfirmModal(false)}
                >
                  ✕
                </button>
              </div>
              <p className="analyze-confirm-subtitle">
                Bot: <strong>{lookup.name || lookup.code}</strong>{" "}
                <span className="mono-code">({lookup.code})</span>
              </p>
            </div>

            <div className="analyze-confirm-body">
              <div className="analyze-confirm-alert">
                <div className="alert-icon">🕒</div>
                <div className="alert-text">
                  <div className="alert-title">This bot has already been analyzed</div>
                  <div className="alert-desc">
                    Time on record:{" "}
                    <strong>{formatDateTime(scoredAtMs) || "Previously stored record"}</strong>
                  </div>
                </div>
              </div>
              <p className="analyze-confirm-prompt">
                You can view the existing result immediately without waiting for it to recompute, or choose to re-analyze from scratch to scan the latest order book from OKX.
              </p>
            </div>

            <div className="analyze-confirm-actions">
              <button
                type="button"
                className="btn pri"
                onClick={() => {
                  setShowConfirmModal(false);
                  handleDoneNavigation(lookup.code, buildFallbackDetailUrl(session, lookup.code));
                }}
              >
                👁️ View existing result
              </button>
              <button
                type="button"
                className="btn btn-warning"
                onClick={() => handleConfirmAnalyze(true)}
              >
                🔄 Re-run analysis
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setShowConfirmModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP-BY-STEP PROGRESS FOR A SINGLE BOT */}
      {step === STEP.WAITING && pendingJob ? (
        <InPageAnalyzeProgress
          job={pendingJob}
          onDone={() => handleDoneNavigation(pendingJob.code, pendingJob.targetUrl)}
          onRetry={() => handleConfirmAnalyze(pendingJob.forceFresh)}
          onDismiss={handleOverlayDismiss}
        />
      ) : null}
    </div>
  );
}

function InPageAnalyzeProgress({ job, onDone, onRetry, onDismiss }) {
  const [status, setStatus] = useState({
    state: "running",
    stage: "ledger",
    stageIndex: 1,
    stageCount: 4,
    errorMessage: null,
  });
  const [elapsedSec, setElapsedSec] = useState(0);
  const [timedOut, setTimedOut] = useState(false);
  const [logs, setLogs] = useState([]);
  const [countdown, setCountdown] = useState(null);

  const startedAtRef = useRef(Date.now());
  const stoppedRef = useRef(false);
  const pollTimerRef = useRef(null);
  const clockTimerRef = useRef(null);
  const countdownTimerRef = useRef(null);
  const logEndRef = useRef(null);

  function addLog(text, type = "info") {
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        time: getLogTime(),
        type,
        text,
      },
    ]);
  }

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  useEffect(() => {
    stoppedRef.current = false;
    startedAtRef.current = Date.now();
    setTimedOut(false);
    setLogs([
      {
        id: "init-1",
        time: getLogTime(),
        type: "info",
        text: `Starting the quantitative assessment pipeline for bot [${job.code}] (${job.botName})...`,
      },
      {
        id: "init-2",
        time: getLogTime(),
        type: "step",
        text: `STEP 1: Connecting to the OKX API, loading open positions and order history...`,
      },
    ]);

    clockTimerRef.current = setInterval(() => {
      if (stoppedRef.current) return;
      const sec = Math.floor((Date.now() - startedAtRef.current) / 1000);
      setElapsedSec(sec);
      if (sec >= POLL_TIMEOUT_MS / 1000) {
        stoppedRef.current = true;
        setTimedOut(true);
        setStatus((prev) => ({ ...prev, state: "error", errorMessage: "The analysis timed out." }));
      }
    }, 500);

    async function poll() {
      if (stoppedRef.current) return;
      try {
        const { ok, data } = await getJson(`/api/analyze/status?code=${encodeURIComponent(job.code)}`);
        if (!ok || !data) return;

        if (data.stage && data.stage !== status.stage) {
          const stepObj = PIPELINE_STEPS.find((p) => p.id === data.stage);
          const stageName = stepObj ? stepObj.title : data.stage;
          addLog(`Moving to stage: ${stageName}`, "step");
        }

        if (data.state === "done" || data.report_ready) {
          stoppedRef.current = true;
          setStatus((prev) => ({ ...prev, state: "done", stageIndex: 4 }));
          addLog(`Analysis completed successfully! Preparing the report.`, "success");
          startCountdown();
          return;
        }

        if (data.state === "error") {
          stoppedRef.current = true;
          setStatus((prev) => ({ ...prev, state: "error", errorMessage: data.error_message || "An error occurred during analysis." }));
          addLog(`Error: ${data.error_message || "Analysis failed"}`, "error");
          return;
        }

        setStatus((prev) => ({
          ...prev,
          stage: data.stage || prev.stage,
          stageIndex: data.stage_index || prev.stageIndex,
        }));
      } catch (_) {}

      if (!stoppedRef.current) {
        pollTimerRef.current = setTimeout(poll, POLL_FAST_MS);
      }
    }

    pollTimerRef.current = setTimeout(poll, POLL_FAST_MS);

    return () => {
      stoppedRef.current = true;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (clockTimerRef.current) clearInterval(clockTimerRef.current);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
  }, [job.code]);

  function startCountdown() {
    let count = 2;
    setCountdown(count);
    countdownTimerRef.current = setInterval(() => {
      count -= 1;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(countdownTimerRef.current);
        onDone();
      }
    }, 1000);
  }

  return (
    <div className="inpage-progress-wrap" style={{ marginTop: 24 }}>
      <div className="stepper-track">
        {PIPELINE_STEPS.map((s, idx) => {
          const isDone = status.state === "done" || idx + 1 < status.stageIndex;
          const isCurrent = status.state !== "done" && idx + 1 === status.stageIndex;
          return (
            <div
              key={s.id}
              className={`stepper-node ${isDone ? "node-done" : isCurrent ? "node-active" : "node-pending"}`}
            >
              <div className="stepper-bullet">
                {isDone ? "✓" : isCurrent ? <span className="stepper-spinner" style={{ width: 12, height: 12 }} /> : idx + 1}
              </div>
              <div className="stepper-node-content">
                <div className="stepper-node-title">{s.title}</div>
                <div className="stepper-node-desc">{s.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="live-log-console" style={{ marginTop: 20 }}>
        <div className="console-head">
          <div className="console-title">
            <span>●</span> LIVE LOG CONSOLE · BOT [{job.code}]
          </div>
          <div className="console-timer">{elapsedSec}s</div>
        </div>
        <div className="console-body">
          {logs.map((log) => (
            <div key={log.id} className={`log-row log-${log.type}`}>
              <span className="log-time">[{log.time}]</span>
              <span className="log-text">{log.text}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {status.state === "done" && (
        <div style={{ marginTop: 16, textAlign: "center" }}>
          <button type="button" className="btn pri" onClick={onDone}>
            View report now {countdown ? `(${countdown}s)` : ""} →
          </button>
        </div>
      )}

      {status.state === "error" && (
        <div style={{ marginTop: 16, textAlign: "center" }}>
          <button type="button" className="btn pri" onClick={onRetry} style={{ marginRight: 8 }}>
            Retry
          </button>
          <button type="button" className="btn" onClick={onDismiss}>
            Close
          </button>
        </div>
      )}
    </div>
  );
}

function buildFallbackDetailUrl(session, code) {
  if (session?.userRef) {
    return `/${session.userRef}_${code}`;
  }
  return `/bot/${code}`;
}

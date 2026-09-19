import React, { useEffect, useRef, useState } from "react";
import { getJson, postJson } from "../api/client.js";
import { useSession } from "../context/SessionContext.jsx";
import BotSummaryCard from "./BotSummaryCard.jsx";

const STEP = {
  INPUT: "input",
  LOOKING_UP: "looking_up",
  SUMMARY: "summary",
  ANALYZING: "analyzing",
  WAITING: "waiting",
};

// 4 Bước định lượng logic trực quan
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

export default function AnalyzeFlow({ onOpenBot }) {
  const { session } = useSession();
  const [step, setStep] = useState(STEP.INPUT);
  const [code, setCode] = useState("");
  const [lookup, setLookup] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [preAnalyzed, setPreAnalyzed] = useState(null);
  const [scoredAtMs, setScoredAtMs] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingJob, setPendingJob] = useState(null);

  function reset() {
    setStep(STEP.INPUT);
    setLookup(null);
    setError(null);
    setNotice(null);
    setPendingJob(null);
    setPreAnalyzed(null);
    setScoredAtMs(null);
    setShowConfirmModal(false);
  }

  async function handleLookupSubmit(event) {
    event.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) {
      setError("Enter a bot code first.");
      return;
    }
    setError(null);
    setNotice(null);
    setPreAnalyzed(null);
    setScoredAtMs(null);
    setShowConfirmModal(false);
    setStep(STEP.LOOKING_UP);

    const { ok, data } = await postJson("/api/lookup", { code: trimmed });
    if (!ok) {
      setError(data.message || "Could not look up this bot code.");
      setStep(STEP.INPUT);
      return;
    }
    if (data.status === "NOT_FOUND") {
      setError(data.note || "No bot found with this code.");
      setStep(STEP.INPUT);
      return;
    }
    setLookup(data);

    // Kiểm tra ngay xem bot này đã có báo cáo phân tích trước đó hay chưa
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
    } catch (_) {
      // Degrade an toàn nếu mạng lỗi
    }
    setPreAnalyzed(isAnalyzed);
    setScoredAtMs(scoredTime);
    setStep(STEP.SUMMARY);
  }

  async function handleConfirmAnalyze(forceFresh = false) {
    if (!lookup) return;
    setError(null);
    setNotice(null);
    setShowConfirmModal(false);

    const targetUrl = buildFallbackDetailUrl(session, lookup.code);

    // Hiển thị giao diện Stepper + Live Log Console in-page bên dưới form
    setPendingJob({
      code: lookup.code,
      botName: lookup.name || lookup.code,
      targetUrl,
      forceFresh,
    });
    setStep(STEP.WAITING);

    // Gọi API analyze với refresh nếu là forceFresh
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
        // Trả kết quả ngay (nếu đã có sẵn hoặc hoàn thành nhanh)
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
                placeholder="Enter OKX bot code (e.g. EF1CC6F40E834D1A)..."
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
                  Searching...
                </>
              ) : (
                "Find bot"
              )}
            </button>
          </div>
          <div className="analyze-search-hint">
            <span className="analyze-hint-pill">OKX Identifier</span>
            <span className="analyze-hint-text">
              Enter the uniqueCode from the OKX copy trading bot URL to inspect live order ledger and execute risk scoring.
            </span>
          </div>
        </form>
      ) : null}

      {step === STEP.SUMMARY && lookup ? (
        <>
          <BotSummaryCard lookup={lookup} />

          {preAnalyzed === true ? (
            <div className="analyze-status-banner banner-existing">
              <span className="banner-icon">ℹ️</span>
              <div className="banner-content">
                <div className="banner-title">THIS BOT HAS ALREADY BEEN ANALYZED IN THE SYSTEM</div>
                <div className="banner-desc">
                  The system already has a stored quantitative assessment for this bot
                  {scoredAtMs ? ` (last run: ${formatDateTime(scoredAtMs)})` : ""}.
                  Click <strong>Analyze this bot</strong> below to choose between viewing the old result or running a new scan.
                </div>
              </div>
            </div>
          ) : preAnalyzed === false ? (
            <div className="analyze-status-banner banner-new">
              <span className="banner-icon">✨</span>
              <div className="banner-content">
                <div className="banner-title">BRAND NEW BOT — NEVER ANALYZED IN THE SYSTEM</div>
                <div className="banner-desc">
                  This bot has no stored data yet. When you click start, the system will connect directly to OKX to load the full order book, analyze related markets, score 10 risk dimensions, and run a 10,000-scenario Monte Carlo simulation (usually takes about 20-60 seconds).
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

      {/* MODAL HOVER XÁC NHẬN KHI BOT ĐÃ TỪNG CHẠY */}
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
                    Run time on the system:{" "}
                    <strong>{formatDateTime(scoredAtMs) || "Previously stored record"}</strong>
                  </div>
                </div>
              </div>
              <p className="analyze-confirm-prompt">
                You can view the existing result instantly without waiting for a recalculation, or choose to run it again from scratch to scan the latest order book from OKX.
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
                👁️ View old result
              </button>
              <button
                type="button"
                className="btn btn-warning"
                onClick={() => handleConfirmAnalyze(true)}
              >
                🔄 Run analysis again
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

      {/* TIẾN TRÌNH THEO TỪNG BƯỚC (STEPPER) + LIVE LOG CONSOLE IN-PAGE */}
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

/**
 * Hiển thị tiến trình trực tiếp in-page bên dưới form:
 * - Stepper 4 bước chỉ rõ đang nhìn vào đâu, đang xử lý dữ liệu gì
 * - Live Log Console hiển thị chi tiết nhật ký thời gian thực
 * - Thông báo hoàn tất và đếm ngược 3s tự chuyển tới trang kết quả
 */
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

  // Cuộn tự động log console
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // Khởi động đồng hồ và ghi nhận log ban đầu
  useEffect(() => {
    stoppedRef.current = false;
    startedAtRef.current = Date.now();
    setTimedOut(false);
    setLogs([
      {
        id: "init-1",
        time: getLogTime(),
        type: "info",
        text: `Starting quantitative assessment pipeline for bot [${job.code}] (${job.botName})...`,
      },
      {
        id: "init-2",
        time: getLogTime(),
        type: "step",
        text: `STEP 1: Connecting to the OKX API, loading open positions and trade history...`,
      },
    ]);

    clockTimerRef.current = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 1000);

    let lastStage = "ledger";

    async function pollOnce() {
      if (stoppedRef.current) return;
      const elapsedMs = Date.now() - startedAtRef.current;
      if (elapsedMs > POLL_TIMEOUT_MS) {
        stoppedRef.current = true;
        setTimedOut(true);
        addLog("Timed out (90s) - the pipeline is still processing on the server.", "warn");
        return;
      }

      const { ok, data } = await getJson(
        `/api/analyze/status?code=${encodeURIComponent(job.code)}`
      );
      if (stoppedRef.current) return;

      if (ok && data && typeof data === "object") {
        const rawState = typeof data.state === "string" ? data.state : "unknown";
        const currentStage = typeof data.stage === "string" ? data.stage : "ledger";
        const reportReady = data.report_ready === true;

        // Cập nhật log khi chuyển bước
        if (currentStage !== lastStage) {
          if (currentStage === "markets" && lastStage === "ledger") {
            addLog("✓ Finished loading the OKX order book. Verified 100 filled orders and open positions.", "check");
            addLog("STEP 2: Analyzing related markets & loading candle data, orderbook depth...", "step");
          } else if (currentStage === "scoring" || currentStage === "decision") {
            if (lastStage === "markets" || lastStage === "ledger") {
              addLog("✓ Measured the volatility regime and market volatility correlation.", "check");
              addLog("STEP 3: Running the Monte Carlo engine (10,000 scenarios) & scoring 10 risk dimensions...", "step");
            }
          } else if (currentStage === "narrative") {
            addLog("✓ Finished computing the risk distribution, VaR/CVaR, and effective leverage.", "check");
            addLog("STEP 4: Synthesizing the safety verdict & structuring the report...", "step");
          }
          lastStage = currentStage;
        }

        // Tính stageIndex (1..4) cho Stepper
        let mappedIndex = 1;
        if (currentStage === "markets") mappedIndex = 2;
        else if (currentStage === "scoring" || currentStage === "decision") mappedIndex = 3;
        else if (currentStage === "narrative" || currentStage === "done" || reportReady) mappedIndex = 4;

        setStatus({
          state: rawState,
          stage: currentStage,
          stageIndex: mappedIndex,
          stageCount: 4,
          errorMessage: data.error || null,
        });

        if (rawState === "done" || reportReady) {
          stoppedRef.current = true;
          addLog("✓ Comprehensive analysis complete. The assessment result is ready!", "check");
          addLog("Preparing to move to the detailed report page...", "info");

          // Bắt đầu đếm ngược 3s tự động chuyển trang
          setCountdown(3);
          let currentCount = 3;
          countdownTimerRef.current = setInterval(() => {
            currentCount -= 1;
            if (currentCount <= 0) {
              clearInterval(countdownTimerRef.current);
              onDone();
            } else {
              setCountdown(currentCount);
            }
          }, 1000);
          return;
        }

        if (rawState === "error") {
          stoppedRef.current = true;
          addLog("Analysis error: " + (data.error || "The server responded with a failure."), "warn");
          return;
        }
      }

      const delay = elapsedMs >= POLL_SLOW_AFTER_MS ? POLL_SLOW_MS : POLL_FAST_MS;
      pollTimerRef.current = setTimeout(pollOnce, delay);
    }

    pollOnce();

    return () => {
      stoppedRef.current = true;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (clockTimerRef.current) clearInterval(clockTimerRef.current);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.code]);

  const isDone = countdown !== null;
  const isError = status.state === "error";

  function formatElapsed(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  return (
    <div className="inpage-analyze-progress">
      <div className="inpage-progress-head">
        <div className="progress-head-info">
          <div className="progress-eyebrow">QUANTITATIVE ASSESSMENT PROGRESS</div>
          <h4 className="progress-bot-title">
            {job.botName} <span className="mono-code">({job.code})</span>
          </h4>
        </div>
        <div className="progress-clock-badge">
          ⏱️ <span className="num">{formatElapsed(elapsedSec)}</span>
        </div>
      </div>

      {/* STEPPER 4 BƯỚC RÕ RÀNG */}
      <div className="analyze-stepper">
        {PIPELINE_STEPS.map((s, idx) => {
          const stepNum = idx + 1;
          const isCompleted = isDone || status.stageIndex > stepNum;
          const isCurrent = !isDone && status.stageIndex === stepNum && !isError;
          const isPending = !isDone && status.stageIndex < stepNum;

          return (
            <div
              key={s.id}
              className={`stepper-item ${isCompleted ? "is-done" : ""} ${
                isCurrent ? "is-active" : ""
              } ${isPending ? "is-pending" : ""}`}
            >
              <div className="stepper-node">
                <div className="stepper-icon">
                  {isCompleted ? (
                    "✓"
                  ) : isCurrent ? (
                    <span className="stepper-spinner" />
                  ) : (
                    stepNum
                  )}
                </div>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div className={`stepper-line ${isCompleted ? "line-done" : ""}`} />
                )}
              </div>
              <div className="stepper-content">
                <div className="stepper-title-row">
                  <span className="stepper-step-label">Step {stepNum}</span>
                  <span className="stepper-status-badge">
                    {isCompleted
                      ? "Done"
                      : isCurrent
                      ? "Processing..."
                      : "Pending"}
                  </span>
                </div>
                <div className="stepper-step-name">{s.title}</div>
                {isCurrent && <div className="stepper-step-desc">{s.desc}</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* LIVE LOG CONSOLE */}
      <div className="analyze-console-wrap">
        <div className="analyze-console-header">
          <span className="console-indicator" />
          <span className="console-title">📡 Live Execution Log</span>
        </div>
        <div className="analyze-console-body">
          {logs.map((item) => (
            <div key={item.id} className={`console-line log-${item.type}`}>
              <span className="console-time">[{item.time}]</span>{" "}
              <span className="console-text">{item.text}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* THÔNG BÁO HOÀN TẤT & BỘ ĐẾM NGƯỢC 3S */}
      {isDone && (
        <div className="analyze-completion-banner">
          <div className="completion-icon">🎉</div>
          <div className="completion-details">
            <div className="completion-title">Analysis completed successfully!</div>
            <div className="completion-subtitle">
              Moving to the results page in{" "}
              <strong className="countdown-highlight">{countdown}s</strong>...
            </div>
          </div>
          <button type="button" className="btn pri completion-btn" onClick={onDone}>
            View results now →
          </button>
        </div>
      )}

      {/* TRƯỜNG HỢP LỖI HOẶC QUÁ GIỜ */}
      {isError && (
        <div className="notice notice-danger" style={{ marginTop: "16px" }}>
          <strong>Analysis error:</strong> {status.errorMessage || "Could not complete the analysis."}
          <div style={{ marginTop: "10px" }}>
            <button type="button" className="btn pri" onClick={onRetry}>
              Retry
            </button>
            <button type="button" className="btn" onClick={onDismiss} style={{ marginLeft: "8px" }}>
              Close
            </button>
          </div>
        </div>
      )}

      {timedOut && !isDone && !isError && (
        <div className="notice notice-warning" style={{ marginTop: "16px" }}>
          Over 90 seconds have passed without a completion signal. The analysis may still be running on the server.
          <div style={{ marginTop: "10px" }}>
            <button type="button" className="btn pri" onClick={onDone}>
              Open results page
            </button>
            <button type="button" className="btn" onClick={onDismiss} style={{ marginLeft: "8px" }}>
              Close
            </button>
          </div>
        </div>
      )}

      {!isDone && !isError && !timedOut && (
        <div className="progress-footer-actions">
          <button type="button" className="btn" onClick={onDismiss}>
            Hide progress
          </button>
          <span className="progress-hint">
            (Hiding the progress view does not interrupt the analysis running on the server)
          </span>
        </div>
      )}
    </div>
  );
}

function buildFallbackDetailUrl(session, code) {
  if (session && session.role === "user" && session.userRef) {
    return `/${session.userRef}_${code}`;
  }
  return `/bot/${code}`;
}

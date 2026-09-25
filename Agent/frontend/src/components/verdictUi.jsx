import React from "react";

/**
 * One place for how a verdict LOOKS in admin lists: colour token + short label.
 *
 * The backend verdict strings ("DRAWDOWN: HIGH · QUALITY: WEAK", ...) are kept
 * verbatim everywhere they are data (filters, search, sorting, `title`). Only
 * the visible label is shortened: the full uppercase string repeated on every
 * row of a 166-bot table was the loudest thing on the page while saying the
 * same two words each time.
 */
export const VERDICT_COLOR_VAR = {
  "DRAWDOWN: HIGH · QUALITY: WEAK": "var(--verdict-high-dd-weak-q)",
  "DRAWDOWN: HIGH · QUALITY: GOOD": "var(--verdict-high-dd-good-q)",
  "DRAWDOWN: LOW · QUALITY: GOOD": "var(--verdict-low-dd-good-q)",
  "DRAWDOWN: LOW · QUALITY: WEAK": "var(--verdict-low-dd-weak-q)",
  "HIDDEN RISK": "var(--verdict-hidden-risk)",
  "INSUFFICIENT EVIDENCE": "var(--verdict-unknown)",
};

export const VERDICT_SHORT = {
  "DRAWDOWN: HIGH · QUALITY: WEAK": "High DD · Weak",
  "DRAWDOWN: HIGH · QUALITY: GOOD": "High DD · Good",
  "DRAWDOWN: LOW · QUALITY: GOOD": "Low DD · Good",
  "DRAWDOWN: LOW · QUALITY: WEAK": "Low DD · Weak",
  "HIDDEN RISK": "Hidden risk",
  "INSUFFICIENT EVIDENCE": "Insufficient evidence",
};

export function verdictShort(verdict) {
  const v = verdict || "INSUFFICIENT EVIDENCE";
  return VERDICT_SHORT[v] || v;
}

export function verdictColor(verdict) {
  return VERDICT_COLOR_VAR[verdict || "INSUFFICIENT EVIDENCE"] || "var(--verdict-unknown)";
}

/** Dot + short label; the full verdict string stays in the tooltip. */
export function VerdictDot({ verdict }) {
  const v = verdict || "INSUFFICIENT EVIDENCE";
  return (
    <span className="vdot" title={v}>
      <i style={{ background: verdictColor(v) }} />
      {verdictShort(v)}
    </span>
  );
}

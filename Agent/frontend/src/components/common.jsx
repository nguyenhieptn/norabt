import React from "react";

export function Loading({ text = "Loading…" }) {
  return <div className="msg">{text}</div>;
}

export function ErrorBox({ error, onRetry }) {
  return (
    <div className="msg err">
      {String(error?.message || error)}
      {onRetry && (
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

export function Empty({ text = "No data yet" }) {
  return <div className="msg">{text}</div>;
}

export function Card({ label, value, sub, tone, icon, glowColor }) {
  const cls =
    tone === "auto"
      ? Number(value) > 0
        ? "up"
        : Number(value) < 0
          ? "down"
          : ""
      : tone || "";
  return (
    <div className="card">
      {glowColor && <div className={`card-glow glow-${glowColor}`} />}
      <div className="card-top-row">
        <div className="lbl">{label}</div>
        {icon && <div className="card-icon-pill">{icon}</div>}
      </div>
      <div className={`val ${cls}`}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export function Cards({ children }) {
  return <div className="cards">{children}</div>;
}

export function Block({ title, note, actions, children, flush, className = "" }) {
  return (
    <div className={`block ${className}`}>
      {(title || note || actions) && (
        <div className="block-h">
          {title && <h2>{title}</h2>}
          {actions}
          {note && <span className="note">{note}</span>}
        </div>
      )}
      <div className={`block-b${flush ? " flush" : ""}`}>{children}</div>
    </div>
  );
}

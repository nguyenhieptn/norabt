import React from 'react'
import { money, pct, num } from '../lib/format'

export function Loading({ text = 'Đang tải…' }) {
  return <div className="msg">{text}</div>
}

export function ErrorBox({ error, onRetry }) {
  return (
    <div className="msg err">
      {String(error?.message || error)}
      {onRetry && (
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={onRetry}>Thử lại</button>
        </div>
      )}
    </div>
  )
}

export function Empty({ text = 'Chưa có dữ liệu' }) {
  return <div className="msg">{text}</div>
}

export function Card({ label, value, sub, tone }) {
  const cls = tone === 'auto'
    ? (Number(value) > 0 ? 'up' : Number(value) < 0 ? 'down' : '')
    : (tone || '')
  return (
    <div className="card">
      <div className="lbl">{label}</div>
      <div className={`val ${cls}`}>{typeof value === 'string' ? value : money(value)}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}

export function Block({ title, note, actions, children, flush }) {
  return (
    <div className="block">
      {(title || note || actions) && (
        <div className="block-h">
          {title && <h2>{title}</h2>}
          {actions}
          {note && <span className="note">{note}</span>}
        </div>
      )}
      <div className={`block-b${flush ? ' flush' : ''}`}>{children}</div>
    </div>
  )
}

/** Ô số có thanh mức độ nền — dài ngắn theo tỷ lệ so với giá trị lớn nhất */
export function BarCell({ value, max, positive = 'var(--up)', negative = 'var(--down)' }) {
  const v = Number(value || 0)
  const w = max ? Math.min(100, (Math.abs(v) / max) * 100) : 0
  return (
    <td className="n bar">
      <i style={{ width: `${w}%`, background: v >= 0 ? positive : negative }} />
      <span className={v > 0 ? 'up' : v < 0 ? 'down' : ''}>{money(v)}</span>
    </td>
  )
}

export function WinrateCell({ value }) {
  const v = Number(value || 0)
  return <td className="n">{pct(v)}</td>
}

/** Biểu đồ đường nhẹ, vẽ bằng SVG thuần — không cần thư viện */
export function Spark({ series, height = 190 }) {
  const all = series.flatMap((s) => s.data)
  if (!all.length) return <Empty />
  const min = Math.min(...all)
  const max = Math.max(...all)
  const range = max - min || 1
  const n = series[0].data.length
  const W = 1000
  const pad = 6
  const H = height - pad * 2
  const x = (i) => (i / Math.max(1, n - 1)) * W
  const y = (v) => pad + H - ((v - min) / range) * H

  return (
    <svg className="spark" viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none">
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1="0" x2={W} y1={pad + H * f} y2={pad + H * f}
          stroke="var(--line)" strokeWidth="1" />
      ))}
      {series.map((s, k) => (
        <polyline key={k} fill="none" stroke={s.color} strokeWidth="1.6"
          points={s.data.map((v, i) => `${x(i)},${y(v)}`).join(' ')} />
      ))}
    </svg>
  )
}

export function Legend({ items }) {
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 10, fontSize: 12.5 }}>
      {items.map((it) => (
        <span key={it.label} style={{ color: 'var(--ink-2)' }}>
          <i style={{
            display: 'inline-block', width: 11, height: 2, background: it.color,
            verticalAlign: 'middle', marginRight: 6,
          }} />
          {it.label}
          {it.value !== undefined && (
            <b style={{ marginLeft: 6, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
              {num(it.value)}
            </b>
          )}
        </span>
      ))}
    </div>
  )
}

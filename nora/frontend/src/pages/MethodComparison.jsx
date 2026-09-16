import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Empty, ErrorBox, Loading } from '../components/common'
import { int, num } from '../lib/format'

const TIMEFRAMES = [
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '24h', label: '24h' },
]

const toneStyle = {
  implemented: { color: 'var(--up)', borderColor: 'var(--up)' },
  pending: { color: 'var(--amber)', borderColor: 'var(--amber)' },
  neutral: { color: 'var(--ink-2)', borderColor: 'var(--line-2)' },
}

const metricLabels = {
  avg_dc_structure_score: 'Avg DC structure score',
  avg_event_rate_per_day: 'Avg event rate/day',
  avg_mu_os_dc: 'Avg mu_OS/DC',
  avg_cross_theta_stability: 'Avg cross-theta stability',
  n_assets: 'Assets',
}

const shellStyle = {
  maxWidth: 1380,
  margin: '0 auto',
  paddingBottom: 64,
}

const panelBase = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 22,
  boxShadow: '0 18px 50px rgba(0, 0, 0, .18)',
}

function Badge({ children, tone = 'neutral' }) {
  const style = toneStyle[tone] || toneStyle.neutral
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minHeight: 24,
      padding: '3px 9px', borderRadius: 999, border: `1px solid ${style.borderColor}`,
      color: style.color, background: 'var(--panel-2)', fontSize: 11, fontWeight: 800,
      lineHeight: 1, whiteSpace: 'nowrap', letterSpacing: '.02em',
    }}>
      {children}
    </span>
  )
}

function methodStatus(method) {
  return (method?.status === 'implemented' || method?.status === 'available')
    ? { label: 'Khả dụng', tone: 'implemented' }
    : { label: 'Chưa triển khai', tone: 'pending' }
}

function HeaderControls({ timeframe, onTimeframeChange, onRefresh, busy }) {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
      <select
        value={timeframe}
        onChange={(e) => onTimeframeChange(e.target.value)}
        style={{
          background: 'var(--panel-2)', color: 'var(--ink)', border: '1px solid var(--line)',
          borderRadius: 12, padding: '10px 12px', fontSize: 13, fontWeight: 800,
          outline: 'none', minWidth: 92,
        }}
      >
        {TIMEFRAMES.map((tf) => <option key={tf.value} value={tf.value}>{tf.label}</option>)}
      </select>
      <button className="btn" onClick={onRefresh} disabled={busy} style={{ borderRadius: 12, padding: '10px 14px' }}>
        {busy ? 'Đang cập nhật…' : 'Cập nhật'}
      </button>
    </div>
  )
}

function Panel({ title, eyebrow, note, children, style }) {
  return (
    <section style={{ ...panelBase, overflow: 'hidden', ...style }}>
      <div style={{ padding: '22px 24px 14px' }}>
        {eyebrow && <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.14em', textTransform: 'uppercase' }}>{eyebrow}</div>}
        <h2 style={{ margin: eyebrow ? '4px 0 0' : 0, fontSize: 22, lineHeight: 1.18, letterSpacing: '-.03em' }}>{title}</h2>
        {note && <div style={{ marginTop: 7, color: 'var(--ink-2)', fontSize: 13, lineHeight: 1.45 }}>{note}</div>}
      </div>
      <div style={{ padding: '0 24px 24px' }}>{children}</div>
    </section>
  )
}

function SummaryTile({ label, value, sub }) {
  return (
    <div style={{ padding: '14px 15px', borderRadius: 17, background: 'var(--panel-2)', border: '1px solid var(--line)' }}>
      <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '.1em' }}>{label}</div>
      <div style={{ marginTop: 6, color: 'var(--ink)', fontSize: 25, lineHeight: 1.05, fontWeight: 900, letterSpacing: '-.04em', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ marginTop: 5, color: 'var(--ink-3)', fontSize: 12, lineHeight: 1.35 }}>{sub}</div>}
    </div>
  )
}

function MetricRows({ metrics }) {
  return (
    <div style={{ display: 'grid', gap: 7 }}>
      {Object.entries(metricLabels).map(([key, label]) => {
        const missing = metrics?.[key] === null || metrics?.[key] === undefined
        return (
          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 14, color: missing ? 'var(--ink-3)' : 'var(--ink-2)', fontSize: 12.5 }}>
            <span>{label}</span>
            <b style={{ color: missing ? 'var(--ink-3)' : 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
              {key === 'n_assets' ? int(metrics?.[key]) : num(metrics?.[key])}
            </b>
          </div>
        )
      })}
    </div>
  )
}

function MethodCard({ method, index, best }) {
  const status = methodStatus(method)
  const score = method?.relative_strength
  const hasScore = score !== null && score !== undefined
  const width = hasScore ? Math.max(2, Math.min(100, Number(score))) : 0

  return (
    <div style={{
      padding: 17, borderRadius: 18, background: best ? 'var(--panel-3)' : 'var(--panel-2)',
      border: `1px solid ${best ? 'var(--info)' : 'var(--line)'}`, display: 'grid', gap: 13,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.12em', textTransform: 'uppercase' }}>
            Method {String(index + 1).padStart(2, '0')}
          </div>
          <h3 style={{ margin: '5px 0 0', fontSize: 18, lineHeight: 1.2, letterSpacing: '-.02em' }}>{method.title}</h3>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      {hasScore ? (
        <>
          <div style={{ height: 10, borderRadius: 999, background: 'var(--panel)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${width}%`, background: 'var(--info)', borderRadius: 999 }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', color: 'var(--ink-2)', fontSize: 12.5 }}>
            <span>Relative strength</span>
            <b style={{ color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>{num(score)} / 100</b>
          </div>
        </>
      ) : (
        <div style={{ color: 'var(--ink-2)', fontSize: 13, lineHeight: 1.5 }}>
          {method.note || 'Chưa có engine hoặc metric thật để so sánh.'}
        </div>
      )}

      <MetricRows metrics={method.metrics || {}} />
    </div>
  )
}

function renderMetricValue(key, value) {
  if (key === 'n_assets') return int(value)
  return num(value)
}

function EvidenceTable({ methods }) {
  if (!methods.length) return <Empty text="Chưa có dữ liệu chi tiết." />

  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Method</th>
            <th>Status</th>
            <th>Relative strength</th>
            <th>Metrics</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {methods.map((method) => {
            const status = methodStatus(method)
            const metrics = method.metrics || {}
            return (
              <tr key={method.id}>
                <td><b>{method.title}</b></td>
                <td><Badge tone={status.tone}>{status.label}</Badge></td>
                <td className="n">{method.relative_strength === null || method.relative_strength === undefined ? '—' : `${num(method.relative_strength)} / 100`}</td>
                <td>
                  <div style={{ display: 'grid', gap: 4, minWidth: 260 }}>
                    {Object.entries(metricLabels).map(([key, label]) => {
                      const missing = metrics[key] === null || metrics[key] === undefined
                      return (
                        <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, color: missing ? 'var(--ink-3)' : 'var(--ink-2)' }}>
                          <span>{label}</span>
                          <b style={{ color: missing ? 'var(--ink-3)' : 'var(--ink)' }}>{renderMetricValue(key, metrics[key])}</b>
                        </div>
                      )
                    })}
                  </div>
                </td>
                <td style={{ maxWidth: 360, color: 'var(--ink-2)', lineHeight: 1.45 }}>{method.note || '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function MethodComparison() {
  const navigate = useNavigate()
  const [timeframe, setTimeframe] = useState('1h')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [err, setErr] = useState(null)

  const loadData = async (tf = timeframe, force = false) => {
    try {
      if (force) setRefreshing(true)
      else setLoading(true)
      const res = await api.researchMethodsCompare(tf, force)
      setData(res)
      setErr(null)
    } catch (e) {
      setErr(e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadData(timeframe, false)
  }, [timeframe])

  const methods = data?.methods || []
  const implemented = methods.filter((method) => method.status === 'implemented')
  const pending = methods.length - implemented.length
  const bestMethod = useMemo(() => {
    return methods
      .filter((method) => method.relative_strength !== null && method.relative_strength !== undefined)
      .sort((a, b) => Number(b.relative_strength) - Number(a.relative_strength))[0]
  }, [methods])

  return (
    <div className="research-page" style={shellStyle}>
      <div style={{
        ...panelBase, padding: '24px 28px', marginBottom: 18,
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 18, flexWrap: 'wrap',
      }}>
        <div style={{ maxWidth: 820 }}>
          <button className="btn" onClick={() => navigate('/research/analysis')} style={{ marginBottom: 14, borderRadius: 12 }}>
            Quay lại overview
          </button>
          <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.16em', textTransform: 'uppercase' }}>
            Method Comparison
          </div>
          <h1 style={{ margin: '7px 0 0', fontSize: 'clamp(29px, 4vw, 43px)', lineHeight: 1.03, letterSpacing: '-.05em' }}>
            Analytical Methods
          </h1>
          <p style={{ color: 'var(--ink-2)', margin: '10px 0 0', fontSize: 14, maxWidth: 800, lineHeight: 1.55 }}>
            So sánh method bằng metric thật từ pipeline. Method chưa có engine được giữ ở trạng thái chưa triển khai, không vẽ điểm giả.
          </p>
        </div>
        <HeaderControls
          timeframe={timeframe}
          onTimeframeChange={setTimeframe}
          onRefresh={() => loadData(timeframe, true)}
          busy={refreshing || loading}
        />
      </div>

      {loading && !data ? (
        <Loading text="Đang tải so sánh phương pháp…" />
      ) : err ? (
        <ErrorBox error={err} onRetry={() => loadData(timeframe, false)} />
      ) : (
        <div style={{ display: 'grid', gap: 18 }}>
          <div style={{
            ...panelBase, padding: 18, display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))', gap: 10,
          }}>
            <SummaryTile label="Methods" value={int(methods.length)} sub="Tổng phương pháp" />
            <SummaryTile label="Implemented" value={int(implemented.length)} sub="Có metric thật" />
            <SummaryTile label="Pending" value={int(pending)} sub="Chưa có engine" />
            <SummaryTile label="Best method" value={bestMethod?.title || '—'} sub="Theo relative strength" />
          </div>

          <Panel title="Relative Strength" eyebrow="Ranking" note="Thanh điểm chỉ xuất hiện khi backend trả metric thật.">
            {!methods.length ? (
              <Empty text="Chưa có dữ liệu phương pháp." />
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 12 }}>
                {methods.map((method, idx) => (
                  <MethodCard key={method.id} method={method} index={idx} best={bestMethod?.id === method.id} />
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Method Evidence" eyebrow="Detailed analysis" note="Metric rỗng được giữ là —, không dùng fallback.">
            <EvidenceTable methods={methods} />
          </Panel>
        </div>
      )}
    </div>
  )
}

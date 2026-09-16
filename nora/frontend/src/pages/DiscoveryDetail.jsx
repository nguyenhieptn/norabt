import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
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
  high: { color: 'var(--info)', borderColor: 'var(--info)' },
  medium: { color: 'var(--amber)', borderColor: 'var(--amber)' },
  low: { color: 'var(--ink-3)', borderColor: 'var(--line-2)' },
  ok: { color: 'var(--up)', borderColor: 'var(--up)' },
  pending: { color: 'var(--amber)', borderColor: 'var(--amber)' },
  neutral: { color: 'var(--ink-2)', borderColor: 'var(--line-2)' },
}

const shellStyle = {
  maxWidth: 1480,
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

function severityTone(severity) {
  const s = String(severity || '').toLowerCase()
  if (s === 'high') return 'high'
  if (s === 'medium') return 'medium'
  return 'low'
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

function Panel({ title, eyebrow, note, actions, children, style }) {
  return (
    <section style={{ ...panelBase, overflow: 'hidden', ...style }}>
      <div style={{ padding: '22px 24px 14px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          {eyebrow && <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.14em', textTransform: 'uppercase' }}>{eyebrow}</div>}
          <h2 style={{ margin: eyebrow ? '4px 0 0' : 0, fontSize: 22, lineHeight: 1.18, letterSpacing: '-.03em' }}>{title}</h2>
          {note && <div style={{ marginTop: 7, color: 'var(--ink-2)', fontSize: 13, lineHeight: 1.45 }}>{note}</div>}
        </div>
        {actions && <div style={{ flex: '0 0 auto' }}>{actions}</div>}
      </div>
      <div style={{ padding: '0 24px 24px' }}>{children}</div>
    </section>
  )
}

function StatTile({ label, value, sub }) {
  return (
    <div style={{ padding: '15px 16px', borderRadius: 18, background: 'var(--panel-2)', border: '1px solid var(--line)' }}>
      <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '.1em' }}>{label}</div>
      <div style={{ marginTop: 7, color: 'var(--ink)', fontSize: 27, lineHeight: 1.05, fontWeight: 900, letterSpacing: '-.04em', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ marginTop: 5, color: 'var(--ink-3)', fontSize: 12, lineHeight: 1.35 }}>{sub}</div>}
    </div>
  )
}

function Histogram({ distribution }) {
  const bins = distribution?.bins || []
  const counts = distribution?.counts || []
  const safeCounts = counts.map((count) => Number(count) || 0)
  const maxCount = safeCounts.length ? Math.max(...safeCounts, 1) : 1

  if (!bins.length || !counts.length) {
    return <Empty text="Chưa đủ dữ liệu để dựng histogram." />
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ minWidth: Math.max(520, safeCounts.length * 58), display: 'grid', gridTemplateColumns: `repeat(${safeCounts.length}, minmax(46px, 1fr))`, gap: 8, alignItems: 'end', height: 230 }}>
        {safeCounts.map((count, idx) => {
          const barHeight = count > 0 ? Math.max(4, (count / maxCount) * 100) : 0
          return (
            <div key={`${idx}-${bins[idx]}`} style={{ display: 'grid', gap: 7, alignItems: 'end', height: '100%' }}>
              <div style={{ alignSelf: 'end', display: 'grid', alignItems: 'end', height: 154, background: 'var(--panel-2)', border: '1px solid var(--line)', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ height: `${barHeight}%`, background: 'var(--info)', borderRadius: '10px 10px 0 0' }} />
              </div>
              <div style={{ textAlign: 'center', fontSize: 12, fontWeight: 900, fontVariantNumeric: 'tabular-nums' }}>{int(count)}</div>
              <div style={{ textAlign: 'center', color: 'var(--ink-3)', fontSize: 10, lineHeight: 1.25, fontVariantNumeric: 'tabular-nums' }}>
                {num(bins[idx])}<br />{num(bins[idx + 1])}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function RobustnessMeter({ label, item }) {
  const hasScore = item?.score !== null && item?.score !== undefined && item?.status !== 'insufficient_data'
  const rawScore = hasScore ? Number(item.score) : null
  const width = hasScore ? Math.max(0, Math.min(100, rawScore)) : 0

  return (
    <div style={{ padding: 15, borderRadius: 16, background: 'var(--panel-2)', border: '1px solid var(--line)', display: 'grid', gap: 11 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
        <b style={{ fontSize: 14 }}>{label}</b>
        {hasScore ? <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 900 }}>{num(rawScore)} / 100</span> : <Badge tone="pending">Chưa đủ dữ liệu</Badge>}
      </div>
      {hasScore ? (
        <div style={{ height: 10, borderRadius: 999, background: 'var(--panel-3)', overflow: 'hidden' }}>
          <div style={{ width: `${width}%`, height: '100%', background: 'var(--info)', borderRadius: 999 }} />
        </div>
      ) : null}
      <div style={{ color: 'var(--ink-3)', fontSize: 12, lineHeight: 1.45 }}>{item?.basis || item?.status || '—'}</div>
    </div>
  )
}

function Robustness({ robustness }) {
  const items = [
    ['Threshold sensitivity', robustness?.threshold_sensitivity],
    ['Time-period stability', robustness?.time_period_stability],
    ['Cross-market stability', robustness?.cross_market_stability],
  ]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
      {items.map(([label, item]) => <RobustnessMeter key={label} label={label} item={item} />)}
    </div>
  )
}

function CrossAssetTable({ rows }) {
  const maxValue = rows.length ? Math.max(...rows.map((row) => Math.abs(Number(row.value) || 0)), 1) : 1

  if (!rows.length) return <Empty text="Chưa có breakdown theo tài sản." />

  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Asset</th>
            <th>Value</th>
            <th>Position</th>
            <th>Delta from mean</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const value = Number(row.value) || 0
            const delta = Number(row.delta_from_mean || 0)
            return (
              <tr key={row.symbol}>
                <td><b>{row.symbol}</b></td>
                <td className="n">{num(row.value)}</td>
                <td style={{ minWidth: 180 }}>
                  <div style={{ height: 9, borderRadius: 999, background: 'var(--panel-3)', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(100, (Math.abs(value) / maxValue) * 100)}%`, height: '100%', background: 'var(--info)', borderRadius: 999 }} />
                  </div>
                </td>
                <td className="n" style={{ color: delta > 0 ? 'var(--up)' : delta < 0 ? 'var(--down)' : 'var(--ink-3)' }}>
                  {num(row.delta_from_mean)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CrossDexTable({ rows }) {
  if (!rows.length) return <Empty text="Chưa có breakdown theo DEX/network." />

  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Network</th>
            <th>DEX name</th>
            <th>Assets</th>
            <th>Mean</th>
            <th>Std</th>
            <th>Sample status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.network || 'unknown'}-${idx}`}>
              <td><b>{row.network || 'unknown'}</b></td>
              <td>{row.dex_name || '—'}</td>
              <td className="n">{int(row.n_assets)}</td>
              <td className="n">{num(row.mean)}</td>
              <td className="n">{num(row.std)}</td>
              <td>{row.insufficient_sample ? <Badge tone="pending">Mẫu chưa đủ</Badge> : <Badge tone="ok">Đủ mẫu</Badge>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DiscoveryDetail() {
  const { discoveryId } = useParams()
  const navigate = useNavigate()
  const [timeframe, setTimeframe] = useState('1h')
  const [discovery, setDiscovery] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [err, setErr] = useState(null)

  const loadData = async (tf = timeframe, force = false) => {
    try {
      if (force) setRefreshing(true)
      else setLoading(true)
      const res = await api.researchDiscoveryDetail(discoveryId, tf, force)
      setDiscovery(res)
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
  }, [discoveryId, timeframe])

  const stats = discovery?.global_stats || {}
  const crossAsset = discovery?.cross_asset || []
  const crossDex = discovery?.cross_dex || []

  return (
    <div className="research-page" style={shellStyle}>
      <div style={{
        ...panelBase, padding: '24px 28px', marginBottom: 18,
        display: 'grid', gap: 18,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 18, flexWrap: 'wrap' }}>
          <div style={{ maxWidth: 900 }}>
            <button className="btn" onClick={() => navigate('/research/analysis')} style={{ marginBottom: 14, borderRadius: 12 }}>
              Quay lại overview
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.16em', textTransform: 'uppercase' }}>
                Discovery Evidence
              </div>
              {discovery && <Badge tone={severityTone(discovery.severity)}>{discovery.severity || 'LOW'}</Badge>}
            </div>
            <h1 style={{ margin: '7px 0 0', fontSize: 'clamp(29px, 4vw, 43px)', lineHeight: 1.03, letterSpacing: '-.05em' }}>
              {discovery?.title || 'Discovery Detail'}
            </h1>
            <p style={{ color: 'var(--ink-2)', margin: '10px 0 0', fontSize: 14, maxWidth: 820, lineHeight: 1.55 }}>
              {discovery?.headline_stat || 'Đang tải bằng chứng Discovery.'}
            </p>
          </div>
          <HeaderControls
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            onRefresh={() => loadData(timeframe, true)}
            busy={refreshing || loading}
          />
        </div>
        <div style={{ padding: '16px 18px', borderRadius: 18, background: 'var(--panel-2)', border: '1px solid var(--line)' }}>
          <div style={{ color: 'var(--ink-3)', fontSize: 11, fontWeight: 900, letterSpacing: '.12em', textTransform: 'uppercase' }}>Hypothesis</div>
          <div style={{ marginTop: 7, color: 'var(--ink)', fontSize: 16, lineHeight: 1.6 }}>
            {discovery?.hypothesis || '—'}
          </div>
        </div>
      </div>

      {loading && !discovery ? (
        <Loading text="Đang tải chi tiết Discovery…" />
      ) : err ? (
        <ErrorBox error={err} onRetry={() => loadData(timeframe, false)} />
      ) : (
        <div style={{ display: 'grid', gap: 18 }}>
          <div style={{
            ...panelBase, padding: 18, display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))', gap: 10,
          }}>
            <StatTile label="Mean" value={num(stats.mean)} sub={discovery?.unit || undefined} />
            <StatTile label="Median" value={num(stats.median)} sub={discovery?.unit || undefined} />
            <StatTile label="Std" value={num(stats.std)} sub="Độ phân tán" />
            <StatTile label="Assets" value={int(stats.n_assets)} sub="Có dữ liệu hợp lệ" />
            <StatTile label="DEX / network" value={int(stats.n_dexes)} sub="Theo registry crawler" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 18, alignItems: 'start' }}>
            <Panel title="Distribution" eyebrow="Evidence" note="Histogram từ field thật của Discovery.">
              <Histogram distribution={discovery?.distribution} />
            </Panel>

            <Panel title="Robustness" eyebrow="Stability" note="Không có dữ liệu thì hiển thị trạng thái, không vẽ thanh 0%.">
              <Robustness robustness={discovery?.robustness || {}} />
            </Panel>
          </div>

          <Panel title="Cross-Asset" eyebrow="Breakdown" note="Asset là một dimension để phân tích finding, không phải navigation chính.">
            <CrossAssetTable rows={crossAsset} />
          </Panel>

          <Panel title="Cross-DEX" eyebrow="Breakdown" note="Nhóm chính là network; DEX name chỉ hiển thị khi registry có dữ liệu.">
            <CrossDexTable rows={crossDex} />
          </Panel>
        </div>
      )}
    </div>
  )
}

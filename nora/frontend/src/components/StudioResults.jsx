import { useState } from 'react'

const formatMoney = (value) => {
  const n = Number(value || 0)
  return `${n >= 0 ? '+' : '-'}$${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

const formatPct = (value) => {
  const n = Number(value || 0)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

const alphaGrade = (metrics) => {
  const trades = Number(metrics.total_trades || 0)
  const winRate = Number(metrics.win_rate ?? metrics.winrate ?? 0)
  const profitFactor = Number(metrics.profit_factor || 0)
  const drawdown = Number(metrics.max_drawdown_pct || 0)
  const returnPct = Number(metrics.return_pct ?? metrics.total_pnl_pct ?? 0)
  const checks = [
    { label: 'Sample size ≥ 30 trades', ok: trades >= 30, value: `${trades} trades` },
    { label: 'Profit factor ≥ 1.5', ok: profitFactor >= 1.5, value: profitFactor.toFixed(2) },
    { label: 'Win rate ≥ 55%', ok: winRate >= 55, value: `${winRate.toFixed(2)}%` },
    { label: 'Max drawdown ≤ 15%', ok: drawdown <= 15, value: `${drawdown.toFixed(2)}%` },
    { label: 'Closed-trade return > 0%', ok: returnPct > 0, value: `${returnPct.toFixed(2)}%` },
  ]
  const passed = checks.filter((check) => check.ok).length
  const label = passed >= 4 ? 'Strong candidate' : passed >= 3 ? 'Watchlist' : 'Research only'
  return { checks, passed, label }
}

export default function StudioResults({ results, loading, error, onSendToBase }) {
  const [filterType, setFilterType] = useState('ALL')
  const [hoverPoint, setHoverPoint] = useState(null)

  if (loading) {
    return (
      <div className="studio-empty-state">
        <div className="studio-spinner"></div>
        <p style={{ marginTop: 14, color: 'var(--amber)', fontWeight: 600 }}>
          Đang chạy mô phỏng AST qua BacktestEngine...
        </p>
        <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
          Dùng nến 1m để khớp lệnh và nến 4h làm bối cảnh chỉ báo.
        </span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="studio-error-box">
        <div className="studio-error-title">Lỗi validate hoặc mô phỏng</div>
        <pre className="studio-error-content">{String(error.detail || error.message || error)}</pre>
      </div>
    )
  }

  if (!results) {
    return (
      <div className="studio-empty-state">
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-2)' }}>Chưa có kết quả mô phỏng</p>
        <p style={{ fontSize: 12.5, color: 'var(--ink-3)', maxWidth: 380, margin: '6px auto 14px' }}>
          Chọn sample hoặc dựng flow AST, sau đó nhấn <b style={{ color: 'var(--amber)' }}>Simulate</b> để chạy qua NoraBT canonical engine.
        </p>
      </div>
    )
  }

  const metrics = results.metrics || {}
  const trades = results.trades || []
  const points = results.equity_curve || []
  const returnPct = Number(metrics.return_pct ?? metrics.total_pnl_pct ?? 0)
  const isProfit = returnPct >= 0
  const grade = alphaGrade(metrics)

  const filteredTrades = trades.filter((trade) => {
    const pnlPct = Number(trade.pnl_pct || 0)
    if (filterType === 'WIN') return pnlPct > 0
    if (filterType === 'LOSS') return pnlPct <= 0
    if (filterType === 'LONG') return trade.pos_type === 'LONG'
    if (filterType === 'SHORT') return trade.pos_type === 'SHORT'
    return true
  })

  let svgPath = ''
  let areaPath = ''
  let minEquity = 0
  let maxEquity = 1
  const width = 600
  const height = 180
  const padTop = 15
  const padBottom = 25
  const padLeft = 10
  const padRight = 10

  if (points.length > 1) {
    const equities = points.map((point) => Number(point.equity || 0))
    minEquity = Math.min(...equities) * 0.99
    maxEquity = Math.max(...equities) * 1.01
    if (maxEquity === minEquity) maxEquity = minEquity + 100

    const scaleX = (i) => padLeft + (i / (points.length - 1)) * (width - padLeft - padRight)
    const scaleY = (val) => padTop + (1 - (val - minEquity) / (maxEquity - minEquity)) * (height - padTop - padBottom)
    const coords = equities.map((equity, i) => [scaleX(i), scaleY(equity)])
    svgPath = coords.map((coord, i) => `${i === 0 ? 'M' : 'L'} ${coord[0].toFixed(1)} ${coord[1].toFixed(1)}`).join(' ')
    const zeroY = height - padBottom
    areaPath = `${svgPath} L ${coords[coords.length - 1][0].toFixed(1)} ${zeroY} L ${coords[0][0].toFixed(1)} ${zeroY} Z`
  }

  return (
    <div className="studio-results-container">
      <div className="studio-results-header">
        <div>
          <span className="tag run" style={{ marginRight: 8 }}>
            {results.symbol} · {results.timeframe || '1m/4h'}
          </span>
          <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
            {(results.data?.candles_1m || 0).toLocaleString()} nến 1m · {(results.data?.candles_4h || 0).toLocaleString()} nến 4h · {results.execution_time_ms}ms
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>PnL closed trades:</span>{' '}
            <span
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: isProfit ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)',
              }}
            >
              {formatMoney(metrics.estimated_pnl_usd)} ({formatPct(returnPct)})
            </span>
          </div>
          {onSendToBase && (
            <button
              className="studio-handoff-btn"
              onClick={() => onSendToBase(results)}
              title="Chuyển cấu hình chiến lược sang Base để chạy Backtest"
            >
              <span>Chạy Backtest (Base)</span>
              <span style={{ fontWeight: 'bold' }}>➔</span>
            </button>
          )}
        </div>
      </div>

      <div className="studio-results-note">
        Equity curve là cumulative closed-trade curve, không phải tick-by-tick equity. Sharpe/Sortino chưa được backend canonical tính nên không hiển thị như metric thật.
      </div>

      <div className="studio-alpha-grade-card">
        <div className="studio-alpha-grade-head">
          <span>Alpha Quality Gate</span>
          <b>{grade.label} · {grade.passed}/5</b>
        </div>
        <div className="studio-alpha-checks">
          {grade.checks.map((check) => (
            <div key={check.label} className={`studio-alpha-check ${check.ok ? 'ok' : 'warn'}`}>
              <span>{check.ok ? '✓' : '!'}</span>
              <b>{check.label}</b>
              <em>{check.value}</em>
            </div>
          ))}
        </div>
      </div>

      <div className="studio-chart-wrapper">
        <div className="studio-chart-title">
          <span>Cumulative closed-trade curve</span>
          {hoverPoint && (
            <span style={{ color: 'var(--amber)', fontSize: 11.5 }}>
              Equity: ${Number(hoverPoint.equity || 0).toLocaleString()} · Drawdown: {Number(hoverPoint.drawdown_pct || 0).toFixed(2)}%
            </span>
          )}
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} className="studio-equity-svg" onMouseLeave={() => setHoverPoint(null)}>
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isProfit ? '#10b981' : '#ef4444'} stopOpacity="0.35" />
              <stop offset="100%" stopColor={isProfit ? '#10b981' : '#ef4444'} stopOpacity="0" />
            </linearGradient>
          </defs>
          <line x1={padLeft} y1={padTop} x2={width - padRight} y2={padTop} stroke="var(--line-2)" strokeDasharray="3 3" />
          <line x1={padLeft} y1={(padTop + height - padBottom) / 2} x2={width - padRight} y2={(padTop + height - padBottom) / 2} stroke="var(--line-2)" strokeDasharray="3 3" />
          <line x1={padLeft} y1={height - padBottom} x2={width - padRight} y2={height - padBottom} stroke="var(--line-2)" />
          {areaPath && <path d={areaPath} fill="url(#equityGrad)" />}
          {svgPath && <path d={svgPath} fill="none" stroke={isProfit ? '#10b981' : '#ef4444'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
          {points.map((point, i) => {
            const barW = width / points.length
            return <rect key={i} x={i * barW} y={0} width={barW} height={height} fill="transparent" onMouseEnter={() => setHoverPoint(point)} />
          })}
        </svg>
      </div>

      <div className="studio-metrics-grid">
        <div className="studio-metric-card">
          <div className="studio-metric-label">Return</div>
          <div className="studio-metric-value" style={{ color: isProfit ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)' }}>
            {formatPct(returnPct)}
          </div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Estimated PnL</div>
          <div className="studio-metric-value" style={{ color: isProfit ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)' }}>
            {formatMoney(metrics.estimated_pnl_usd)}
          </div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Max Drawdown</div>
          <div className="studio-metric-value" style={{ color: 'var(--down, #ef4444)' }}>
            -{Number(metrics.max_drawdown_pct || 0).toFixed(2)}%
          </div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Win Rate</div>
          <div className="studio-metric-value">{Number(metrics.win_rate || 0).toFixed(2)}%</div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Profit Factor</div>
          <div className="studio-metric-value">{Number(metrics.profit_factor || 0).toFixed(2)}</div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Gross Profit</div>
          <div className="studio-metric-value">{formatPct(metrics.gross_profit)}</div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Gross Loss</div>
          <div className="studio-metric-value">{formatPct(metrics.gross_loss)}</div>
        </div>
        <div className="studio-metric-card">
          <div className="studio-metric-label">Trades</div>
          <div className="studio-metric-value">
            {metrics.total_trades || 0}{' '}
            <span style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 'normal' }}>
              ({metrics.winning_trades || 0}W / {metrics.losing_trades || 0}L)
            </span>
          </div>
        </div>
      </div>

      <div className="studio-trades-section">
        <div className="studio-trades-header">
          <span style={{ fontWeight: 600, fontSize: 13 }}>Nhật ký vị thế ({filteredTrades.length})</span>
          <div className="studio-filter-pills">
            {['ALL', 'WIN', 'LOSS', 'LONG', 'SHORT'].map((type) => (
              <button key={type} className={`studio-pill ${filterType === type ? 'active' : ''}`} onClick={() => setFilterType(type)}>
                {type === 'ALL' ? 'Tất cả' : type === 'WIN' ? 'Thắng' : type === 'LOSS' ? 'Thua' : type}
              </button>
            ))}
          </div>
        </div>

        {filteredTrades.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-3)', fontSize: 12.5 }}>
            Không có vị thế nào trong bộ lọc này.
          </div>
        ) : (
          <div className="studio-table-scroll">
            <table className="studio-trades-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Flow</th>
                  <th>Loại</th>
                  <th>Vào lệnh</th>
                  <th className="n">Giá vào</th>
                  <th>Đóng lệnh</th>
                  <th className="n">Giá đóng</th>
                  <th className="n">PnL ước tính</th>
                  <th className="n">PnL %</th>
                  <th>Trạng thái</th>
                  <th>Lý do</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrades.map((trade, index) => {
                  const pnlPct = Number(trade.pnl_pct || 0)
                  const win = pnlPct > 0
                  return (
                    <tr key={`${trade.trade_id}-${index}`}>
                      <td className="mono">{trade.index || index + 1}</td>
                      <td style={{ fontSize: 11.5, color: 'var(--ink-2)' }}>{trade.flow}</td>
                      <td>
                        <span className={`tag ${trade.pos_type === 'LONG' ? 'run' : 'stop'}`}>{trade.pos_type}</span>
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--ink-2)' }}>{trade.entry_date}</td>
                      <td className="n mono">{trade.entry_price}</td>
                      <td style={{ fontSize: 11, color: 'var(--ink-2)' }}>{trade.close_date}</td>
                      <td className="n mono">{trade.close_price ?? 'N/A'}</td>
                      <td className="n mono" style={{ fontWeight: 600, color: win ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)' }}>
                        {formatMoney(trade.estimated_pnl_usd)}
                      </td>
                      <td className="n mono" style={{ color: win ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)' }}>
                        {formatPct(pnlPct)}
                      </td>
                      <td style={{ fontSize: 11.5, color: 'var(--ink-2)' }}>{trade.status}</td>
                      <td style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{trade.reason}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Block, Card } from '../components/common'
import { int, pct } from '../lib/format'

export default function Scan() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [err, setErr] = useState(null)
  const [timeframe, setTimeframe] = useState('1h')
  const [filterClass, setFilterClass] = useState('ALL')
  const [search, setSearch] = useState('')
  const [selectedAsset, setSelectedAsset] = useState(null)

  const loadScan = async (tf = timeframe, force = false) => {
    try {
      setLoading(true)
      const res = force ? await api.researchScanRun(tf) : await api.researchScanLatest(tf)
      setData(res)
      setErr(null)
    } catch (e) {
      setErr(e.message || 'Lỗi khi tải kết quả scan')
    } finally {
      setLoading(false)
      setScanning(false)
    }
  }

  useEffect(() => {
    loadScan(timeframe, false)
  }, [timeframe])

  const handleRunBatch = () => {
    setScanning(true)
    loadScan(timeframe, true)
  }

  if (err && !data) return <ErrorBox error={err} />

  const summary = data?.summary || {}
  const rawLeaderboard = data?.asset_leaderboard || []
  const strategyLeaderboard = data?.strategy_leaderboard || []

  const filteredAssets = rawLeaderboard.filter((a) => {
    if (filterClass !== 'ALL' && a.classification !== filterClass) return false
    if (search && !a.symbol.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="research-page">
      <div className="head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>🛰️</span>
            <h1>Scan · Bàn Điều Khiển Batch Research</h1>
          </div>
          <p style={{ color: 'var(--muted)', marginTop: 4 }}>
            Quét và kiểm định hàng loạt toàn bộ danh mục tài sản DEX qua cùng một Cost Model chuẩn hóa.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            style={{
              background: 'var(--bg2)',
              color: 'var(--fg)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '8px 12px',
              fontWeight: 600,
            }}
          >
            <option value="15m">Khung 15m</option>
            <option value="1h">Khung 1h</option>
            <option value="4h">Khung 4h</option>
            <option value="24h">Khung 24h</option>
          </select>

          <button
            onClick={handleRunBatch}
            disabled={scanning || loading}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              boxShadow: '0 4px 12px rgba(37,99,235,0.3)',
            }}
          >
            {scanning ? '⏳ Đang quét batch…' : '⚡ Chạy Batch Scan Mới'}
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 24 }}>
        <Card
          label="Tài sản quét"
          value={int(summary.total_assets || 0)}
          sub={`${int(summary.pass_count || 0)} pass / ${int(summary.fail_count || 0)} fail`}
        />
        <Card
          label="Tỷ lệ Pass"
          value={pct(summary.pass_rate_pct || 0)}
          sub="Đạt chuẩn trade tốt"
          style={{ borderLeft: '4px solid #10b981' }}
        />
        <Card
          label="Median Sharpe"
          value={summary.median_sharpe !== undefined ? Number(summary.median_sharpe).toFixed(2) : '--'}
          sub="Trung vị toàn danh mục"
        />
        <Card
          label="Median Max DD"
          value={pct(summary.median_mdd_pct || 0)}
          sub="Độ sụt giảm trung vị"
        />
        <Card
          label="Median OOS Decay"
          value={pct(summary.median_oos_degradation_pct || 0)}
          sub="Suy thoái Out-of-sample"
        />
      </div>

      {/* Main Asset Leaderboard */}
      <Block
        title="Asset Leaderboard · Xếp hạng chất lượng thị trường"
        note={`${filteredAssets.length}/${rawLeaderboard.length} tài sản DEX`}
      >
        {/* Filter Toolbar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 16,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'Tất cả' },
              { id: 'CAN_TRADE', label: '✅ Trade tốt' },
              { id: 'NARROW_CONDITIONS', label: '⚠️ Điều kiện hẹp' },
              { id: 'DO_NOT_TRADE', label: '❌ Không trade' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterClass(f.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 20,
                  fontSize: 13,
                  fontWeight: 600,
                  border: '1px solid var(--border)',
                  background: filterClass === f.id ? 'var(--fg)' : 'var(--bg2)',
                  color: filterClass === f.id ? 'var(--bg)' : 'var(--fg)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          <input
            type="text"
            placeholder="Tìm theo symbol (SOL, BTC, WIF...)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--bg2)',
              color: 'var(--fg)',
              minWidth: 240,
            }}
          />
        </div>

        {loading && !scanning ? (
          <Loading text="Đang tải bảng xếp hạng…" />
        ) : (
          <div className="tblwrap">
            <table className="scan-table">
              <thead>
                <tr>
                  <th style={{ width: 45 }}>#</th>
                  <th>Tài sản</th>
                  <th>Phân loại & Điểm</th>
                  <th>Regime</th>
                  <th className="n">Sharpe</th>
                  <th className="n">Max DD</th>
                  <th className="n">Winrate</th>
                  <th>Reason Tags</th>
                  <th>Chiến lược phù hợp</th>
                  <th style={{ textAlign: 'center' }}>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.map((row) => (
                  <tr
                    key={row.symbol}
                    onClick={() => setSelectedAsset(row)}
                    style={{
                      cursor: 'pointer',
                      background: selectedAsset?.symbol === row.symbol ? 'rgba(59,130,246,0.08)' : 'transparent',
                    }}
                  >
                    <td style={{ fontWeight: 700, color: 'var(--muted)' }}>{row.rank}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 800, fontSize: 15 }}>{row.symbol}</span>
                        <span style={{ fontSize: 11, padding: '2px 6px', background: 'var(--bg2)', borderRadius: 4, color: 'var(--muted)' }}>DEX</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span
                          className={`badge badge-${row.tradeability_badge}`}
                          style={{
                            padding: '3px 8px',
                            borderRadius: 6,
                            fontSize: 12,
                            fontWeight: 700,
                          }}
                        >
                          {row.tradeability_title}
                        </span>
                        <span style={{ fontWeight: 800, color: 'var(--fg)', fontSize: 13 }}>
                          {row.tradeability_score.toFixed(0)} <span style={{ fontSize: 10, color: 'var(--muted)' }}>/ 100</span>
                        </span>
                      </div>
                    </td>
                    <td>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600,
                          background: `${row.regime_color}18`,
                          color: row.regime_color,
                          border: `1px solid ${row.regime_color}40`,
                        }}
                      >
                        {row.regime_name}
                      </span>
                    </td>
                    <td className="n" style={{ fontWeight: 700, color: row.sharpe >= 1.5 ? '#10b981' : (row.sharpe > 0 ? 'var(--fg)' : '#ef4444') }}>
                      {row.sharpe.toFixed(2)}
                    </td>
                    <td className="n" style={{ color: row.mdd_pct > 25 ? '#ef4444' : 'var(--fg)' }}>
                      -{row.mdd_pct.toFixed(1)}%
                    </td>
                    <td className="n">{row.winrate_pct.toFixed(1)}%</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {(row.reason_tags || []).map((t, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: 11,
                              padding: '1px 6px',
                              borderRadius: 4,
                              background: t.type === 'danger' ? 'rgba(239,68,68,0.15)' : (t.type === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(59,130,246,0.15)'),
                              color: t.type === 'danger' ? '#ef4444' : (t.type === 'warning' ? '#f59e0b' : '#3b82f6'),
                            }}
                          >
                            {t.label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--fg)', maxWidth: 180, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {row.best_strategy}
                    </td>
                    <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => navigate(`/research/analysis?symbol=${row.symbol}`)}
                        className="btn btn-secondary"
                        style={{
                          fontSize: 12,
                          padding: '4px 10px',
                          borderRadius: 6,
                          fontWeight: 600,
                          background: 'var(--bg2)',
                        }}
                      >
                        Phân Tích ➔
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Block>

      {/* Strategy Leaderboard */}
      <Block title="Strategy Leaderboard · Chiến lược theo độ phủ thị trường" note="Dựa trên kiểm định toàn danh mục DEX">
        <div className="tblwrap">
          <table>
            <thead>
              <tr>
                <th>Chiến lược</th>
                <th>Phân loại</th>
                <th className="n">Tài sản phù hợp</th>
                <th className="n">Avg Sharpe</th>
                <th className="n">Avg Winrate</th>
                <th>Trạng thái độ bền (Robustness)</th>
              </tr>
            </thead>
            <tbody>
              {strategyLeaderboard.map((s, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 700 }}>{s.strategy_name}</td>
                  <td style={{ color: 'var(--muted)', fontSize: 13 }}>{s.type}</td>
                  <td className="n" style={{ fontWeight: 700 }}>{s.suitable_assets_count} assets</td>
                  <td className="n" style={{ fontWeight: 700, color: s.avg_sharpe >= 1.2 ? '#10b981' : 'var(--fg)' }}>
                    {s.avg_sharpe.toFixed(2)}
                  </td>
                  <td className="n">{s.avg_winrate.toFixed(1)}%</td>
                  <td>
                    <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, background: 'rgba(16,185,129,0.1)', color: '#10b981', fontWeight: 600 }}>
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Block>

      {/* Drill-down Drawer for selected asset */}
      {selectedAsset && (
        <div
          style={{
            marginTop: 20,
            padding: 20,
            borderRadius: 12,
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 20 }}>🔍</span>
              <h3 style={{ margin: 0 }}>Drill-down: {selectedAsset.symbol} (Score: {selectedAsset.tradeability_score.toFixed(0)}/100)</h3>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => navigate(`/research/analysis?symbol=${selectedAsset.symbol}`)}
                className="btn btn-primary"
                style={{ fontSize: 13, padding: '6px 14px' }}
              >
                Mở Báo Cáo Phân Tích Đầy Đủ ➔
              </button>
              <button
                onClick={() => setSelectedAsset(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 18 }}
              >
                ✕
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            <div style={{ padding: 14, background: 'var(--bg)', borderRadius: 8, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>KHUYẾN NGHỊ THAO TÁC</div>
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--fg)', lineHeight: 1.5 }}>
                {selectedAsset.headline_insight}
              </div>
            </div>

            <div style={{ padding: 14, background: 'var(--bg)', borderRadius: 8, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>CHIẾN LƯỢC TỐI ƯU</div>
              <div style={{ fontWeight: 700, color: '#3b82f6', fontSize: 15 }}>
                {selectedAsset.best_strategy}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                Khung đề xuất: <b>{selectedAsset.recommended_timeframe}</b> · OOS Decay: <b>{selectedAsset.oos_degradation_pct}%</b>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

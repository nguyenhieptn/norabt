import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Block, Card } from '../components/common'
import { int, money, pct } from '../lib/format'

export default function Dashboard() {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => { api.dashboard().then(setD).catch(setErr) }, [])

  if (err) return <ErrorBox error={err} />
  if (!d) return <Loading text="Đang tổng hợp…" />

  const maxG = Math.max(...d.groups.map((g) => g.n), 1)

  return (
    <>
      <div className="head">
        <h1>Tổng quan</h1>
        <p>Toàn cảnh kho chiến lược và các lần chạy backtest.</p>
      </div>

      <div className="cards">
        <Card label="Lần chạy" value={int(d.runs)} sub={`${int(d.runs_co_ket_qua)} đã có kết quả`} />
        <Card label="Chiến lược" value={int(d.strategies)} sub={`${int(d.containers)} bộ chứa`} />
        <Card label="Phiên đào" value={int(d.optimizations)} sub="tìm tham số tối ưu" />
        <Card label="Nhóm chiến lược" value={int(d.groups.length)} sub="theo phân loại" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 20 }}>
        <Block title="Kho chiến lược theo nhóm">
          {d.groups.map((g) => (
            <div key={g.ten} style={{ marginBottom: 9 }}>
              <div style={{ display: 'flex', fontSize: 13.5, marginBottom: 3 }}>
                <span>{g.ten}</span>
                <b style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums' }}>{int(g.n)}</b>
              </div>
              <div style={{ height: 5, background: 'var(--panel-3)' }}>
                <div style={{
                  height: '100%', width: `${(g.n / maxG) * 100}%`,
                  background: 'var(--amber)', opacity: .75,
                }} />
              </div>
            </div>
          ))}
        </Block>

        <Block title="Lần chạy gần đây" flush>
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Mã</th><th>Tên</th><th className="n">Lệnh</th><th className="n">Lãi lỗ</th><th className="n">Thắng</th></tr>
              </thead>
              <tbody>
                {d.recent_runs.map((r) => (
                  <tr key={r.run_id}>
                    <td className="mono">
                      <Link to={`/library/result/${r.run_id}`} style={{ color: 'var(--amber)' }}>
                        {r.run_id}
                      </Link>
                    </td>
                    <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <Link to={`/library/result/${r.run_id}`}>{r.name || '—'}</Link>
                    </td>
                    <td className="n">{r.trades ? int(r.trades) : '—'}</td>
                    <td className={`n ${Number(r.pnl) > 0 ? 'up' : Number(r.pnl) < 0 ? 'down' : ''}`}>
                      {r.pnl !== null && r.pnl !== undefined ? money(r.pnl) : '—'}
                    </td>
                    <td className="n">{r.winrate !== null && r.winrate !== undefined ? pct(r.winrate) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Block>
      </div>

      <Block title="Luồng làm việc">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 14 }}>
          {[
            { to: '/miner', n: '1', t: 'Đào chiến lược', d: 'Quét dải tham số, sinh hàng loạt biến thể rồi chấm điểm.' },
            { to: '/library/alpha', n: '2', t: 'Thư viện Alpha', d: 'Chiến lược đã có, phân theo bốn loại logic.' },
            { to: '/library/base', n: '3', t: 'Cấu hình chạy', d: 'Gắn coin, vốn, khoảng thời gian cho một lần chạy.' },
            { to: '/library/result', n: '4', t: 'Kết quả', d: 'Chỉ số đầy đủ, biểu đồ và đánh giá từng lần chạy.' },
          ].map((s) => (
            <Link key={s.to} to={s.to} style={{
              border: '1px solid var(--line)', background: 'var(--panel-2)',
              padding: '14px 16px', display: 'block',
            }}>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.1em',
                color: 'var(--ink-3)', marginBottom: 6,
              }}>BƯỚC {s.n}</div>
              <b style={{ fontSize: 15 }}>{s.t}</b>
              <p style={{ margin: '5px 0 0', fontSize: 13, color: 'var(--ink-2)' }}>{s.d}</p>
            </Link>
          ))}
        </div>
      </Block>
    </>
  )
}

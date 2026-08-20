import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Empty, Block } from '../components/common'
import { money, pct, int, dur, dt, num } from '../lib/format'

export default function Trades() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [page, setPage] = useState(1)
  const [symbol, setSymbol] = useState('')
  const [flow, setFlow] = useState('')
  const [only, setOnly] = useState('')
  const [symbols, setSymbols] = useState([])
  const [flows, setFlows] = useState([])
  const size = 20

  useEffect(() => {
    api.chartOptions(id).then((r) => setSymbols(r.symbols)).catch(() => {})
    api.byFlow(id).then((r) => setFlows(r.rows)).catch(() => {})
  }, [id])

  useEffect(() => {
    setData(null); setErr(null)
    api.trades(id, { page, size, symbol, flow, only })
      .then(setData).catch(setErr)
  }, [id, page, symbol, flow, only])

  const pages = data ? Math.max(1, Math.ceil(data.total / size)) : 1

  return (
    <>
      <p className="crumb">
        <Link to="/library/result">Các lần chạy</Link> · <Link to={`/library/result/${id}`}>mã {id}</Link> · danh sách lệnh
      </p>
      <div className="head">
        <h1>Danh sách lệnh</h1>
        <p>{data ? `${int(data.total)} lệnh khớp điều kiện lọc` : 'Đang tải…'}</p>
      </div>

      <div className="bar-ctl">
        <select value={symbol} onChange={(e) => { setSymbol(e.target.value); setPage(1) }}>
          <option value="">Tất cả coin</option>
          {symbols.map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol} ({s.n})</option>)}
        </select>
        <select value={flow} onChange={(e) => { setFlow(e.target.value); setPage(1) }}>
          <option value="">Tất cả nhánh</option>
          {flows.map((f) => <option key={f.flow} value={f.flow}>{f.flow}</option>)}
        </select>
        <select value={only} onChange={(e) => { setOnly(e.target.value); setPage(1) }}>
          <option value="">Thắng và thua</option>
          <option value="win">Chỉ lệnh thắng</option>
          <option value="loss">Chỉ lệnh thua</option>
        </select>
      </div>

      <Block flush>
        {err ? <ErrorBox error={err} />
          : !data ? <Loading />
          : data.rows.length === 0 ? <Empty text="Không có lệnh nào khớp" />
          : (
            <>
              <div className="tblwrap">
                <table>
                  <thead>
                    <tr>
                      <th>Coin</th><th>Nhánh</th><th>Hướng</th><th className="n">Bậc</th>
                      <th>Vào lệnh</th><th className="n">Giá khớp</th><th className="n">Giá thoát</th>
                      <th className="n">Giữ</th><th>Kết cục</th>
                      <th className="n">Lãi lỗ</th><th className="n">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((t) => (
                      <tr key={t.id}>
                        <td className="mono">{t.symbol}</td>
                        <td className="mono" style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{t.flow}</td>
                        <td><span className={`tag ${t.side === 'LONG' ? 'trend' : 'busd'}`}>{t.side}</span></td>
                        <td className="n">{t.phase}</td>
                        <td className="mono" style={{ fontSize: 11.5 }}>{dt(t.enter_time)}</td>
                        <td className="n">{num(t.matched_price, 6)}</td>
                        <td className="n">{num(t.exit_price, 6)}</td>
                        <td className="n">{dur(t.gio_giu)}</td>
                        <td style={{ color: t.status === 2 ? 'var(--up)' : t.status === 3 ? 'var(--down)' : 'var(--ink-3)' }}>
                          {t.status_ten}
                        </td>
                        <td className={`n ${Number(t.pnl) > 0 ? 'up' : Number(t.pnl) < 0 ? 'down' : ''}`}>
                          {money(t.pnl)}
                        </td>
                        <td className="n">{pct(t.profit_pct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pager">
                <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Trước</button>
                <span>Trang {page} / {pages}</span>
                <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Sau →</button>
                <span className="sp">{int(data.total)} lệnh</span>
              </div>
            </>
          )}
      </Block>
    </>
  )
}

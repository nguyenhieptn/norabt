import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Empty, Block } from '../components/common'
import { Pager, usePaged } from '../components/Pager'
import { int, num } from '../lib/format'

/** Kho alpha: các chiến thuật đã có, dùng để gắn vào lần chạy backtest */
export default function KhoAlpha() {
  const [rows, setRows] = useState(null)
  const [groups, setGroups] = useState([])
  const [group, setGroup] = useState('')
  const [q, setQ] = useState('')
  const [err, setErr] = useState(null)

  const load = () => {
    setRows(null); setErr(null)
    api.strategies({ group, q, limit: 800 })
      .then((r) => setRows(r.rows)).catch(setErr)
  }

  useEffect(() => { api.strategyGroups().then((r) => setGroups(r.rows)).catch(() => {}) }, [])
  useEffect(load, [group])

  const pg = usePaged(rows)

  return (
    <>
      <div className="bar-ctl">
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">Tất cả nhóm</option>
          {groups.map((g) => <option key={g.name} value={g.name}>{g.name} ({g.n})</option>)}
        </select>
        <input placeholder="Tìm theo tên…" value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()} style={{ minWidth: 220 }} />
        <button className="btn" onClick={load}>Tìm</button>
      </div>

      <Block flush>
        {err ? <ErrorBox error={err} onRetry={load} />
          : rows === null ? <Loading />
          : rows.length === 0 ? <Empty />
          : (
            <>
              <div className="tblwrap">
              <table>
                <thead>
                  <tr>
                    <th>Mã</th><th>Tên</th><th>Nhóm</th><th>Loại</th>
                    <th className="n">Chốt lãi</th><th className="n">Cắt lỗ</th>
                    <th className="n">Đòn bẩy</th>
                    <th style={{ textAlign: 'right' }}>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {pg.slice.map((s) => (
                    <tr key={s.id}>
                      <td className="mono">
                        <Link to={`/library/alpha/${s.id}`} style={{ color: 'var(--amber)' }}>{s.id}</Link>
                      </td>
                      <td><Link to={`/library/alpha/${s.id}`}>{s.name}</Link></td>
                      <td style={{ color: 'var(--ink-3)' }}>{s.group || '—'}</td>
                      <td>
                        {s.is_container === 1
                          ? <span className="tag dca">Bộ chứa</span>
                          : <span className="tag">Đơn lẻ</span>}
                      </td>
                      <td className="n">{s.takeprofit ?? '—'}</td>
                      <td className="n">{s.stoploss ?? '—'}</td>
                      <td className="n">{s.margin ?? '—'}</td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <Link
                          className="btn pri"
                          to="/library/base"
                          style={{ fontSize: 11.5, padding: '2px 8px' }}
                          title="Tạo lần chạy Backtest trong Base với chiến lược này"
                        >
                          Chạy Backtest ➔
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <Pager {...pg} unit="chiến lược" />
            </>
          )}
      </Block>
    </>
  )
}

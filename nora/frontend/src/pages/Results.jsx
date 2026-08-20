import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Empty, Block, Spark, Legend } from '../components/common'
import { Pager, usePaged } from '../components/Pager'
import MetricTable from '../components/MetricTable'
import { int, money } from '../lib/format'

/** Bảng chỉ số chi tiết — bung ra khi bấm vào một lần chạy */
function MetricPanel({ runId }) {
  const [m, setM] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setM(null); setErr(null)
    api.metrics(runId).then(setM).catch(setErr)
  }, [runId])

  if (err) return <div className="msg err">{String(err.message || err)}</div>
  if (!m) return <Loading text="Đang tính chỉ số…" />

  const eq = m.equity_daily || []

  return (
    <div style={{ background: 'var(--panel-2)', borderTop: '1px solid var(--line-2)', padding: '16px 18px' }}>
      <div style={{ border: '1px solid var(--line)', background: 'var(--panel)', marginBottom: 16 }}>
        <MetricTable m={m} gonNheYNghia />
      </div>

      {eq.length > 1 && (
        <div style={{ border: '1px solid var(--line)', background: 'var(--panel)', padding: '12px 14px' }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.1em',
            textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 8,
          }}>
            Đường vốn theo ngày · {eq.length} ngày
            {m.peak_at && ` · sụt sâu nhất từ ${m.peak_at} đến ${m.trough_at}`}
          </div>
          <Spark series={[{ data: eq.map((e) => e.balance), color: 'var(--amber)' }]} height={150} />
          <Legend items={[
            { label: 'Số dư đầu', color: 'var(--ink-3)', value: m.start_balance },
            { label: 'Số dư cuối', color: 'var(--amber)', value: m.end_balance },
          ]} />
        </div>
      )}

      <div className="bar-ctl" style={{ marginTop: 14, marginBottom: 0 }}>
        <Link className="btn" to={`/library/result/${runId}`}>Xem đầy đủ</Link>
        <Link className="btn" to={`/library/result/${runId}/trades`}>Danh sách lệnh</Link>
        <Link className="btn pri" to={`/library/result/${runId}/chart`}>Biểu đồ</Link>
      </div>
    </div>
  )
}

export default function Results() {
  const [rows, setRows] = useState(null)
  const [groups, setGroups] = useState([])
  const [group, setGroup] = useState('')
  const [q, setQ] = useState('')
  const [err, setErr] = useState(null)
  const [open, setOpen] = useState(null)

  const load = () => {
    setRows(null); setErr(null); setOpen(null)
    api.runs({ group, q, limit: 300 }).then((r) => setRows(r.rows)).catch(setErr)
  }

  useEffect(() => { api.groups().then((r) => setGroups(r.rows)).catch(() => {}) }, [])
  useEffect(load, [group])

  const pg = usePaged(rows)

  return (
    <>
      <div className="head">
        <h1>Kết quả các lần chạy</h1>
        <p>Bấm vào một dòng để xem bảng chỉ số chi tiết và biểu đồ đánh giá.</p>
      </div>

      <div className="bar-ctl">
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">Tất cả nhóm</option>
          {groups.map((g) => <option key={g.name} value={g.name}>{g.name} ({g.n})</option>)}
        </select>
        <input placeholder="Tìm theo tên hoặc mã…" value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()} style={{ minWidth: 240 }} />
        <button className="btn" onClick={load}>Tìm</button>
      </div>

      <Block flush>
        {err ? <ErrorBox error={err} onRetry={load} />
          : rows === null ? <Loading />
          : rows.length === 0 ? <Empty text="Không có lần chạy nào khớp" />
          : (
            <>
              <div className="tblwrap">
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 26 }}></th>
                    <th>Mã</th><th>Tên</th><th>Nhóm</th>
                    <th className="n">Số lệnh</th><th className="n">Số dư</th><th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {pg.slice.map((r) => (
                    <React.Fragment key={r.id}>
                      <tr className="rowlink"
                        onClick={() => setOpen(open === r.id ? null : r.id)}
                        style={open === r.id ? { background: 'var(--panel-2)' } : undefined}>
                        <td style={{ color: 'var(--amber)', fontFamily: 'var(--mono)' }}>
                          {open === r.id ? '▾' : '▸'}
                        </td>
                        <td className="mono">{r.id}</td>
                        <td>{r.name || '—'}</td>
                        <td style={{ color: 'var(--ink-3)' }}>{r.group || '—'}</td>
                        <td className="n">{r.trades ? int(r.trades) : '—'}</td>
                        <td className="n">{money(r.balance)}</td>
                        <td>
                          <span className={`tag ${r.running ? 'run' : 'stop'}`}>
                            {r.running ? 'Đang chạy' : 'Đã dừng'}
                          </span>
                        </td>
                      </tr>
                      {open === r.id && (
                        <tr>
                          <td colSpan={7} style={{ padding: 0, whiteSpace: 'normal' }}>
                            <MetricPanel runId={r.id} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
              </div>
              <Pager {...pg} unit="lần chạy" />
            </>
          )}
      </Block>
    </>
  )
}

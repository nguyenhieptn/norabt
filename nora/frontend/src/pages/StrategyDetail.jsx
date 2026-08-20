import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Block, Empty } from '../components/common'
import { strategyKind } from '../lib/format'

/** Vẽ điều kiện JSON thành cây dễ đọc.
 *  Mảng ngoài cùng là HOẶC, mảng bên trong là VÀ, phần tử 3 ô là một phép so sánh. */
function Cond({ node, depth = 0 }) {
  if (node === null || node === undefined) return null

  // phép so sánh: [vế trái, toán tử, vế phải]
  if (Array.isArray(node) && node.length === 3 && typeof node[1] === 'string'
      && ['>', '<', '=', '>=', '<=', '!='].includes(node[1])) {
    return (
      <div>
        <Side v={node[0]} /> <span className="op">{node[1]}</span> <Side v={node[2]} />
      </div>
    )
  }

  if (Array.isArray(node)) {
    const label = depth % 2 === 0 ? 'HOẶC' : 'VÀ'
    if (node.length === 1) return <Cond node={node[0]} depth={depth + 1} />
    return (
      <div className="grp">
        {node.map((c, i) => (
          <div key={i}>
            {i > 0 && <span className="op" style={{ opacity: .7 }}>{label}</span>}
            <Cond node={c} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }
  return <Side v={node} />
}

function Side({ v }) {
  if (v === null || v === undefined) return <span className="val">—</span>
  if (typeof v === 'number' || typeof v === 'boolean') return <span className="val">{String(v)}</span>
  if (typeof v === 'string') return <span className="val">{v}</span>

  const t = v.type || 'frame'
  if (t === 'frame') {
    const parts = [v.frame, v.column]
    if (v.index !== undefined) parts.push(`[${v.index}]`)
    let s = `${v.frame || ''} ${v.column || ''}${v.index !== undefined ? `(${v.index})` : ''}`
    if (v.percent) s += ` ×${v.percent}%`
    if (v.subtract) s += ` − ${v.subtract.column}`
    if (v.symbol) s = `${v.symbol} ${s}`
    return <span className="col">{s}</span>
  }
  if (t === 'event') return <span className="col">lệnh.{v.column}</span>
  if (t === 'calculate') {
    return (
      <span>
        (<Side v={v.number_1} /> <span className="op">{v.logic}</span> <Side v={v.number_2} />)
        {v.multiply && v.multiply !== 1 ? <span className="val"> ×{v.multiply}</span> : null}
      </span>
    )
  }
  if (t === 'min' || t === 'max') {
    return (
      <span>
        <span className="op">{t}</span>(
        {(v.numbers || []).map((n, i) => (
          <span key={i}>{i > 0 && ', '}<Side v={n} /></span>
        ))})
      </span>
    )
  }
  return <span className="val">{JSON.stringify(v).slice(0, 60)}</span>
}

export default function StrategyDetail() {
  const { id } = useParams()
  const [s, setS] = useState(null)
  const [err, setErr] = useState(null)
  const [raw, setRaw] = useState(false)

  useEffect(() => {
    setS(null); setErr(null)
    api.strategy(id).then(setS).catch(setErr)
  }, [id])

  if (err) return <ErrorBox error={err} />
  if (!s) return <Loading />

  let content = null
  try { content = typeof s.content === 'string' ? JSON.parse(s.content) : s.content } catch (e) { /* để null */ }
  const kind = strategyKind(s.content)
  const flows = content && typeof content === 'object'
    ? Object.entries(content).filter(([, v]) => v && typeof v === 'object')
    : []

  return (
    <>
      <p className="crumb"><Link to="/library/alpha">Chiến thuật</Link> · mã {id}</p>
      <div className="head">
        <h1>{s.name}</h1>
        <p>
          <span className={`tag ${kind.key}`}>{kind.label}</span>
          {'  '}nhóm {s.group || '—'} · chốt lãi {s.takeprofit ?? '—'} · cắt lỗ {s.stoploss ?? '—'}
          {' '}· đòn bẩy {s.margin ?? '—'} · thời hạn {s.timelife ?? '—'}
        </p>
      </div>

      {s.children && (
        <Block title="Các chiến thuật con" note="bộ chứa gom nhiều chiến thuật chạy song song" flush>
          <div className="tblwrap">
            <table>
              <thead><tr><th>Mã</th><th>Tên</th><th className="n">Thứ tự</th><th className="n">Số vị thế</th></tr></thead>
              <tbody>
                {s.children.map((c) => (
                  <tr key={c.id}>
                    <td className="mono"><Link to={`/library/alpha/${c.id}`} style={{ color: 'var(--amber)' }}>{c.id}</Link></td>
                    <td><Link to={`/library/alpha/${c.id}`}>{c.name}</Link></td>
                    <td className="n">{c.weight}</td>
                    <td className="n">{c.slot}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Block>
      )}

      <Block
        title="Điều kiện vào lệnh"
        note={<button className="btn" style={{ padding: '4px 10px', fontSize: 12 }}
          onClick={() => setRaw(!raw)}>{raw ? 'Xem dạng cây' : 'Xem JSON gốc'}</button>}
      >
        {!content ? <Empty text="Chiến thuật này không có nội dung điều kiện" />
          : raw ? (
            <pre className="cond" style={{ whiteSpace: 'pre-wrap', margin: 0, maxHeight: 520, overflow: 'auto' }}>
              {JSON.stringify(content, null, 2)}
            </pre>
          ) : flows.length === 0 ? <Empty />
          : (
            <div className="cond">
              {flows.map(([name, flow]) => (
                <div key={name} style={{ marginBottom: 18 }}>
                  <div style={{ color: 'var(--amber)', fontWeight: 600, marginBottom: 4 }}>
                    {name} {flow.type ? `· ${flow.type}` : ''}
                    {Array.isArray(flow.match) ? ` · ${flow.match.length} bậc` : ''}
                  </div>
                  {Array.isArray(flow.match) && flow.match.map((ph, i) => (
                    <div key={i} className="grp" style={{ marginBottom: 8 }}>
                      <div style={{ color: 'var(--ink-3)', fontSize: 11.5 }}>
                        Bậc {i} · vốn {ph.enter_package ?? '—'}
                        {typeof ph.enter_package === 'number' ? '%' : ''}
                        {ph.margin ? ` · đòn bẩy ${ph.margin}` : ''}
                        {ph.stoploss ? ` · cắt lỗ ${ph.stoploss}` : ''}
                      </div>
                      <Cond node={ph.condition} />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
      </Block>
    </>
  )
}

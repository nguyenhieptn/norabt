import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Block, Empty } from '../components/common'
import { Cond } from '../components/Cond'
import { strategyKind } from '../lib/format'

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

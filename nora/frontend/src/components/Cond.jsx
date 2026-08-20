import React from 'react'

/** Vẽ điều kiện JSON thành cây dễ đọc.
 *  Mảng ngoài cùng là HOẶC, mảng bên trong là VÀ, phần tử 3 ô là một phép so sánh. */
export function Cond({ node, depth = 0 }) {
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

export function Side({ v }) {
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

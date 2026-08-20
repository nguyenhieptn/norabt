import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Cond } from './Cond'
import { strategyKind, int } from '../lib/format'

/**
 * Tóm tắt chiến lược của một lần chạy: nhìn phát là biết nó là loại gì, vào
 * lệnh theo điều kiện nào, nhồi mấy bậc, mỗi bậc bao nhiêu vốn.
 */
export default function StrategyCard({ s }) {
  const [mo, setMo] = useState(false)
  const kind = strategyKind(s.content)
  let content = null
  try { content = typeof s.content === 'string' ? JSON.parse(s.content) : s.content } catch (e) { /* để trống */ }
  const luong = content && typeof content === 'object'
    ? Object.entries(content).filter(([, v]) => v && typeof v === 'object' && v.type)
    : []

  const so = [
    ['Chốt lãi', s.takeprofit], ['Cắt lỗ', s.stoploss], ['Đòn bẩy', s.margin],
    ['Thời hạn', s.timelife], ['Lãi nền', s.baseprofit],
    ['Bước lãi', s.step_profit], ['Lùi lãi', s.back_profit],
    ['Mốc tính', s.baseprofit_baseon],
  ]

  return (
    <div className="cl">
      <div className="cl-h">
        <span className={`tag ${kind.key}`}>{kind.label}</span>
        <Link to={`/library/alpha/${s.id}`} className="mono" style={{ color: 'var(--amber)' }}>{s.id}</Link>
        <b>{s.name}</b>
        <span style={{ color: 'var(--ink-3)', fontSize: 12.5 }}>
          {s.group || '—'} · chạy trên {int(s.so_coin)} coin
          {s.is_container ? ' · bộ chứa' : ''}
        </span>
        <button className="btn" style={{ marginLeft: 'auto' }} onClick={() => setMo(!mo)}>
          {mo ? 'Thu gọn' : 'Xem điều kiện vào lệnh'}
        </button>
      </div>

      <div className="cl-so">
        {so.map(([k, v]) => (
          <div key={k}>
            <span>{k}</span>
            <b>{v === null || v === undefined || v === '' ? '—' : String(v)}</b>
          </div>
        ))}
      </div>

      <div className="cl-luong">
        {luong.map(([ten, f]) => (
          <span key={ten} className="cl-chip">
            <i className={f.type === 'LONG' ? 'up' : 'down'}>{f.type}</i>
            {ten}
            <em>{(f.match || []).length} bậc</em>
            {(f.match || []).some((m) => m.enter_package !== undefined) && (
              <u>vốn {(f.match || []).map((m) => (
                // vốn tính bằng công thức (ví dụ min(close/atr, …)) thì không có
                // con số cố định để hiện — nói thẳng là "động" cho khỏi hiểu nhầm
                m.enter_package && typeof m.enter_package === 'object' ? 'động' : m.enter_package
              )).join(' / ')}</u>
            )}
          </span>
        ))}
      </div>

      {mo && (
        <div className="cond" style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
          {luong.length === 0 ? <div className="msg">Không đọc được nội dung điều kiện</div>
            : luong.map(([ten, f]) => (
              <div key={ten} style={{ marginBottom: 16 }}>
                <div style={{ color: 'var(--amber)', fontWeight: 600, marginBottom: 4 }}>
                  {ten} · {f.type} · {(f.match || []).length} bậc
                </div>
                {(f.match || []).map((ph, i) => (
                  <div key={i} className="grp" style={{ marginBottom: 8 }}>
                    <div style={{ color: 'var(--ink-3)', fontSize: 11.5 }}>
                      Bậc {i}
                      {ph.enter_package !== undefined && typeof ph.enter_package !== 'object'
                        ? ` · vốn ${ph.enter_package}` : ''}
                      {ph.margin ? ` · đòn bẩy ${ph.margin}` : ''}
                      {ph.stoploss ? ` · cắt lỗ ${ph.stoploss}` : ''}
                    </div>
                    <Cond node={ph.condition} />
                  </div>
                ))}
                {f.stop && (
                  <div className="grp">
                    <div style={{ color: 'var(--ink-3)', fontSize: 11.5 }}>Điều kiện thoát</div>
                    {(Array.isArray(f.stop) ? f.stop : [f.stop]).map((x, i) => (
                      <Cond key={i} node={x.condition ?? x} />
                    ))}
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

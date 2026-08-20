import React, { useEffect, useRef, useState } from 'react'
import { int, money, num } from '../lib/format'

/** Đo bề ngang thật của khung để vẽ theo pixel — chữ không bị kéo méo như khi
 *  phóng viewBox. Không đo được (lúc dựng thử) thì lấy một bề ngang mặc định. */
export function useWidth(mac_dinh = 900) {
  const ref = useRef(null)
  const [w, setW] = useState(mac_dinh)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined
    const ro = new ResizeObserver(([e]) => {
      const x = Math.round(e.contentRect.width)
      if (x > 0) setW(x)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

/** Ô chú giải nổi theo con trỏ */
function Tip({ x, y, children }) {
  if (x === null) return null
  return (
    <div className="viz-tip" style={{ left: x, top: y }}>{children}</div>
  )
}

const MAU = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)']

/* ------------------------------------------------------------------ tròn */

/**
 * Vành khuyên phần trên tổng thể. Tối đa 6 phần, phần thứ 7 trở đi gộp thành
 * "Khác" — quá 6 màu là mắt hết phân biệt nổi.
 * Mỗi cung cách nhau 2px bằng chính màu nền, không viền.
 */
export function Donut({ data, nhan_tong = 'Tổng', don_vi = '' }) {
  const [tip, setTip] = useState({ x: null })
  const sap = [...data].sort((a, b) => b.n - a.n)
  const chinh = sap.slice(0, 6)
  const con_lai = sap.slice(6)
  const phan = con_lai.length
    ? [...chinh, { ten: `Khác (${con_lai.length} nhóm)`, n: con_lai.reduce((t, x) => t + x.n, 0) }]
    : chinh
  const tong = phan.reduce((t, x) => t + x.n, 0) || 1

  const S = 190, R = 84, r = 56, C = S / 2
  const KHE = 2 / R                      // khe hở 2px quy ra radian

  let goc = -Math.PI / 2
  const cung = phan.map((p, i) => {
    const rong = (p.n / tong) * Math.PI * 2
    const a0 = goc + KHE / 2
    const a1 = goc + rong - KHE / 2
    goc += rong
    const lon = rong > Math.PI ? 1 : 0
    const P = (rad, ban) => [C + ban * Math.cos(rad), C + ban * Math.sin(rad)]
    const [x0, y0] = P(a0, R); const [x1, y1] = P(a1, R)
    const [x2, y2] = P(a1, r); const [x3, y3] = P(a0, r)
    return {
      ...p, i,
      pct: (p.n / tong) * 100,
      d: a1 <= a0 ? '' : `M${x0},${y0} A${R},${R} 0 ${lon} 1 ${x1},${y1} L${x2},${y2} A${r},${r} 0 ${lon} 0 ${x3},${y3} Z`,
    }
  })

  return (
    <div className="viz" onMouseLeave={() => setTip({ x: null })}>
      <div className="viz-donut">
        <svg width={S} height={S} role="img" aria-label={nhan_tong}>
          {cung.map((c) => (
            <path key={c.ten} d={c.d} fill={MAU[c.i % MAU.length]}
              opacity={tip.i === undefined || tip.i === c.i ? 1 : 0.35}
              onMouseMove={(e) => setTip({
                x: e.nativeEvent.offsetX + 14, y: e.nativeEvent.offsetY + 10, i: c.i, c,
              })} />
          ))}
          <text x={C} y={C - 4} textAnchor="middle" className="viz-hero">{int(tong)}</text>
          <text x={C} y={C + 15} textAnchor="middle" className="viz-sub">{nhan_tong}</text>
        </svg>

        <div className="viz-legend">
          {cung.map((c) => (
            <div key={c.ten} className={`viz-leg ${tip.i !== undefined && tip.i !== c.i ? 'mo' : ''}`}
              onMouseMove={(e) => setTip({ x: 12, y: 12, i: c.i, c })}>
              <i style={{ background: MAU[c.i % MAU.length] }} />
              <span className="ten">{c.ten}</span>
              <b>{int(c.n)}</b>
              <span className="pct">{num(c.pct, 1)}%</span>
            </div>
          ))}
        </div>
      </div>
      <Tip {...tip}>
        {tip.c && <><b>{tip.c.ten}</b><br />{int(tip.c.n)} {don_vi} · {num(tip.c.pct, 1)}%</>}
      </Tip>
    </div>
  )
}

/* -------------------------------------------------------------------- cột */

/**
 * Cột lãi lỗ quanh mốc 0 — lãi và lỗ là hai cực nên dùng hai màu đối nghịch,
 * không phải hai màu danh mục. Chỉ ghi số ở cột cao nhất và thấp nhất.
 */
export function CotPnL({ data, cao = 230 }) {
  const [ref, W] = useWidth()
  const [tip, setTip] = useState({ x: null })
  if (!data.length) return null

  const L = 8, R = 8, T = 22, B = 34
  const w = Math.max(320, W)
  const trong = w - L - R
  const bang = trong / data.length
  const rong = Math.min(24, bang - 10)
  const H = cao - T - B

  const dinh = Math.max(...data.map((d) => Number(d.gia_tri) || 0), 0)
  const day = Math.min(...data.map((d) => Number(d.gia_tri) || 0), 0)
  const bien = dinh - day || 1
  const y0 = T + (dinh / bien) * H                        // mốc 0
  const yOf = (v) => T + ((dinh - v) / bien) * H

  const max_i = data.indexOf(data.reduce((a, b) => (Number(b.gia_tri) > Number(a.gia_tri) ? b : a)))
  const min_i = data.indexOf(data.reduce((a, b) => (Number(b.gia_tri) < Number(a.gia_tri) ? b : a)))

  return (
    <div className="viz" ref={ref} onMouseLeave={() => setTip({ x: null })}>
      <svg width={w} height={cao} role="img">
        <line x1={L} x2={w - R} y1={y0} y2={y0} className="viz-truc" />
        {data.map((d, i) => {
          const v = Number(d.gia_tri) || 0
          const x = L + bang * i + (bang - rong) / 2
          const y = v >= 0 ? yOf(v) : y0
          const h = Math.max(1.5, Math.abs(yOf(v) - y0))
          const am = v < 0
          const bk = Math.min(4, rong / 2, h)
          // bo 4px ở đầu số liệu, vuông ở chân mốc 0
          const d_path = am
            ? `M${x},${y} h${rong} v${h - bk} a${bk},${bk} 0 0 1 ${-bk},${bk} h${-(rong - bk * 2)} a${bk},${bk} 0 0 1 ${-bk},${-bk} Z`
            : `M${x},${y + bk} a${bk},${bk} 0 0 1 ${bk},${-bk} h${rong - bk * 2} a${bk},${bk} 0 0 1 ${bk},${bk} v${h - bk} h${-rong} Z`
          return (
            <g key={d.nhan + i}
              onMouseMove={(e) => setTip({ x: e.nativeEvent.offsetX + 14, y: e.nativeEvent.offsetY - 6, d })}>
              <rect x={L + bang * i} y={T} width={bang} height={H} fill="transparent" />
              <path d={d_path} fill={am ? 'var(--down)' : 'var(--up)'} />
              {(i === max_i || i === min_i) && (
                <text x={x + rong / 2} y={am ? y + h + 13 : y - 6} textAnchor="middle" className="viz-nhan">
                  {money(v)}
                </text>
              )}
              <text x={x + rong / 2} y={cao - 12} textAnchor="middle" className="viz-truc-nhan">
                {d.nhan}
              </text>
            </g>
          )
        })}
      </svg>
      <Tip {...tip}>
        {tip.d && <><b>{tip.d.ten || tip.d.nhan}</b><br />{money(tip.d.gia_tri)}
          {tip.d.phu ? <><br />{tip.d.phu}</> : null}</>}
      </Tip>
    </div>
  )
}

/* --------------------------------------------------------------- tăng trưởng */

/**
 * Đường tăng trưởng lũy kế: đường 2px, nền loang 10%, lưới mảnh một nét,
 * chấm cuối có vòng nền 2px và ghi thẳng giá trị.
 */
export function TangTruong({ data, cao = 250, nhan = 'Lãi lỗ lũy kế' }) {
  const [ref, W] = useWidth()
  const [tip, setTip] = useState({ x: null })
  if (data.length < 2) return null

  const L = 56, R = 78, T = 18, B = 30
  const w = Math.max(360, W)
  const H = cao - T - B
  const trong = w - L - R

  const gt = data.map((d) => Number(d.cong_don) || 0)
  let hi = Math.max(...gt, 0)
  let lo = Math.min(...gt, 0)
  const dem = (hi - lo) * 0.08 || 1
  hi += dem; lo -= dem
  const X = (i) => L + (i / (data.length - 1)) * trong
  const Y = (v) => T + ((hi - v) / (hi - lo)) * H

  const duong = gt.map((v, i) => `${i ? 'L' : 'M'}${X(i)},${Y(v)}`).join(' ')
  const nen = `${duong} L${X(gt.length - 1)},${Y(Math.max(lo, 0))} L${X(0)},${Y(Math.max(lo, 0))} Z`

  // vạch lưới tròn số
  const buoc = Math.pow(10, Math.floor(Math.log10(Math.max(1, hi - lo)))) / 2
  const vach = []
  for (let v = Math.ceil(lo / buoc) * buoc; v <= hi; v += buoc) vach.push(v)

  const cuoi = gt.length - 1
  const i_tip = tip.i ?? null

  return (
    <div className="viz" ref={ref} onMouseLeave={() => setTip({ x: null })}>
      <svg width={w} height={cao} role="img" aria-label={nhan}
        onMouseMove={(e) => {
          const px = e.nativeEvent.offsetX
          const i = Math.max(0, Math.min(data.length - 1,
            Math.round(((px - L) / trong) * (data.length - 1))))
          setTip({ x: Math.min(px + 14, w - 150), y: 14, i })
        }}>
        {vach.slice(0, 9).map((v) => (
          <g key={v}>
            <line x1={L} x2={w - R} y1={Y(v)} y2={Y(v)} className="viz-luoi" />
            <text x={L - 9} y={Y(v) + 4} textAnchor="end" className="viz-truc-nhan">{int(v)}</text>
          </g>
        ))}
        <line x1={L} x2={w - R} y1={Y(0)} y2={Y(0)} className="viz-truc" />

        <path d={nen} fill="var(--s1)" opacity=".1" />
        <path d={duong} fill="none" stroke="var(--s1)" strokeWidth="2"
          strokeLinejoin="round" strokeLinecap="round" />

        {i_tip !== null && (
          <>
            <line x1={X(i_tip)} x2={X(i_tip)} y1={T} y2={T + H} className="viz-doc" />
            <circle cx={X(i_tip)} cy={Y(gt[i_tip])} r="5" fill="var(--s1)"
              stroke="var(--panel)" strokeWidth="2" />
          </>
        )}

        <circle cx={X(cuoi)} cy={Y(gt[cuoi])} r="4.5" fill="var(--s1)"
          stroke="var(--panel)" strokeWidth="2" />
        <text x={X(cuoi) + 10} y={Y(gt[cuoi]) + 4} className="viz-nhan">{money(gt[cuoi])}</text>

        {data.map((d, i) => (
          (i === 0 || i === cuoi || i % Math.ceil(data.length / 6) === 0) && (
            <text key={d.thang} x={X(i)} y={cao - 10} textAnchor="middle" className="viz-truc-nhan">
              {d.thang}
            </text>
          )
        ))}
      </svg>
      <Tip {...tip}>
        {i_tip !== null && data[i_tip] && (
          <>
            <b>{data[i_tip].thang}</b><br />
            Lũy kế {money(data[i_tip].cong_don)}<br />
            Tháng này {money(data[i_tip].pnl)} · {int(data[i_tip].so_lenh)} lệnh
          </>
        )}
      </Tip>
    </div>
  )
}

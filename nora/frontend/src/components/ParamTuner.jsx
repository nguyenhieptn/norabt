import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Loading } from './common'
import DaiGiaTri, { sinhDai } from './DaiGiaTri'
import { int, money } from '../lib/format'

/** Đếm số tổ hợp: nhân số giá trị của các biến thuộc diện quét */
export function demToHop(bien) {
  return (bien || []).reduce(
    (t, b) => (b.quet ? t * Math.max(1, (b.values || []).filter((v) => String(v).trim()).length) : t),
    1,
  )
}

/** Tính công thức dạng "100+#x#" hoặc "10000 / #x#" khi thay số vào.
 *  Chỉ nhận đúng hai dạng đó, không đánh giá chuỗi tuỳ ý. */
function tinhCongThuc(ct, ten, v) {
  const so = Number(v)
  if (!ct || Number.isNaN(so)) return null
  const pheps = { '+': (a, b) => a + b, '-': (a, b) => a - b,
    '*': (a, b) => a * b, '/': (a, b) => (b ? a / b : null) }
  const moc = ct.replace(/\s+/g, '')
  let m = new RegExp(`^(-?\\d+(?:\\.\\d+)?)([+\\-*/])#${ten}#$`).exec(moc)
  if (m) return pheps[m[2]](Number(m[1]), so)
  m = new RegExp(`^#${ten}#([+\\-*/])(-?\\d+(?:\\.\\d+)?)$`).exec(moc)
  if (m) return pheps[m[1]](so, Number(m[2]))
  return null
}

const goiSo = (x) => (x === null || x === undefined ? '?'
  : String(Math.round(x * 100) / 100).replace('.', ','))

/** Nghĩa của một biến ứng với giá trị đang gõ, không phải giá trị lúc nạp trang */
function nghiaTheoGiaTri(b, bien) {
  const v = (b.values || []).filter((x) => String(x).trim() !== '')
  if (!v.length) return b.y_nghia
  const ct = (bien || []).find((x) => x.type === 'EXPRESSIONS'
    && String((x.values || [])[0] || '').includes(`#${b.name}#`))
  if (!ct) return b.y_nghia

  const ten_dung = String(ct.name || '')
  const noi = (gt) => {
    const kq = tinhCongThuc(String((ct.values || [])[0]), b.name, gt)
    if (kq === null) return null
    const bac = /^match_order(\d+)/.exec(ten_dung)
    if (bac) {
      const lech = 100 - kq
      return `nhồi bậc ${bac[1]} khi giá ${lech > 0 ? 'giảm' : 'tăng'} ${goiSo(Math.abs(lech))}%`
    }
    if (ten_dung.startsWith('match_price')) {
      const lech = 100 - kq
      if (Math.abs(lech) < 1e-9) return 'đặt đúng giá tham chiếu'
      return `đặt ${lech > 0 ? 'thấp hơn' : 'cao hơn'} giá tham chiếu ${goiSo(Math.abs(lech))}%`
    }
    return `${ten_dung} = ${goiSo(kq)}`
  }

  const dau = noi(v[0])
  if (!dau) return b.y_nghia
  if (v.length === 1) return dau
  const cuoi = noi(v[v.length - 1])
  return cuoi ? `${dau}  →  ${cuoi}` : dau
}

/** Giá trị nào nằm ngoài lưới cột mà bộ dữ liệu đã tính sẵn.
 *  Quét ra ngoài lưới thì engine đọc phải cột trống, kết quả rỗng mà không báo. */
function ngoaiLuoi(c, values) {
  const g = c.gioi_han || {}
  const v = (values || []).map((x) => String(x).trim()).filter(Boolean)
  if (g.chon) return v.filter((x) => !g.chon.includes(x))
  if (g.tu !== undefined) {
    return v.filter((x) => !/^\d+$/.test(x) || Number(x) < g.tu || Number(x) > g.den)
  }
  return []
}

const MO_TA = {
  INPUT: 'giá trị rời — mỗi giá trị là một nhánh quét',
  SETS: 'bộ giá trị, ví dụ tỷ lệ vốn từng bậc DCA',
  EXPRESSIONS: 'công thức tính từ biến khác, viết #tên_biến#',
}

/**
 * Bảng nổi để tạo mới hoặc tinh chỉnh dải tham số của một phiên quét.
 *
 * Luôn mở sẵn bằng bộ tham số cho lợi tức cao nhất tìm được (cùng lần chạy →
 * cùng chiến lược → cao nhất hệ thống), để không phải bắt đầu từ màn hình trắng.
 *
 * Cố ý chỉ tạo phiên MỚI, không ghi đè: bảng phiên đào dùng chung với hệ thống
 * thật, sửa thẳng vào phiên đang có kết quả là xoá mất lịch sử của người khác.
 */
export default function ParamTuner({ oid, baseRun, onCreated, onClose }) {
  const [d, setD] = useState(null)
  const [runs, setRuns] = useState([])
  const [err, setErr] = useState(null)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [chiBao, setChiBao] = useState([])       // chỉ báo trong chiến lược của lần chạy gốc
  const [quet, setQuet] = useState({})           // ma -> { ten_bien, values }

  const taoMoi = !oid

  useEffect(() => {
    setD(null); setErr(null); setMsg(null)
    const p = taoMoi ? api.mauThamSo({ base_run: baseRun }) : api.optimizationParams(oid)
    p.then((r) => setD({
      ...r,
      name: taoMoi
        ? (r.tot_nhat?.opt_name ? `${r.tot_nhat.opt_name} (phiên mới)` : 'Phiên đào mới')
        : `${r.name} (bản chỉnh)`,
      base_run: r.base_run || baseRun || '',
    })).catch(setErr)
  }, [oid, baseRun])

  useEffect(() => {
    if (taoMoi) api.runs({ limit: 300 }).then((r) => setRuns(r.rows)).catch(() => {})
  }, [taoMoi])

  // Chỉ báo (EMA, ATR, Keltner…) nằm trong nội dung chiến lược chứ không phải
  // trong danh sách biến của phiên đào, nên phải đọc riêng từ lần chạy gốc.
  useEffect(() => {
    const r = d?.base_run
    setChiBao([]); setQuet({})
    if (!r) return
    api.chiBaoQuet(r).then((x) => setChiBao(x.rows || [])).catch(() => setChiBao([]))
  }, [d?.base_run])

  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  /** Chép một chuỗi vào bộ nhớ tạm, có đường lùi cho trình duyệt cũ */
  const chep = (text) => {
    try {
      if (navigator.clipboard?.writeText) { navigator.clipboard.writeText(text); return }
    } catch (e) { /* rơi xuống cách cũ */ }
    const o = document.createElement('textarea')
    o.value = text
    o.style.position = 'fixed'; o.style.left = '-9999px'
    document.body.appendChild(o); o.select()
    try { document.execCommand('copy') } catch (e) { /* thôi vậy */ }
    document.body.removeChild(o)
  }

  const than = () => {
    if (err && !d) return <div className="msg err">{String(err.message || err)}</div>
    if (!d) return <Loading text="Đang lấy bộ tham số mẫu…" />

    const doi = (i, moi) => setD({ ...d, bien: d.bien.map((b, k) => (k === i ? { ...b, ...moi } : b)) })
    const xoa = (i) => setD({ ...d, bien: d.bien.filter((_, k) => k !== i) })

    // Thứ tự có ý nghĩa: bộ tối ưu tính lần lượt từ trên xuống, công thức dùng
    // #biến# nào thì biến đó phải nằm phía trên, không thì cả phiên quét dừng
    // giữa chừng với lỗi "Please define #x# before y".
    const doi_cho = (i, buoc) => {
      const j = i + buoc
      if (j < 0 || j >= d.bien.length) return
      const ds = [...d.bien]
      const t = ds[i]; ds[i] = ds[j]; ds[j] = t
      setD({ ...d, bien: ds })
    }

    /** Công thức nào đang dùng biến khai phía dưới nó */
    const saiThuTu = (i) => {
      const b = d.bien[i]
      if (b.type !== 'EXPRESSIONS') return null
      const ct = String((b.values || [])[0] || '')
      const tren = new Set(d.bien.slice(0, i).map((x) => x.name))
      const thieu = [...new Set([...ct.matchAll(/#([^#]+)#/g)].map((m) => m[1].split('[')[0]))]
        .filter((x) => !tren.has(x))
      return thieu.length ? thieu : null
    }
    const them = () => setD({
      ...d,
      bien: [...d.bien, { id: '', name: '', type: 'INPUT', values: [], quet: true }],
    })
    const dienTotNhat = () => setD({
      ...d,
      bien: d.bien.map((b) => (b.quet && b.tot_nhat ? { ...b, values: [b.tot_nhat] } : b)),
    })

    // chỉ báo được chọn -> thành biến quét mới, kèm dải giá trị
    const chon = chiBao
      .map((c) => ({ c, q: quet[c.ma] }))
      .filter((x) => x.q && (x.q.values || []).length)
      .map(({ c, q }) => ({
        strategy: c.strategy, ten_bien: q.ten_bien || c.ten_bien_goi_y,
        ap_dung: c.ap_dung,
        // hệ số Keltner viết không dấu chấm trong tên cột: 0.5 -> "05"
        values: q.values.map((v) => (c.bien_doi === 'he_so' ? String(v).replace('.', '') : String(v))),
      }))

    const toHop = demToHop(d.bien) * chon.reduce((t, x) => t * Math.max(1, x.values.length), 1)
    const uocTinh = Math.ceil(toHop / Math.max(1, d.workers))

    const luu = async () => {
      setBusy(true); setMsg(null); setErr(null)
      try {
        if (chon.length) {
          const r = await api.quetChiBao({
            base_run: d.base_run, name: d.name, workers: d.workers,
            data_len: d.data_len, bien: d.bien, chi_bao: chon,
          })
          setMsg(r.message)
          onCreated && onCreated(r.opt_id)
        } else {
          const r = await api.createOptimization({
            name: d.name, base_run: d.base_run, workers: d.workers,
            data_len: d.data_len, node: d.node, bien: d.bien,
          })
          setMsg(`Đã tạo phiên mới mã ${r.id} · ${int(r.to_hop)} tổ hợp · ${r.workers} luồng`)
          onCreated && onCreated(r.id)
        }
      } catch (e) { setErr(e) } finally { setBusy(false) }
    }

    return (
      <>
        {d.tot_nhat && (
          <div className="mau">
            <span>
              Điền sẵn theo bộ cho lợi tức cao nhất — số dư{' '}
              <b className="up">{money(d.tot_nhat.balance)}</b>
              {' '}từ phiên <span className="mono">{d.tot_nhat.opt_id}</span>
              {d.tot_nhat.nguon ? ` · ${d.tot_nhat.nguon}` : ''}
            </span>
            <button className="btn" onClick={dienTotNhat}>Thu về đúng giá trị tốt nhất</button>
          </div>
        )}
        {d.ghi_chu && <div className="pre luu_y">{d.ghi_chu}</div>}

        <div className="tuner-form">
          <label>
            <span>Tên phiên</span>
            <input value={d.name} onChange={(e) => setD({ ...d, name: e.target.value })} />
          </label>
          <label>
            <span>Lần chạy gốc</span>
            {taoMoi && runs.length ? (
              <select value={d.base_run || ''} onChange={(e) => setD({ ...d, base_run: e.target.value })}>
                <option value="">— chọn lần chạy —</option>
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>{r.id} · {r.name}</option>
                ))}
              </select>
            ) : (
              <input type="number" value={d.base_run || ''}
                onChange={(e) => setD({ ...d, base_run: e.target.value })} />
            )}
          </label>
          <label>
            <span>Số luồng (tối đa {d.max_workers})</span>
            <input type="number" min={1} max={d.max_workers} value={d.workers || 1}
              onChange={(e) => setD({
                ...d,
                workers: Math.max(1, Math.min(d.max_workers, Number(e.target.value) || 1)),
              })} />
          </label>
          <label>
            <span>Khối dữ liệu (ngày)</span>
            <input type="number" min={1} value={d.data_len || 1}
              onChange={(e) => setD({ ...d, data_len: Math.max(1, Number(e.target.value) || 1) })} />
          </label>
        </div>

        {taoMoi && !d.base_run && (
          <div className="pre luu_y">
            Chọn lần chạy gốc ở trên để hiện các chỉ báo (EMA, Keltner…) trong chiến lược
            của nó — tick vào là quét luôn chu kỳ, không phải sửa tay nội dung chiến lược.
          </div>
        )}

        {taoMoi && d.base_run && chiBao.length === 0 && (
          <div className="pre luu_y">
            Chiến lược của lần chạy này không dùng chỉ báo nào có chu kỳ quét được
            (EMA, Keltner). RSI và ATR chỉ có sẵn chu kỳ 14 trong bộ dữ liệu.
          </div>
        )}

        {chiBao.length > 0 && (
          <>
            <div className="mau">
              <span>
                Chỉ báo trong chiến lược — tick vào là quét luôn chu kỳ của nó
              </span>
            </div>
            <div className="tblwrap">
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 34 }} />
                    <th>Chỉ báo</th><th className="n">Đang dùng</th>
                    <th>Dải quét</th><th>Tên biến</th><th className="n">Nhánh</th>
                  </tr>
                </thead>
                <tbody>
                  {chiBao.map((c) => {
                    const q = quet[c.ma]
                    return (
                      <tr key={c.ma + c.strategy}>
                        <td>
                          <input type="checkbox" checked={!!q}
                            disabled={!!c.gioi_han?.co_dinh}
                            title={c.gioi_han?.co_dinh ? c.gioi_han.ghi_chu : ''}
                            onChange={(e) => setQuet((s) => {
                              const n = { ...s }
                              if (e.target.checked) {
                                n[c.ma] = { ten_bien: c.ten_bien_goi_y, values: [String(c.gia_tri)] }
                              } else delete n[c.ma]
                              return n
                            })} />
                        </td>
                        <td>
                          <div>{c.nhan}</div>
                          <div style={{ color: 'var(--ink-3)', fontSize: 12 }}>
                            {c.y_nghia} · {int(c.so_cho)} chỗ trong chiến lược {c.chien_luoc}
                          </div>
                        </td>
                        <td className="n mono" style={{ color: 'var(--ink-3)' }}>{String(c.gia_tri)}</td>
                        <td style={{ whiteSpace: 'normal' }}>
                          {q ? (
                            <>
                              <DaiGiaTri values={q.values}
                                onChange={(v) => setQuet((s) => ({ ...s, [c.ma]: { ...s[c.ma], values: v } }))} />
                              {ngoaiLuoi(c, q.values).length > 0 && (
                                <div style={{ color: 'var(--down)', fontSize: 11.5, marginTop: 4 }}>
                                  {ngoaiLuoi(c, q.values).join(', ')} không có trong bộ dữ liệu
                                </div>
                              )}
                            </>
                          ) : <span style={{ color: 'var(--ink-3)' }}>chưa quét</span>}
                          {c.gioi_han?.ghi_chu && (
                            <div style={{ color: 'var(--ink-3)', fontSize: 11.5, marginTop: 3 }}>
                              {c.gioi_han.ghi_chu}
                            </div>
                          )}
                        </td>
                        <td>
                          {q ? (
                            <input className="ten" value={q.ten_bien}
                              onChange={(e) => setQuet((s) => ({
                                ...s, [c.ma]: { ...s[c.ma], ten_bien: e.target.value },
                              }))} />
                          ) : '—'}
                        </td>
                        <td className="n">{q ? (q.values || []).length : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="tblwrap">
          <table>
            <thead>
              <tr>
                <th>Tham số</th><th>Kiểu</th>
                <th>Dải quét</th><th className="n">Nhánh</th><th />
              </tr>
            </thead>
            <tbody>
              {d.bien.map((b, i) => (
                <tr key={b.id || `${b.name}-${i}`}>
                  {/* Nghĩa đứng trước, tên biến trong chiến lược đứng sau: tên do
                      người viết chiến lược tự đặt (input4h, order2…) nên tự nó
                      chẳng nói lên điều gì. */}
                  <td style={{ whiteSpace: 'normal', maxWidth: 330 }}>
                    <div style={{ marginBottom: 4 }}>
                      {nghiaTheoGiaTri(b, d.bien) || '(chưa rõ tác dụng)'}
                    </div>
                    {saiThuTu(i) && (
                      <div style={{ color: 'var(--down)', fontSize: 11.5, marginBottom: 4 }}>
                        dùng #{saiThuTu(i).join('#, #')}# khai phía dưới — bấm ↑ đưa biến đó lên trước
                      </div>
                    )}
                    <input className="ten" value={b.name || ''}
                      title="tên biến trong chiến lược"
                      onChange={(e) => doi(i, { name: e.target.value })} />
                  </td>
                  <td>
                    <select value={b.type}
                      title={MO_TA[b.type]}
                      onChange={(e) => doi(i, {
                        type: e.target.value,
                        quet: e.target.value !== 'EXPRESSIONS',
                      })}>
                      <option value="INPUT">INPUT</option>
                      <option value="SETS">SETS</option>
                      <option value="EXPRESSIONS">EXPRESSIONS</option>
                    </select>
                  </td>
                  <td style={{ whiteSpace: 'normal' }}>
                    {b.type === 'EXPRESSIONS' ? (
                      <input className="dai" value={(b.values || []).join(', ')}
                        onChange={(e) => doi(i, { values: [e.target.value] })} />
                    ) : (
                      <DaiGiaTri
                        values={b.values}
                        tot_nhat={b.tot_nhat}
                        onChange={(v) => doi(i, { values: v })} />
                    )}
                  </td>
                  <td className="n">
                    {b.quet ? (b.values || []).filter((v) => String(v).trim()).length : '—'}
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="goiy" title="Đưa lên trên"
                      disabled={i === 0} onClick={() => doi_cho(i, -1)}>↑</button>{' '}
                    <button className="goiy" title="Đưa xuống dưới"
                      disabled={i === d.bien.length - 1} onClick={() => doi_cho(i, 1)}>↓</button>{' '}
                    {/* chép "#tên#" để dán thẳng vào nội dung chiến lược — đúng
                        thao tác của màn hình tối ưu bên hệ thống gốc */}
                    <button className="goiy" title="Chép #tên# để dán vào chiến lược"
                      onClick={() => chep(b.type === 'SETS' ? `"#${b.name}[]#"` : `"#${b.name}#"`)}>
                      ⧉
                    </button>{' '}
                    <button className="goiy xoa" title="Bỏ biến này" onClick={() => xoa(i)}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="tuner-f">
          <button className="btn" onClick={them}>＋ Thêm biến</button>
          <span>
            Tổng <b style={{ color: 'var(--amber)' }}>{int(toHop)}</b> tổ hợp
            {' · '}chia {d.workers} luồng ≈ <b>{int(uocTinh)}</b> lượt backtest mỗi luồng
          </span>
          <button className="btn pri" onClick={luu}
            disabled={busy
              || chiBao.some((c) => quet[c.ma] && ngoaiLuoi(c, quet[c.ma].values).length)
              || d.bien.some((_, i) => saiThuTu(i))}>
            {busy ? 'Đang lưu…' : taoMoi ? 'Tạo phiên đào' : 'Lưu thành phiên mới'}
          </button>
        </div>

        {toHop > 500 && (
          <div className="pre luu_y">
            {int(toHop)} tổ hợp là rất nhiều — mỗi tổ hợp chạy trọn một lần backtest.
            Nên thu hẹp dải giá trị trước khi chạy.
          </div>
        )}
        {msg && <div className="pre luu_y">{msg}</div>}
        {err && <div className="pre loi">{String(err.message || err)}</div>}
      </>
    )
  }

  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose && onClose()}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-h">
          <b>{taoMoi ? 'Tạo phiên đào alpha mới' : 'Tinh chỉnh tham số quét'}</b>
          <span className="note">
            {taoMoi
              ? 'mở sẵn bằng bộ tham số đang cho lợi tức cao nhất'
              : 'sửa dải giá trị rồi lưu thành phiên mới — phiên gốc giữ nguyên'}
          </span>
          <button className="btn" onClick={onClose}>Đóng</button>
        </div>
        <div className="modal-b">{than()}</div>
      </div>
    </div>
  )
}

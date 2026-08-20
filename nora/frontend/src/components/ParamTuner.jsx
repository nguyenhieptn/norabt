import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Loading } from './common'
import { int, money } from '../lib/format'

/** Đếm số tổ hợp: nhân số giá trị của các biến thuộc diện quét */
export function demToHop(bien) {
  return (bien || []).reduce(
    (t, b) => (b.quet ? t * Math.max(1, (b.values || []).filter((v) => String(v).trim()).length) : t),
    1,
  )
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

  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const than = () => {
    if (err && !d) return <div className="msg err">{String(err.message || err)}</div>
    if (!d) return <Loading text="Đang lấy bộ tham số mẫu…" />

    const doi = (i, moi) => setD({ ...d, bien: d.bien.map((b, k) => (k === i ? { ...b, ...moi } : b)) })
    const xoa = (i) => setD({ ...d, bien: d.bien.filter((_, k) => k !== i) })
    const them = () => setD({
      ...d,
      bien: [...d.bien, { id: '', name: '', type: 'INPUT', values: [], quet: true }],
    })
    const dienTotNhat = () => setD({
      ...d,
      bien: d.bien.map((b) => (b.quet && b.tot_nhat ? { ...b, values: [b.tot_nhat] } : b)),
    })

    const toHop = demToHop(d.bien)
    const uocTinh = Math.ceil(toHop / Math.max(1, d.workers))

    const luu = async () => {
      setBusy(true); setMsg(null); setErr(null)
      try {
        const r = await api.createOptimization({
          name: d.name, base_run: d.base_run, workers: d.workers,
          data_len: d.data_len, node: d.node, bien: d.bien,
        })
        setMsg(`Đã tạo phiên mới mã ${r.id} · ${int(r.to_hop)} tổ hợp · ${r.workers} luồng`)
        onCreated && onCreated(r.id)
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

        <div className="tblwrap">
          <table>
            <thead>
              <tr>
                <th>Biến</th><th>Kiểu</th>
                <th>Dải giá trị (cách nhau bằng dấu phẩy)</th>
                <th>Tốt nhất</th><th className="n">Nhánh</th><th />
              </tr>
            </thead>
            <tbody>
              {d.bien.map((b, i) => (
                <tr key={b.id || `${b.name}-${i}`}>
                  <td>
                    <input className="ten" value={b.name || ''}
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
                    <input className="dai" value={(b.values || []).join(', ')}
                      onChange={(e) => doi(i, { values: e.target.value.split(',').map((x) => x.trim()) })} />
                  </td>
                  <td>
                    {b.tot_nhat ? (
                      <button className="goiy" title="Dùng giá trị này"
                        onClick={() => doi(i, { values: [b.tot_nhat] })}>
                        {b.tot_nhat}
                      </button>
                    ) : <span style={{ color: 'var(--ink-3)' }}>—</span>}
                  </td>
                  <td className="n">
                    {b.quet ? (b.values || []).filter((v) => String(v).trim()).length : '—'}
                  </td>
                  <td>
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
          <button className="btn pri" onClick={luu} disabled={busy}>
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

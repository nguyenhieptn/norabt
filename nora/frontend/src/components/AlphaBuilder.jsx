import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Loading } from './common'
import { int, money } from '../lib/format'

/**
 * Dựng một alpha mới sinh ra thành lần chạy thật để backtest được.
 *
 * Alpha do phiên đào sinh ra chỉ nằm dưới dạng ảnh chụp trong bảng kết quả,
 * chưa có chiến lược lẫn lần chạy thật. Hộp này chép ảnh chụp đó ra thành
 * bản ghi mới — chỉ thêm, không sửa gì của hệ thống cũ.
 */
export default function AlphaBuilder({ rid, onCreated, onDone, onClose }) {
  const [d, setD] = useState(null)
  const [ds, setDs] = useState([])
  const [ten, setTen] = useState('')
  const [dataset, setDataset] = useState('')
  const [von, setVon] = useState('')
  const [err, setErr] = useState(null)
  const [ok, setOk] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setD(null); setErr(null); setOk(null)
    api.alphaChiTiet(rid).then((r) => {
      setD(r); setTen(r.ten_goi_y); setDataset(r.dataset_goi_y || '')
      setVon(r.von || 10000)
    }).catch(setErr)
    api.datasets().then((r) => setDs(r.rows)).catch(() => {})
  }, [rid])

  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const dung = async () => {
    setBusy(true); setErr(null)
    try {
      const r = await api.taoRunTuAlpha(rid, { name: ten, dataset, balance: von })
      setOk(r)
      onCreated && onCreated(r)   // chỉ làm mới danh sách; chuyển thẻ để người dùng tự bấm
    } catch (e) { setErr(e) } finally { setBusy(false) }
  }

  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose && onClose()}>
      <div className="modal" style={{ width: 'min(720px, 100%)' }} role="dialog" aria-modal="true">
        <div className="modal-h">
          <b>Dựng alpha thành lần chạy</b>
          <span className="note">chỉ thêm bản ghi mới, không sửa dữ liệu cũ</span>
          <button className="btn" onClick={onClose}>Đóng</button>
        </div>
        <div className="modal-b">
          {err && !d ? <div className="msg err">{String(err.message || err)}</div>
            : !d ? <Loading text="Đang đọc alpha…" />
            : (
              <>
                <div className="mau">
                  <span>
                    Alpha <span className="mono">{rid}</span> từ phiên{' '}
                    <span className="mono">{d.opt_id}</span> · số dư mô phỏng{' '}
                    <b className="up">{money(d.balance)}</b>
                  </span>
                </div>

                <div className="tuner-form">
                  <label>
                    <span>Tên lần chạy</span>
                    <input value={ten} onChange={(e) => setTen(e.target.value)} />
                  </label>
                  <label>
                    <span>Bộ dữ liệu nến</span>
                    <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
                      {!ds.includes(dataset) && dataset && <option value={dataset}>{dataset}</option>}
                      {ds.map((x) => <option key={x} value={x}>{x}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Vốn</span>
                    <input type="number" value={von} onChange={(e) => setVon(e.target.value)} />
                  </label>
                </div>

                <div className="tblwrap">
                  <table>
                    <tbody>
                      <tr><td>Luồng chiến lược</td>
                        <td className="mono" style={{ color: 'var(--amber)' }}>{d.luong.join(', ') || '—'}</td></tr>
                      <tr><td>Số coin sẽ tạo</td><td>{int(d.so_coin)}</td></tr>
                      <tr><td>Coin</td>
                        <td className="mono" style={{ fontSize: 11.5, whiteSpace: 'normal' }}>
                          {d.coin.join(', ')}{d.so_coin > d.coin.length ? ` … +${d.so_coin - d.coin.length}` : ''}
                        </td></tr>
                      <tr><td>Chốt lãi / cắt lỗ</td>
                        <td>{d.truong?.takeprofit ?? '—'} / {d.truong?.stoploss ?? '—'}</td></tr>
                      <tr><td>Đòn bẩy · thời hạn</td>
                        <td>{d.truong?.margin ?? '—'} · {d.truong?.timelife ?? '—'}</td></tr>
                      <tr><td>Kiểu ký quỹ</td><td>{d.margin_type}</td></tr>
                      <tr><td>Kiểu dữ liệu · khối</td>
                        <td className="mono">
                          {d.data_type || '(để rỗng như bản gốc)'} · {d.data_len} ngày
                        </td></tr>
                      <tr><td>Dồn lãi · vốn dự phòng</td>
                        <td>{d.compound ?? '—'} · {d.reserve ?? '—'}</td></tr>
                    </tbody>
                  </table>
                </div>

                <div className="tuner-f">
                  {d.run_id && !ok && (
                    <span style={{ color: 'var(--amber)' }}>
                      Alpha này đã được dựng thành lần chạy {d.run_id}
                    </span>
                  )}
                  {!ok && (
                    <button className="btn pri" onClick={dung} disabled={busy || !dataset}>
                      {busy ? 'Đang dựng…' : 'Dựng lần chạy'}
                    </button>
                  )}
                </div>

                {ok && (
                  <>
                    <div className="pre luu_y">
                      {ok.message} · bộ dữ liệu <span className="mono">{ok.dataset}</span>.
                      Lần chạy đang ở trạng thái chưa chạy, bấm ▶ là backtest được ngay.
                    </div>
                    <div className="tuner-f">
                      <button className="btn pri" onClick={() => onDone && onDone(ok)}>
                        Sang thẻ Lần chạy
                      </button>
                    </div>
                  </>
                )}
                {err && <div className="pre loi">{String(err.message || err)}</div>}
              </>
            )}
        </div>
      </div>
    </div>
  )
}

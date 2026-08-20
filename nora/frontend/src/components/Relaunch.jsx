import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { Loading } from './common'
import { int } from '../lib/format'

/**
 * Hộp chạy backtest — gộp cả chạy lần đầu lẫn chạy lại vào một chỗ.
 *
 *   Giữ nguyên  — chạy đúng chiến lược đang gắn. Nếu đã có kết quả cũ thì
 *                 lượt này ghi đè, nên phải nói rõ số lệnh sẽ mất.
 *   Đổi tham số — sinh chiến lược mới từ con số đã sửa rồi tạo lần chạy mới,
 *                 đi đúng đường sinh alpha; lần chạy cũ vẫn còn để đối chiếu.
 */
export default function Relaunch({ runId, canhBao = [], onClose, onXong }) {
  const [d, setD] = useState(null)
  const [ds, setDs] = useState([])
  const [kieu, setKieu] = useState('nguyen')
  const [sua, setSua] = useState({})          // "sid|đường dẫn" -> giá trị mới
  const [ten, setTen] = useState('')
  const [dataset, setDataset] = useState('')
  const [err, setErr] = useState(null)
  const [ok, setOk] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setD(null); setErr(null); setOk(null); setSua({})
    api.thamSo(runId).then((r) => {
      setD(r); setTen(`${r.run?.name || `Lần chạy ${runId}`}-v2`)
      setDataset(r.run?.dataset || '')
    }).catch(setErr)
    api.datasets().then((r) => setDs(r.rows)).catch(() => {})
  }, [runId])

  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const doi = useMemo(() => {
    const ra = []
    for (const [khoa, gt] of Object.entries(sua)) {
      const [sid, dd] = khoa.split('|')
      ra.push({ strategy: Number(sid), duong_dan: JSON.parse(dd), gia_tri: gt })
    }
    return ra
  }, [sua])

  const chay = async () => {
    if (kieu === 'nguyen' && d.so_lenh_cu > 0
      && !window.confirm(`Chạy lại với tham số hiện tại?\n\n${int(d.so_lenh_cu)} lệnh của kết quả cũ sẽ bị xoá.`)) return
    setBusy(true); setErr(null)
    try {
      const r = await api.chayLai(runId, kieu === 'nguyen'
        ? { kieu: 'nguyen' }
        : { kieu: 'doi_tham_so', thay_doi: doi, name: ten, dataset })
      setOk(r)
      onXong && onXong(r)
    } catch (e) { setErr(e) } finally { setBusy(false) }
  }

  const than = () => {
    if (err && !d) return <div className="msg err">{String(err.message || err)}</div>
    if (!d) return <Loading text="Đang đọc tham số chiến lược…" />

    return (
      <>
        <div className="mau">
          <div className="switch">
            <button className={kieu === 'nguyen' ? 'on' : ''} onClick={() => setKieu('nguyen')}>
              Giữ nguyên tham số
            </button>
            <button className={kieu === 'doi' ? 'on' : ''} onClick={() => setKieu('doi')}>
              Đổi tham số
            </button>
          </div>
          <span style={{ color: 'var(--ink-3)' }}>
            {kieu === 'nguyen'
              ? (d.so_lenh_cu > 0
                ? `chạy đè lên kết quả cũ (${int(d.so_lenh_cu)} lệnh sẽ bị xoá)`
                : 'chạy đúng chiến lược đang gắn')
              : 'sinh chiến lược mới và lần chạy mới, lần chạy cũ giữ nguyên'}
          </span>
        </div>

        {kieu === 'nguyen' && canhBao.map((t, k) => (
          <div key={k} className="pre luu_y">{t}</div>
        ))}

        {kieu === 'doi' && (
          <>
            <div className="tuner-form">
              <label>
                <span>Tên lần chạy mới</span>
                <input value={ten} onChange={(e) => setTen(e.target.value)} />
              </label>
              <label>
                <span>Bộ dữ liệu nến</span>
                <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
                  {!ds.includes(dataset) && dataset && <option value={dataset}>{dataset}</option>}
                  {ds.map((x) => <option key={x} value={x}>{x}</option>)}
                </select>
              </label>
            </div>

            {d.chien_luoc.map((cl) => (
              <div key={cl.id}>
                <div className="mau">
                  <span>
                    Chiến lược <span className="mono" style={{ color: 'var(--amber)' }}>{cl.id}</span>{' '}
                    {cl.name} · {cl.tham_so.length} con số chỉnh được
                  </span>
                </div>
                <div className="tblwrap">
                  <table className="chiso">
                    <thead>
                      <tr><th>Tham số</th><th className="n">Đang dùng</th><th>Giá trị mới</th></tr>
                    </thead>
                    <tbody>
                      {cl.tham_so.map((t, i) => {
                        const khoa = `${cl.id}|${JSON.stringify(t.duong_dan)}`
                        const truoc = i === 0 ? null : cl.tham_so[i - 1].nhom
                        return (
                          <React.Fragment key={khoa}>
                            {t.nhom !== truoc && (
                              <tr className="nhom"><td colSpan={3}>{t.nhom}</td></tr>
                            )}
                            <tr>
                              <td className="mono" style={{ fontSize: 12 }}>{t.nhan || '(giá trị)'}</td>
                              <td className="n mono" style={{ color: 'var(--ink-3)' }}>
                                {String(t.gia_tri)}
                              </td>
                              <td>
                                <input
                                  className="dai"
                                  style={{ maxWidth: 170,
                                    borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                  value={khoa in sua ? sua[khoa] : String(t.gia_tri)}
                                  onChange={(e) => {
                                    const v = e.target.value
                                    setSua((s) => {
                                      const n = { ...s }
                                      if (v === String(t.gia_tri)) delete n[khoa]
                                      else n[khoa] = v
                                      return n
                                    })
                                  }} />
                              </td>
                            </tr>
                          </React.Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </>
        )}

        <div className="tuner-f">
          {kieu === 'doi' && (
            <span>
              Đã đổi <b style={{ color: 'var(--amber)' }}>{doi.length}</b> con số
              {doi.length === 0 ? ' — chưa có gì để sinh chiến lược mới' : ''}
            </span>
          )}
          {!ok && (
            <button className="btn pri" onClick={chay}
              disabled={busy || (kieu === 'doi' && doi.length === 0)}>
              {busy ? 'Đang gửi…'
                : kieu === 'nguyen'
                  ? (d.so_lenh_cu > 0 ? '▶ Chạy lại y nguyên' : '▶ Chạy backtest')
                  : 'Sinh lần chạy mới'}
            </button>
          )}
        </div>

        {ok && (
          <>
            <div className="pre luu_y">
              {ok.kieu === 'nguyen'
                ? 'Đã gửi lệnh chạy. Thanh tiến độ sẽ tự cập nhật.'
                : `${ok.message}. Lần chạy cũ vẫn còn nguyên kết quả để đối chiếu.`}
            </div>
            <div className="tuner-f">
              <button className="btn pri" onClick={onClose}>Đóng</button>
            </div>
          </>
        )}
        {err && <div className="pre loi">{String(err.message || err)}</div>}
      </>
    )
  }

  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose && onClose()}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-h">
          <b>Chạy backtest {runId}</b>
          <span className="note">giữ nguyên tham số, hoặc đổi rồi sinh chiến lược mới</span>
          <button className="btn" onClick={onClose}>Đóng</button>
        </div>
        <div className="modal-b">{than()}</div>
      </div>
    </div>
  )
}

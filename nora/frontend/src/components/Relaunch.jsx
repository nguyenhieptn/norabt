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
  const [loc, setLoc] = useState('')
  const [nangCao, setNangCao] = useState(false)   // false: núm vặn dễ hiểu · true: đường dẫn thô

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

  /** Hệ số Keltner viết không dấu chấm trong tên cột: 0.5 -> "05", 1 -> "1". */
  const maHoa = (v, bien_doi) => (bien_doi === 'he_so' ? String(v).replace('.', '') : String(v))

  /** Ghép lại tên cột từ tên gốc và các phần đã đổi.
   *  Chu kỳ và hệ số nằm chung một tên (kup17_05) nên phải ghép chứ không thay
   *  cả chuỗi — vặn hai núm mà thay cả chuỗi thì núm sau đè mất núm trước. */
  const ghepCot = (goc, phan) => {
    let m = /^(k(?:up|lo))(\d+)(?:_(\d+))?$/.exec(goc)
    if (m) {
      const ky = phan.chu_ky !== undefined ? phan.chu_ky : m[2]
      const hs = phan.he_so !== undefined ? phan.he_so : m[3]
      return `${m[1]}${ky}` + (hs ? `_${hs}` : '')
    }
    m = /^((?:price_)?(?:ema|wma|sma|rsi|atr|macd)[a-z_]*?)(\d+)$/.exec(goc)
    if (m) return `${m[1]}${phan.chu_ky !== undefined ? phan.chu_ky : m[2]}`
    return goc
  }

  const doi = useMemo(() => {
    const ra = []
    // Cùng đường dẫn ở hai chiến lược là hai giá trị độc lập, không được gộp.
    const cot = new Map()          // "strategy|đường dẫn" -> { goc, phan, strategy, duong_dan }

    for (const [khoa, gt] of Object.entries(sua)) {
      if (!khoa.startsWith('nut|')) {
        const [sid, dd] = khoa.split('|')
        ra.push({ strategy: Number(sid), duong_dan: JSON.parse(dd), gia_tri: gt })
        continue
      }
      // một núm dễ hiểu có thể chạm nhiều chỗ cùng lúc
      const nut = JSON.parse(khoa.slice(4))
      for (const ap of nut.ap_dung) {
        if (ap.phan) {
          const duong_dan = JSON.stringify(ap.duong_dan)
          const k = `${nut.strategy}|${duong_dan}`
          const cu = cot.get(k) || {
            goc: ap.goc, phan: {}, strategy: nut.strategy, duong_dan: ap.duong_dan,
          }
          cu.phan[ap.phan] = maHoa(gt, nut.bien_doi)
          cot.set(k, cu)
        } else {
          ra.push({
            strategy: nut.strategy,
            duong_dan: ap.duong_dan,
            gia_tri: ap.mau.replace('{}', maHoa(gt, nut.bien_doi)),
          })
        }
      }
    }

    for (const v of cot.values()) {
      ra.push({ strategy: v.strategy, duong_dan: v.duong_dan, gia_tri: ghepCot(v.goc, v.phan) })
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

  // gõ về đúng giá trị cũ thì thôi không tính là đã đổi
  const dat = (khoa, v, cu) => setSua((s) => {
    const n = { ...s }
    if (v === String(cu)) delete n[khoa]
    else n[khoa] = v
    return n
  })

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

            <div className="bar-ctl" style={{ padding: '0 14px' }}>
              <div className="switch">
                <button className={!nangCao ? 'on' : ''}
                  onClick={() => { setNangCao(false); setSua({}) }}>Dễ hiểu</button>
                <button className={nangCao ? 'on' : ''}
                  onClick={() => { setNangCao(true); setSua({}) }}>Nâng cao</button>
              </div>
              <input placeholder="Lọc tham số… (keltner, ema, khung, chốt lãi…)"
                value={loc} onChange={(e) => setLoc(e.target.value)}
                style={{ minWidth: 260 }} />
              {loc && <button className="btn" onClick={() => setLoc('')}>Xoá lọc</button>}
              <span style={{ marginLeft: 'auto', fontSize: 12.5, color: 'var(--ink-3)' }}>
                {nangCao
                  ? 'từng đường dẫn trong chiến lược — sửa đúng một chỗ'
                  : 'gom theo khái niệm — một dòng sửa hết mọi chỗ đang dùng'}
              </span>
            </div>

            {d.chien_luoc.map((cl) => (
              <div key={cl.id}>
                <div className="mau">
                  <span>
                    Chiến lược <span className="mono" style={{ color: 'var(--amber)' }}>{cl.id}</span>{' '}
                    {cl.name} · {nangCao ? `${cl.tham_so.length} đường dẫn`
                      : `${(cl.de_hieu || []).length} núm vặn`}
                  </span>
                </div>

                {!nangCao && (
                  <div className="tblwrap">
                    <table className="chiso">
                      <thead>
                        <tr>
                          <th>Tham số</th><th>Ý nghĩa</th>
                          <th className="n">Đang dùng</th><th>Giá trị mới</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(cl.de_hieu || []).filter((t) => !loc
                          || `${t.nhan} ${t.y_nghia || ''} ${t.nhom}`.toLowerCase().includes(loc.toLowerCase())
                        ).map((t, i, mang) => {
                          const nut = { ...t, strategy: cl.id }
                          const khoa = 'nut|' + JSON.stringify(nut)
                          const truoc = i === 0 ? null : mang[i - 1].nhom
                          const cu = String(t.gia_tri)
                          const hien = khoa in sua ? sua[khoa] : cu
                          return (
                            <React.Fragment key={`${cl.id}|${t.ma}|${i}`}>
                              {t.nhom !== truoc && (
                                <tr className="nhom"><td colSpan={4}>{t.nhom}</td></tr>
                              )}
                              <tr>
                                <td>
                                  {t.nhan}
                                  {t.so_cho > 1 && (
                                    <span className="nhieu">sửa {t.so_cho} chỗ</span>
                                  )}
                                </td>
                                <td style={{ color: 'var(--ink-3)', fontSize: 12.5,
                                  whiteSpace: 'normal', maxWidth: 260 }}>{t.y_nghia || '—'}</td>
                                <td className="n mono" style={{ color: 'var(--ink-3)' }}>{cu}</td>
                                <td>
                                  {t.kieu === 'khung' ? (
                                    <select style={{ borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                      value={hien} onChange={(e) => dat(khoa, e.target.value, cu)}>
                                      {(t.chon || []).map((x) => <option key={x} value={x}>{x}</option>)}
                                    </select>
                                  ) : t.kieu === 'bool' ? (
                                    <select style={{ borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                      value={hien} onChange={(e) => dat(khoa, e.target.value, cu)}>
                                      <option value="false">tắt</option>
                                      <option value="true">bật</option>
                                    </select>
                                  ) : (
                                    <input className="dai" style={{ maxWidth: 150,
                                      borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                      value={hien} onChange={(e) => dat(khoa, e.target.value, cu)} />
                                  )}
                                </td>
                              </tr>
                            </React.Fragment>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {nangCao && (
                <div className="tblwrap">
                  <table className="chiso">
                    <thead>
                      <tr>
                        <th>Đường dẫn</th><th>Ý nghĩa</th>
                        <th className="n">Đang dùng</th><th>Giá trị mới</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cl.tham_so.filter((t) => !loc
                        || `${t.nhan} ${t.y_nghia || ''} ${t.nhom} ${t.gia_tri}`
                          .toLowerCase().includes(loc.toLowerCase())
                      ).map((t, i, mang) => {
                        const khoa = `${cl.id}|${JSON.stringify(t.duong_dan)}`
                        const truoc = i === 0 ? null : mang[i - 1].nhom
                        return (
                          <React.Fragment key={khoa}>
                            {t.nhom !== truoc && (
                              <tr className="nhom"><td colSpan={4}>{t.nhom}</td></tr>
                            )}
                            <tr>
                              <td className="mono" style={{ fontSize: 12 }}>{t.nhan || '(giá trị)'}</td>
                              <td style={{ color: 'var(--ink-3)', fontSize: 12.5 }}>
                                {t.y_nghia || '—'}
                              </td>
                              <td className="n mono" style={{ color: 'var(--ink-3)' }}>
                                {String(t.gia_tri)}
                              </td>
                              <td>
                                {t.kieu === 'khung' ? (
                                  <select
                                    style={{ borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                    value={khoa in sua ? sua[khoa] : String(t.gia_tri)}
                                    onChange={(e) => dat(khoa, e.target.value, t.gia_tri)}>
                                    {(t.chon || []).map((x) => <option key={x} value={x}>{x}</option>)}
                                  </select>
                                ) : (
                                  <input
                                    className="dai"
                                    style={{ maxWidth: 170,
                                      borderColor: khoa in sua ? 'var(--amber)' : undefined }}
                                    value={khoa in sua ? sua[khoa] : String(t.gia_tri)}
                                    onChange={(e) => dat(khoa, e.target.value, t.gia_tri)} />
                                )}
                              </td>
                            </tr>
                          </React.Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                )}
              </div>
            ))}
          </>
        )}

        <div className="tuner-f">
          {kieu === 'doi' && (
            <span>
              Đã đổi <b style={{ color: 'var(--amber)' }}>{Object.keys(sua).length}</b> tham số
            {doi.length !== Object.keys(sua).length ? ` (chạm vào ${doi.length} chỗ)` : ''}
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

import React, { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { Loading, ErrorBox, Block, Empty } from '../components/common'
import { int } from '../lib/format'

export default function Chart() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const [symbols, setSymbols] = useState([])
  const [presets, setPresets] = useState([])
  const [days, setDays] = useState([])
  const [symbol, setSymbol] = useState(sp.get('symbol') || '')
  const [day, setDay] = useState('')
  const [frame, setFrame] = useState('4h')
  const [preset, setPreset] = useState('keltner9')
  const [custom, setCustom] = useState('')
  const [url, setUrl] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.chartOptions(id).then((r) => {
      setSymbols(r.symbols)
      setPresets(r.presets)
      if (!symbol && r.symbols.length) setSymbol(r.symbols[0].symbol)
    }).catch(setErr)
  }, [id])

  useEffect(() => {
    if (!symbol) return
    setDays([]); setDay('')
    api.chartDays(id, symbol).then((r) => {
      setDays(r.rows)
      if (r.rows.length) setDay(r.rows[0].ngay)
    }).catch(() => {})
  }, [id, symbol])

  const gen = () => {
    if (!symbol || !day) return
    setBusy(true); setErr(null); setUrl(null)
    const ind = preset === 'custom' ? custom : preset
    api.makeChart(id, { symbol, day: String(day).replace(/-/g, '_'), frame, indicator: ind })
      .then((r) => setUrl(r.url))
      .catch(setErr)
      .finally(() => setBusy(false))
  }

  return (
    <>
      <p className="crumb">
        <Link to="/library/result">Các lần chạy</Link> · <Link to={`/library/result/${id}`}>mã {id}</Link> · biểu đồ
      </p>
      <div className="head">
        <h1>Biểu đồ nến và chỉ báo</h1>
        <p>Xem điểm vào lệnh có khớp tín hiệu chỉ báo hay không.</p>
      </div>

      <div className="bar-ctl">
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          {symbols.map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol} ({s.n} lệnh)</option>)}
        </select>

        <select value={day} onChange={(e) => setDay(e.target.value)}>
          {days.length === 0 && <option value="">— chọn ngày —</option>}
          {days.map((d) => (
            <option key={d.ngay} value={d.ngay}>{d.ngay} ({d.n} lệnh)</option>
          ))}
        </select>

        <select value={frame} onChange={(e) => setFrame(e.target.value)}>
          <option value="4h">Khung 4 giờ</option>
          <option value="1m">Khung 1 phút</option>
        </select>

        <select value={preset} onChange={(e) => setPreset(e.target.value)}>
          {presets.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          <option value="custom">Tự chọn cột…</option>
        </select>

        {preset === 'custom' && (
          <input
            placeholder="vd: price_ema9,kup9_1,klo9_1,atr"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            style={{ minWidth: 280 }}
          />
        )}

        <button className="btn pri" onClick={gen} disabled={busy || !symbol || !day}>
          {busy ? 'Đang vẽ…' : 'Vẽ biểu đồ'}
        </button>
      </div>

      {err && <ErrorBox error={err} />}

      <Block flush>
        {busy ? <Loading text="Đang sinh biểu đồ, việc này mất khoảng 20–60 giây…" />
          : url ? (
            <div className="chartbox">
              <iframe src={url} title="Biểu đồ backtest" />
            </div>
          ) : (
            <Empty text="Chọn coin, ngày và bộ chỉ báo rồi bấm Vẽ biểu đồ" />
          )}
      </Block>

      {url && (
        <p style={{ color: 'var(--ink-3)', fontSize: 12.5, lineHeight: 1.6 }}>
          🟢 <b>BUY</b> (tam giác xanh dưới đáy nến): Long Entry / DCA · 🔴 <b>SELL</b> (tam giác đỏ trên đỉnh nến): Short Entry / DCA · <i>Rê chuột vào điểm nến</i> để xem chi tiết giá khớp, thời gian, luồng và lý do vào lệnh.
        </p>
      )}


    </>
  )
}

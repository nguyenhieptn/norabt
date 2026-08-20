import React from 'react'

/** Có phải cấp số cộng không — để mở sẵn đúng kiểu nhập khi nạp bộ tham số cũ */
export function docDai(values) {
  const v = (values || []).map((x) => Number(String(x).trim())).filter((x) => !Number.isNaN(x))
  if (v.length !== (values || []).length || v.length === 0) return null
  if (v.length === 1) return { tu: v[0], den: v[0], buoc: 1 }
  const buoc = +(v[1] - v[0]).toFixed(10)
  if (buoc === 0) return null
  for (let i = 2; i < v.length; i++) {
    if (Math.abs((v[i] - v[i - 1]) - buoc) > 1e-9) return null
  }
  return { tu: v[0], den: v[v.length - 1], buoc }
}

/** Sinh danh sách giá trị từ một dải; chặn trần để một ô lỡ tay không đẻ ra triệu tổ hợp */
export function sinhDai({ tu, den, buoc }, tran = 500) {
  const a = Number(tu); const b = Number(den); let s = Number(buoc)
  if (Number.isNaN(a) || Number.isNaN(b) || Number.isNaN(s) || s === 0) return null
  if ((b - a) * s < 0) s = -s
  const n = Math.floor(Math.abs((b - a) / s)) + 1
  if (n > tran) return { qua_nhieu: n }
  // làm tròn theo số chữ số thập phân của bước, tránh 0.30000000000000004
  const le = (String(buoc).split('.')[1] || '').length
  const ra = []
  for (let i = 0; i < n; i++) ra.push(+(a + i * s).toFixed(le))
  return ra.map(String)
}

/**
 * Ô nhập dải quét: từ – đến – bước, hoặc liệt kê tay khi các mốc không đều.
 * Quét lưới vốn nghĩ theo dải, bắt gõ tay từng số là vừa mỏi vừa dễ sót.
 */
export default function DaiGiaTri({ values, onChange, tot_nhat }) {
  const dai = docDai(values)
  const [kieu, setKieu] = React.useState(dai ? 'dai' : 'liet')
  const [d, setD] = React.useState(dai || { tu: '', den: '', buoc: '' })

  React.useEffect(() => {
    const x = docDai(values)
    if (x) setD(x)
  }, [values && values.join(',')])

  const ap = (moi) => {
    setD(moi)
    const ra = sinhDai(moi)
    if (Array.isArray(ra)) onChange(ra)
  }

  const ket = sinhDai(d)
  const so_nhanh = Array.isArray(ket) ? ket.length : (ket && ket.qua_nhieu) || 0

  return (
    <div className="dai-o">
      <div className="switch nho">
        <button className={kieu === 'dai' ? 'on' : ''} onClick={() => setKieu('dai')}>Dải</button>
        <button className={kieu === 'liet' ? 'on' : ''} onClick={() => setKieu('liet')}>Liệt kê</button>
      </div>

      {kieu === 'dai' ? (
        <>
          <label>từ<input value={d.tu} onChange={(e) => ap({ ...d, tu: e.target.value })} /></label>
          <label>đến<input value={d.den} onChange={(e) => ap({ ...d, den: e.target.value })} /></label>
          <label>bước<input value={d.buoc} onChange={(e) => ap({ ...d, buoc: e.target.value })} /></label>
          {ket && ket.qua_nhieu ? (
            <span className="canh">{ket.qua_nhieu} giá trị — quá nhiều, nới bước lên</span>
          ) : (
            <span className="xem">
              {so_nhanh ? `${so_nhanh} giá trị: ${ket.slice(0, 4).join(', ')}${ket.length > 4 ? '…' : ''}` : ''}
            </span>
          )}
        </>
      ) : (
        <input className="dai" value={(values || []).join(', ')}
          onChange={(e) => onChange(e.target.value.split(',').map((x) => x.trim()))} />
      )}

      {tot_nhat !== undefined && tot_nhat !== null && (
        <button className="goiy" title="Chỉ quét đúng giá trị đang tốt nhất"
          onClick={() => { setKieu('liet'); onChange([String(tot_nhat)]) }}>
          tốt nhất {tot_nhat}
        </button>
      )}
    </div>
  )
}

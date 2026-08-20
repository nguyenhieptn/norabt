const vn = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 })
const vn0 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 })

export const num = (v, d = 2) =>
  v === null || v === undefined || v === '' ? '—'
    : (d === 0 ? vn0 : vn).format(Number(v))

export const money = (v) => {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return (n > 0 ? '+' : '') + vn.format(n)
}

export const pct = (v) => (v === null || v === undefined ? '—' : `${vn.format(Number(v))}%`)

export const int = (v) => (v === null || v === undefined ? '—' : vn0.format(Number(v)))

export const dur = (hours) => {
  if (hours === null || hours === undefined) return '—'
  const h = Number(hours)
  if (h < 1) return `${Math.round(h * 60)} phút`
  if (h < 48) return `${vn.format(h)} giờ`
  return `${vn.format(h / 24)} ngày`
}

export const dt = (ms) => {
  if (!ms) return '—'
  const d = new Date(Number(ms))
  return d.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export const dateOnly = (ms) => {
  if (!ms) return '—'
  return new Date(Number(ms)).toLocaleDateString('vi-VN')
}

/** Nhận diện loại chiến lược từ nội dung JSON */
export function strategyKind(content) {
  if (!content) return { key: 'unknown', label: 'Chưa rõ' }
  const s = typeof content === 'string' ? content : JSON.stringify(content)
  if (/BUSD_\d+_\d+/.test(s)) return { key: 'busd', label: 'Dòng tiền' }
  if (/"kup\d|"klo\d/.test(s)) return { key: 'band', label: 'Biên độ' }
  if (/price_wma|rsi_wma45|price_ema9/.test(s)) return { key: 'trend', label: 'Xu hướng' }
  if (/rsi_wma|matched_price/.test(s)) return { key: 'dca', label: 'DCA' }
  return { key: 'other', label: 'Khác' }
}

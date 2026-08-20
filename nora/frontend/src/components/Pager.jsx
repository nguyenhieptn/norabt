import React from 'react'
import { int } from '../lib/format'

/** Phân trang dùng chung — mặc định 20 dòng mỗi trang */
export const PAGE_SIZE = 20

export function usePaged(rows, size = PAGE_SIZE) {
  const [page, setPage] = React.useState(1)
  React.useEffect(() => { setPage(1) }, [rows])
  const total = rows ? rows.length : 0
  const pages = Math.max(1, Math.ceil(total / size))
  const cur = Math.min(page, pages)
  const slice = rows ? rows.slice((cur - 1) * size, cur * size) : []
  return { page: cur, pages, total, slice, setPage, size }
}

export function Pager({ page, pages, total, setPage, unit = 'dòng' }) {
  if (total === 0) return null
  return (
    <div className="pager">
      <button className="btn" disabled={page <= 1} onClick={() => setPage(1)}>«</button>
      <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Trước</button>
      <span>Trang {page} / {pages}</span>
      <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Sau →</button>
      <button className="btn" disabled={page >= pages} onClick={() => setPage(pages)}>»</button>
      <span className="sp">{int(total)} {unit}</span>
    </div>
  )
}

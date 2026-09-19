import React from "react";

export const PAGE_SIZE = 10;

export function usePaged(rows, initialSize = PAGE_SIZE) {
  const [size, setSize] = React.useState(initialSize);
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    setPage(1);
  }, [rows, size]);

  const total = rows ? rows.length : 0;
  const pages = Math.max(1, Math.ceil(total / size));
  const cur = Math.min(Math.max(1, page), pages);
  const slice = rows ? rows.slice((cur - 1) * size, cur * size) : [];

  return { page: cur, pages, total, slice, setPage, size, setSize };
}

export function Pager({ page, pages, total, setPage, size, setSize, unit = "bot" }) {
  if (total === 0) return null;
  const start = (page - 1) * size + 1;
  const end = Math.min(page * size, total);

  return (
    <div className="pager">
      <div className="pager-controls">
        <button
          type="button"
          className="btn"
          disabled={page <= 1}
          onClick={() => setPage(1)}
          title="First page"
        >
          «
        </button>
        <button
          type="button"
          className="btn"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
        >
          ← Prev
        </button>
        <span className="pager-current">
          Page <b>{page}</b> / <b>{pages}</b>
        </span>
        <button
          type="button"
          className="btn"
          disabled={page >= pages}
          onClick={() => setPage(page + 1)}
        >
          Next →
        </button>
        <button
          type="button"
          className="btn"
          disabled={page >= pages}
          onClick={() => setPage(pages)}
          title="Last page"
        >
          »
        </button>
      </div>

      {setSize && (
        <div className="pager-size-selector">
          <span>Show</span>
          <select
            value={size}
            onChange={(e) => setSize(Number(e.target.value))}
            aria-label="Rows per page"
          >
            <option value={10}>10 rows</option>
            <option value={20}>20 rows</option>
            <option value={50}>50 rows</option>
          </select>
        </div>
      )}

      <span className="sp">
        Showing <b>{start}</b> – <b>{end}</b> of <b>{total}</b> {unit}
      </span>
    </div>
  );
}

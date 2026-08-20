const BASE = ''

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    let msg = `Lỗi ${res.status}`
    try {
      const j = await res.json()
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch (e) { /* giữ thông báo mặc định */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  node: () => req('/api/node'),
  preflight: (id) => req(`/api/runs/${id}/preflight`),
  start: (id) => req(`/api/runs/${id}/start`, { method: 'POST' }),
  stop: (id) => req(`/api/runs/${id}/stop`, { method: 'POST' }),
  log: (id, tail = 120) => req(`/api/runs/${id}/log?tail=${tail}`),
  progress: (id) => req(`/api/runs/${id}/progress`),
  thamSo: (id) => req(`/api/runs/${id}/tham-so`),
  chayLai: (id, body) => req(`/api/runs/${id}/chay-lai`, {
    method: 'POST', body: JSON.stringify(body || {}),
  }),
  dashboard: () => req('/api/dashboard'),
  metrics: (id) => req(`/api/runs/${id}/metrics`),
  metricsBrief: (id) => req(`/api/runs/${id}/metrics-brief`),
  optimizations: (p = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v))
    return req(`/api/miner/optimizations?${qs}`)
  },
  optimization: (id) => req(`/api/miner/optimizations/${id}`),
  optimizationParams: (id) => req(`/api/miner/optimizations/${id}/params`),
  mauThamSo: (p = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v))
    return req(`/api/miner/mau?${qs}`)
  },
  createOptimization: (body) => req('/api/miner/optimizations', {
    method: 'POST', body: JSON.stringify(body),
  }),
  optProgress: (id) => req(`/api/miner/optimizations/${id}/progress`),
  optStart: (id) => req(`/api/miner/optimizations/${id}/start`, { method: 'POST' }),
  optStop: (id) => req(`/api/miner/optimizations/${id}/stop`, { method: 'POST' }),
  optLog: (id, tail = 120) => req(`/api/miner/optimizations/${id}/log?tail=${tail}`),
  optimizationResults: (id, p = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v))
    return req(`/api/miner/optimizations/${id}/results?${qs}`)
  },
  groups: () => req('/api/groups'),
  datasets: () => req('/api/datasets'),
  alphaMoi: (p = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v))
    return req(`/api/base/alpha-moi?${qs}`)
  },
  alphaChiTiet: (rid) => req(`/api/base/alpha-moi/${rid}`),
  taoRunTuAlpha: (rid, body) => req(`/api/base/alpha-moi/${rid}/tao-run`, {
    method: 'POST', body: JSON.stringify(body || {}),
  }),
  runs: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v))
    return req(`/api/runs?${qs}`)
  },
  run: (id) => req(`/api/runs/${id}`),
  overview: (id) => req(`/api/runs/${id}/overview`),
  byFlow: (id) => req(`/api/runs/${id}/by-flow`),
  behavior: (id) => req(`/api/runs/${id}/behavior`),
  bySymbol: (id) => req(`/api/runs/${id}/by-symbol`),
  timeline: (id) => req(`/api/runs/${id}/timeline`),
  equity: (id, points = 1200) => req(`/api/runs/${id}/equity?points=${points}`),
  insights: (id) => req(`/api/runs/${id}/insights`),
  trades: (id, p = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v !== null && v !== ''))
    return req(`/api/runs/${id}/trades?${qs}`)
  },
  strategies: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v))
    return req(`/api/strategies?${qs}`)
  },
  strategy: (id) => req(`/api/strategies/${id}`),
  strategyGroups: () => req('/api/strategy-groups'),
  chartOptions: (id) => req(`/api/runs/${id}/chart-options`),
  chartDays: (id, symbol) => req(`/api/runs/${id}/chart-days?symbol=${symbol}`),
  makeChart: (id, p) => {
    const qs = new URLSearchParams(p)
    return req(`/api/runs/${id}/chart?${qs}`, { method: 'POST' })
  },
}

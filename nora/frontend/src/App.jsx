import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Scan from './pages/Scan'
import Analysis from './pages/Analysis'
import DiscoveryDetail from './pages/DiscoveryDetail'
import MethodComparison from './pages/MethodComparison'
import AssetResearchDetail from './pages/AssetResearchDetail'
import Alpha from './pages/Alpha'
import Studio from './pages/Studio'
import StrategyDetail from './pages/StrategyDetail'
import Base from './pages/Base'
import Wfa from './pages/Wfa'
import MonteCarlo from './pages/MonteCarlo'
import Results from './pages/Results'
import RunDetail from './pages/RunDetail'
import Trades from './pages/Trades'
import Chart from './pages/Chart'
import ThemeToggle from './components/ThemeToggle'

const cls = ({ isActive }) => (isActive ? 'on' : '')

function AppLayout() {
  const location = useLocation()
  const isResearchMode = location.pathname.startsWith('/research/analysis') || location.pathname === '/analysis'

  // State cho việc mở / ẩn các tab con (Collapsible Accordion Tabs)
  const [openScanTab, setOpenScanTab] = useState(true)
  const [openResearchTab, setOpenResearchTab] = useState(true)

  return (
    <div className="app">
      <aside className="side" style={{ width: 236, flex: '0 0 236px' }}>
        <div className="brand">
          <b>Nora</b>
          <span>Research &amp; Backtest</span>
        </div>

        <nav className="nav" style={{ flex: 1, overflowY: 'auto' }}>
          {/* TAB 1 LỚN: SCAN (Chứa toàn bộ các tab nội dung của Backtest) */}
          <div className="accordion-tab-group">
            <div
              className={`accordion-tab-header ${!isResearchMode ? 'active-group' : ''}`}
              onClick={() => setOpenScanTab(!openScanTab)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>🛰️</span>
                <b>TAB SCAN</b>
              </div>
              <span className="accordion-arrow">{openScanTab ? '▾' : '▸'}</span>
            </div>

            {openScanTab && (
              <div className="accordion-tab-content">
                <NavLink to="/dashboard" className={cls}>📊 Tổng quan</NavLink>
                <NavLink to="/library/alpha" className={cls}>🧬 Alpha · Chiến lược</NavLink>
                <NavLink to="/library/base" className={cls}>⚙️ Base · Cấu hình chạy</NavLink>
                <NavLink to="/library/wfa" className={cls}>🔄 Walk-Forward (WFA)</NavLink>
                <NavLink to="/library/monte-carlo" className={cls}>🎲 Mô phỏng Monte Carlo</NavLink>
                <NavLink to="/library/result" className={cls}>📈 Result · Kết quả</NavLink>
              </div>
            )}
          </div>

          {/* TAB 2 LỚN: NGHIÊN CỨU (Bàn phân tích thị trường) */}
          <div className="accordion-tab-group" style={{ marginTop: 14 }}>
            <div
              className={`accordion-tab-header ${isResearchMode ? 'active-group' : ''}`}
              onClick={() => setOpenResearchTab(!openResearchTab)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>🔬</span>
                <b>TAB NGHIÊN CỨU</b>
              </div>
              <span className="accordion-arrow">{openResearchTab ? '▾' : '▸'}</span>
            </div>

            {openResearchTab && (
              <div className="accordion-tab-content">
                <NavLink to="/research/analysis" className={cls}>
                  🛰️ Market Research Command Center
                </NavLink>
              </div>
            )}
          </div>
        </nav>

        <ThemeToggle />
        <div className="side-foot" style={{ marginTop: 12 }}>DEX Research Platform</div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/research/analysis" element={<Analysis />} />
          <Route path="/research/analysis/discovery/:discoveryId" element={<DiscoveryDetail />} />
          <Route path="/research/analysis/methods" element={<MethodComparison />} />
          <Route path="/research/analysis/asset/:symbol" element={<AssetResearchDetail />} />
          <Route path="/library/alpha" element={<Alpha />} />
          <Route path="/library/alpha/:id" element={<StrategyDetail />} />
          <Route path="/library/base" element={<Base />} />
          <Route path="/library/wfa" element={<Wfa />} />
          <Route path="/library/monte-carlo" element={<MonteCarlo />} />
          <Route path="/library/result" element={<Results />} />
          <Route path="/library/result/:id" element={<RunDetail />} />
          <Route path="/library/result/:id/trades" element={<Trades />} />
          <Route path="/library/result/:id/chart" element={<Chart />} />

          {/* đường dẫn chuyển hướng tương thích */}
          <Route path="/scan" element={<Navigate to="/dashboard" replace />} />
          <Route path="/analysis" element={<Navigate to="/research/analysis" replace />} />
          <Route path="/studio" element={<Navigate to="/library/alpha?tab=builder" replace />} />
          <Route path="/wfa" element={<Navigate to="/library/wfa" replace />} />
          <Route path="/monte-carlo" element={<Navigate to="/library/monte-carlo" replace />} />
          <Route path="/runs" element={<Navigate to="/library/result" replace />} />
          <Route path="/strategies" element={<Navigate to="/library/alpha" replace />} />
          <Route path="/miner" element={<Navigate to="/library/alpha?tab=dao" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}


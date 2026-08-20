import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Alpha from './pages/Alpha'
import StrategyDetail from './pages/StrategyDetail'
import Base from './pages/Base'
import Results from './pages/Results'
import RunDetail from './pages/RunDetail'
import Trades from './pages/Trades'
import Chart from './pages/Chart'
import ThemeToggle from './components/ThemeToggle'

const cls = ({ isActive }) => (isActive ? 'on' : '')

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <aside className="side">
          <div className="brand">
            <b>Nora</b>
            <span>Backtest</span>
          </div>

          <nav className="nav">
            <NavLink to="/dashboard" className={cls}>Tổng quan</NavLink>

            <div className="nav-group">Thư viện</div>
            <NavLink to="/library/alpha" className={cls}>Alpha · chiến lược &amp; đào</NavLink>
            <NavLink to="/library/base" className={cls}>Base · cấu hình chạy</NavLink>
            <NavLink to="/library/result" className={cls}>Result · kết quả</NavLink>
          </nav>

          <ThemeToggle />
          <div className="side-foot" style={{ marginTop: 12 }}>dữ liệu từ hệ thống hiện tại</div>
        </aside>

        <main className="main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/library/alpha" element={<Alpha />} />
            <Route path="/library/alpha/:id" element={<StrategyDetail />} />
            <Route path="/library/base" element={<Base />} />
            <Route path="/library/result" element={<Results />} />
            <Route path="/library/result/:id" element={<RunDetail />} />
            <Route path="/library/result/:id/trades" element={<Trades />} />
            <Route path="/library/result/:id/chart" element={<Chart />} />

            {/* đường dẫn cũ vẫn dùng được */}
            <Route path="/runs" element={<Navigate to="/library/result" replace />} />
            <Route path="/strategies" element={<Navigate to="/library/alpha" replace />} />
            <Route path="/miner" element={<Navigate to="/library/alpha?tab=dao" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

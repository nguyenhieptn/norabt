import React from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Alpha from './pages/Alpha'

const loi = []
window.addEventListener('error', (e) => loi.push(String(e.message)))
class Bat extends React.Component {
  componentDidCatch(e) { loi.push('React: ' + e.message) }
  static getDerivedStateFromError() { return { h: true } }
  render() { return this.state?.h ? null : this.props.children }
}
const cho = (ms) => new Promise((r) => setTimeout(r, ms))
const nut = (t, g = document) => [...g.querySelectorAll('button')].find((b) => b.textContent.includes(t))
const set = (el, v) => {
  Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v)
  el.dispatchEvent(new window.Event('input', { bubbles: true }))
}

createRoot(document.getElementById('goc')).render(
  <Bat><MemoryRouter initialEntries={['/library/alpha?tab=dao']}>
    <Routes><Route path="/library/alpha" element={<Alpha />} /></Routes>
  </MemoryRouter></Bat>)

;(async () => {
  await cho(6000)
  nut('Tạo phiên đào mới').click(); await cho(6000)
  const m = document.querySelector('.modal')
  const nghia = (i) => m.querySelectorAll('tbody tr')[i].children[0].querySelector('div').textContent.trim()
  const oDai = (i) => m.querySelectorAll('tbody tr')[i].querySelectorAll('.dai-o label input')

  console.log('dòng 1 ban đầu :', nghia(0))
  const o = oDai(0)
  set(o[0], '102'); set(o[1], '110'); set(o[2], '2'); await cho(800)
  console.log('quét 102→110 b2:', nghia(0))
  console.log('dòng 2 ban đầu :', nghia(1))
  const o2 = oDai(1)
  set(o2[0], '-3'); set(o2[1], '-9'); set(o2[2], '3'); await cho(800)
  console.log('quét -3→-9 b3  :', nghia(1))
  console.log('LỖI:', loi.length ? loi.slice(0, 3) : 'không có')
  process.exit(0)
})()

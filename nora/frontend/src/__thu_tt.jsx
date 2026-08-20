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
const T = (g = document) => g.textContent
const nut = (t, g = document) => [...g.querySelectorAll('button')].find((b) => b.textContent.includes(t))
const set = (el, v) => {
  const proto = el.tagName === 'SELECT' ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v)
  el.dispatchEvent(new window.Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
}

createRoot(document.getElementById('goc')).render(
  <Bat><MemoryRouter initialEntries={['/library/alpha?tab=dao']}>
    <Routes><Route path="/library/alpha" element={<Alpha />} /></Routes>
  </MemoryRouter></Bat>)

;(async () => {
  await cho(6000)
  nut('Tạo phiên đào mới').click(); await cho(6000)
  const m = document.querySelector('.modal')
  const bang = () => m.querySelectorAll('table')[m.querySelectorAll('table').length - 1]
  const hang = () => [...bang().querySelectorAll('tbody tr')]
  const ten = () => hang().map((r) => r.querySelector('input.ten')?.value)

  console.log('1. Thứ tự ban đầu:', ten().slice(0, 6).join(' · '))
  console.log('2. Có nút ↑ ↓ ⧉ ×:',
    ['↑', '↓', '⧉', '×'].map((k) => (nut(k, hang()[1]) ? '✓' : '✗') + k).join(' '))

  // đẩy công thức match_price_4h (dòng 5) lên trên input4h (dòng 1)
  for (let i = 0; i < 4; i++) { nut('↑', hang()[4 - i]).click(); await cho(350) }
  console.log('3. Sau khi kéo công thức lên đầu:', ten().slice(0, 3).join(' · '))
  console.log('4. Báo sai thứ tự:', /khai phía dưới — bấm ↑/.test(T(m)) ? '✓' : '✗',
    '| nút tạo khoá:', nut('Tạo phiên đào', m)?.disabled ? '✓' : '✗')

  for (let i = 0; i < 4; i++) { nut('↓', hang()[i]).click(); await cho(350) }
  console.log('5. Kéo trả về:', ten().slice(0, 3).join(' · '),
    '| hết báo:', /khai phía dưới/.test(T(m)) ? '✗' : '✓',
    '| nút tạo:', nut('Tạo phiên đào', m)?.disabled ? '✗ khoá' : '✓ mở')
  console.log('LỖI:', loi.length ? loi.slice(0, 3) : 'không có')
  process.exit(0)
})()

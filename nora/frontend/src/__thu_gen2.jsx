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
  console.log('1. Chưa chọn lần chạy → có nhắc:', /Chọn lần chạy gốc ở trên để hiện các chỉ báo/.test(T(m)) ? '✓' : '✗')
  set(m.querySelector('.tuner-form select'), '3379'); await cho(4000)
  console.log('2. Sau khi chọn 3379 → khối chỉ báo:', /Chỉ báo trong chiến lược/.test(T(m)) ? '✓' : '✗')

  const bangCB = m.querySelectorAll('table')[0]
  const hang = [...bangCB.querySelectorAll('tbody tr')]
  console.log('3. Dải cho phép ghi kèm:')
  for (const r of hang) console.log('     ', r.children[3].textContent.replace(/\s+/g, ' ').trim().slice(0, 74))
  console.log('4. RSI/ATR bị khoá tick:',
    hang.filter((r) => r.querySelector('input[type=checkbox]').disabled).length, 'dòng')

  hang[0].querySelector('input[type=checkbox]').click(); await cho(900)
  const o = [...hang[0].querySelectorAll('.dai-o label input')]
  set(o[0], '13'); set(o[1], '35'); set(o[2], '2'); await cho(900)
  console.log('5. Gõ tới 35 (ngoài dải):',
    /không có trong bộ dữ liệu/.test(T(m)) ? '✓ báo đỏ' : '✗',
    '| nút tạo bị khoá:', nut('Tạo phiên đào', m)?.disabled ? '✓' : '✗')
  set(o[1], '25'); await cho(900)
  console.log('6. Sửa về 25:', /không có trong bộ dữ liệu/.test(T(m)) ? '✗ vẫn báo' : '✓ hết báo',
    '| nút tạo:', nut('Tạo phiên đào', m)?.disabled ? '✗ vẫn khoá' : '✓ mở')
  console.log('7. Nút chép #tên#:', m.querySelectorAll('button.goiy[title*="Chép"]').length, 'nút')
  console.log('LỖI:', loi.length ? loi.slice(0, 3) : 'không có')
  process.exit(0)
})()

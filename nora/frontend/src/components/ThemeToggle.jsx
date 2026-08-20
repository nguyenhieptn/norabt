import React, { useEffect, useState } from 'react'

const KEY = 'nora-theme'

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem(KEY) || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(KEY, theme)
  }, [theme])

  const dark = theme === 'dark'
  return (
    <button
      className="theme-btn"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      aria-label={dark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
    >
      <span aria-hidden="true">{dark ? '☀' : '☾'}</span>
      {dark ? 'Chế độ sáng' : 'Chế độ tối'}
    </button>
  )
}

import { useRef } from 'react'

export default function StudioEditor({
  code = '',
  onChange = () => {},
  onSimulate,
  disabled = false,
  readOnly = false,
  placeholder = 'JSON AST preview...',
}) {
  const textareaRef = useRef(null)
  const lineNumbersRef = useRef(null)

  const lines = String(code || '').split('\n')
  const lineCount = Math.max(lines.length, 1)

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (onSimulate && !disabled) onSimulate()
      return
    }

    if (readOnly || disabled || e.key !== 'Tab') return

    e.preventDefault()
    const start = e.target.selectionStart
    const end = e.target.selectionEnd
    const val = e.target.value
    const newVal = val.substring(0, start) + '    ' + val.substring(end)
    onChange(newVal)

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 4
      }
    }, 0)
  }

  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop
    }
  }

  return (
    <div className="studio-editor-container">
      <div className="studio-editor-gutter" ref={lineNumbersRef}>
        {Array.from({ length: lineCount }).map((_, i) => (
          <div key={i} className="studio-line-number">
            {i + 1}
          </div>
        ))}
      </div>
      <textarea
        ref={textareaRef}
        className="studio-editor-textarea"
        value={code}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onScroll={handleScroll}
        spellCheck="false"
        autoCapitalize="off"
        autoComplete="off"
        placeholder={placeholder}
        disabled={disabled}
        readOnly={readOnly}
      />
    </div>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'

function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}${path}`
}

/**
 * Theo dõi tiến độ một lần chạy qua WebSocket.
 *
 * Máy chủ đóng kết nối ngay khi lần chạy đã kết thúc (gói cuối có final = true),
 * nên sau khi bấm nút chạy phải gọi refresh() để mở lại kết nối mới —
 * nếu không thì thanh tiến độ sẽ đứng im ở kết quả cũ.
 * Mất mạng thì tự nối lại ba lần, quá đó mới lùi về hỏi định kỳ.
 */
export function useRunProgress(runId, enabled = true) {
  const [data, setData] = useState(null)
  const [live, setLive] = useState(false)
  const [lan, setLan] = useState(0)          // tăng lên để mở lại kết nối

  const refresh = useCallback(() => setLan((n) => n + 1), [])

  const ws = useRef(null)
  const poll = useRef(null)
  const retry = useRef(0)
  const xong = useRef(false)                 // đã nhận gói cuối, thôi nối lại
  const huy = useRef(false)                  // rời màn hình

  useEffect(() => {
    if (!runId || !enabled) return
    huy.current = false
    xong.current = false
    retry.current = 0
    setLive(false)

    const startPolling = () => {
      if (poll.current) return
      const tick = () => fetch(`/api/runs/${runId}/progress`)
        .then((r) => r.json()).then((m) => { if (!huy.current) setData(m) })
        .catch(() => {})
      tick()
      poll.current = setInterval(tick, 5000)
    }
    const stopPolling = () => { clearInterval(poll.current); poll.current = null }

    const connect = () => {
      if (huy.current || xong.current) return
      let sock
      try {
        sock = new WebSocket(wsUrl(`/ws/runs/${runId}/progress`))
      } catch (e) {
        startPolling()
        return
      }
      ws.current = sock

      sock.onopen = () => { if (!huy.current) { setLive(true); retry.current = 0; stopPolling() } }
      sock.onmessage = (ev) => {
        if (huy.current) return
        try {
          const m = JSON.parse(ev.data)
          if (m.error) return
          setData(m)
          if (m.final) xong.current = true
        } catch (e) { /* bỏ qua gói hỏng */ }
      }
      sock.onclose = () => {
        if (huy.current) return
        setLive(false)
        if (xong.current) return                    // kết thúc bình thường
        retry.current += 1
        if (retry.current <= 3) setTimeout(connect, 1500 * retry.current)
        else startPolling()                          // đành hỏi định kỳ
      }
      sock.onerror = () => { try { sock.close() } catch (e) {} }
    }

    connect()
    return () => {
      huy.current = true
      stopPolling()
      try { ws.current?.close() } catch (e) {}
    }
  }, [runId, enabled, lan])

  return { progress: data, live, refresh }
}

/** Theo dõi log chạy theo thời gian thực (chỉ mở khi đang chạy) */
export function useRunLog(runId, enabled) {
  const [log, setLog] = useState(null)

  useEffect(() => {
    if (!runId || !enabled) return
    let sock
    let huy = false
    try {
      sock = new WebSocket(wsUrl(`/ws/runs/${runId}/log?tail=80`))
    } catch (e) { return }
    sock.onmessage = (ev) => {
      if (huy) return
      try {
        const m = JSON.parse(ev.data)
        if (m.log) setLog(m.log)
      } catch (e) { /* bỏ qua */ }
    }
    return () => { huy = true; try { sock.close() } catch (e) {} }
  }, [runId, enabled])

  return log
}

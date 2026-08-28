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
  const retryTimer = useRef(null)
  const xong = useRef(false)                 // đã nhận gói cuối, thôi nối lại

  useEffect(() => {
    if (!runId || !enabled) return undefined
    let huy = false                            // riêng cho đúng lượt effect này
    let sock = null
    let pollTimer = null
    let retryTimerId = null
    let retryCount = 0
    let daXong = false

    xong.current = false
    retry.current = 0
    setData(null)
    clearTimeout(retryTimer.current)
    retryTimer.current = null
    setLive(false)

    const stopPolling = () => {
      if (poll.current === pollTimer) poll.current = null
      clearInterval(pollTimer)
      pollTimer = null
    }
    const startPolling = () => {
      if (huy || pollTimer) return
      const tick = () => fetch(`/api/runs/${runId}/progress`)
        .then((r) => r.json()).then((m) => { if (!huy) setData(m) })
        .catch(() => {})
      tick()
      pollTimer = setInterval(tick, 5000)
      poll.current = pollTimer
    }
    const clearRetry = () => {
      clearTimeout(retryTimerId)
      retryTimerId = null
      clearTimeout(retryTimer.current)
      retryTimer.current = null
    }

    const connect = () => {
      clearRetry()
      if (huy || daXong) return
      try {
        sock = new WebSocket(wsUrl(`/ws/runs/${runId}/progress`))
      } catch (e) {
        startPolling()
        return
      }
      ws.current = sock

      sock.onopen = () => {
        if (huy || sock !== ws.current) return
        setLive(true)
        retryCount = 0
        retry.current = 0
        stopPolling()
      }
      sock.onmessage = (ev) => {
        if (huy || sock !== ws.current) return
        try {
          const m = JSON.parse(ev.data)
          if (m.error) return
          setData(m)
          if (m.final) {
            daXong = true
            xong.current = true
          }
        } catch (e) { /* bỏ qua gói hỏng */ }
      }
      sock.onclose = () => {
        if (huy || sock !== ws.current) return
        setLive(false)
        if (daXong) return                         // kết thúc bình thường
        retryCount += 1
        retry.current = retryCount
        if (retryCount <= 3) {
          retryTimerId = setTimeout(connect, 1500 * retryCount)
          retryTimer.current = retryTimerId
        } else startPolling()                      // đành hỏi định kỳ
      }
      sock.onerror = () => { try { sock.close() } catch (e) {} }
    }

    connect()
    return () => {
      huy = true
      clearRetry()
      stopPolling()
      if (ws.current === sock) ws.current = null
      try { sock?.close() } catch (e) {}
    }
  }, [runId, enabled, lan])

  return { progress: data, live, refresh }
}

/**
 * Theo dõi log chạy theo thời gian thực (chỉ mở khi đang chạy).
 *
 * Lấy một bản qua HTTP ngay lúc bật để có cái hiện liền, rồi mới mở WebSocket
 * cho các dòng tiếp theo — chờ gói đầu của WebSocket thì ô log trống hàng chục
 * giây, mà mất kết nối là trống luôn tới hết lượt chạy.
 */
export function useRunLog(runId, enabled) {
  const [log, setLog] = useState(null)

  useEffect(() => {
    if (!runId || !enabled) return undefined
    let huy = false
    let sock = null
    let hen = null
    let lan = 0

    const lay_ngay = () => fetch(`/api/runs/${runId}/log?tail=80`)
      .then((r) => r.json())
      .then((r) => { if (!huy && r && r.data) setLog(r.data) })
      .catch(() => {})

    const noi = () => {
      if (huy) return
      try {
        sock = new WebSocket(wsUrl(`/ws/runs/${runId}/log?tail=80`))
      } catch (e) { return }
      sock.onmessage = (ev) => {
        if (huy) return
        try {
          const m = JSON.parse(ev.data)
          if (m.log) setLog(m.log)
        } catch (e) { /* bỏ qua gói hỏng */ }
      }
      sock.onclose = () => {
        if (huy) return
        lan += 1
        if (lan <= 2) hen = setTimeout(noi, 2000 * lan)
      }
      sock.onerror = () => { try { sock.close() } catch (e) {} }
    }

    lay_ngay()
    noi()
    return () => {
      huy = true
      clearTimeout(hen)
      try { sock && sock.close() } catch (e) {}
    }
  }, [runId, enabled])

  return log
}

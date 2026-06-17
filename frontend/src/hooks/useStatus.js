import { useState, useEffect, useRef, useCallback } from 'react'

export function useStatus() {
  const [status, setStatus] = useState(null)
  const wsRef = useRef(null)
  const retryRef = useRef(null)

  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/status`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.event !== 'ping') {
          setStatus(msg)
        }
      } catch {}
    }

    ws.onclose = () => {
      const delay = Math.min(10000, (retryRef.current || 500) * 2)
      retryRef.current = delay
      setTimeout(connect, delay)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return status
}

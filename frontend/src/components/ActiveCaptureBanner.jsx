import { useState, useEffect } from 'react'
import { api } from '../api.js'

export function ActiveCaptureBanner({ status, onStop }) {
  const [elapsed, setElapsed] = useState('')

  useEffect(() => {
    if (!status?.started_at) return
    const start = new Date(status.started_at + 'Z').getTime()
    const tick = () => {
      const s = Math.floor((Date.now() - start) / 1000)
      const m = Math.floor(s / 60)
      setElapsed(`${m}m ${s % 60}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [status?.started_at])

  if (!status || !['capturing', 'building'].includes(status.status)) {
    return <p className="text-xs text-zinc-600">All quiet</p>
  }

  const isBuilding = status.status === 'building'
  const hasFrames = status.status === 'capturing' && (status.captured ?? 0) > 0

  return (
    <div className="border-l-2 border-cyan-400 pl-3 space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-cyan-300">
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        {isBuilding ? 'Building video…' : 'Capturing'}
      </div>

      {hasFrames && (
        <img
          key={status.captured}
          src={api.latestFrameUrl(status.captured)}
          alt={`Frame ${status.captured}`}
          className="w-full rounded-xl border border-zinc-700 object-cover"
        />
      )}

      {!isBuilding && (
        <div className="text-xs text-zinc-400">
          {status.captured} / {status.total} frames · {elapsed}
        </div>
      )}
      <button
        onClick={onStop}
        className="text-xs border border-red-800 text-red-400 hover:bg-red-950 rounded-2xl px-3 py-1"
      >
        Stop
      </button>
    </div>
  )
}

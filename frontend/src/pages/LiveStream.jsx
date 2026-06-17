import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { TopBar } from '../components/TopBar.jsx'
import { QualitySelector } from '../components/QualitySelector.jsx'
import { api } from '../api.js'
import { useStatus } from '../hooks/useStatus.js'
import { useCapabilities } from '../hooks/useCapabilities.js'

export default function LiveStream() {
  const [camInfo, setCamInfo] = useState(null)
  const wsMsg = useStatus()
  const [captureActive, setCaptureActive] = useState(false)
  const { modes, model } = useCapabilities()
  const [streamKey, setStreamKey] = useState(Date.now())
  const [streamRes, setStreamRes] = useState(null)
  const [changing, setChanging] = useState(false)
  const [showQuality, setShowQuality] = useState(false)
  const [debugMode, setDebugMode] = useState(false)
  const panelRef = useRef(null)

  useEffect(() => {
    api.getCameraInfo().then(setCamInfo).catch(() => {})
    api.getStreamQuality().then(setStreamRes).catch(() => {})
    api.getLogLevel().then(({ level }) => setDebugMode(level === 'DEBUG')).catch(() => {})
  }, [])

  async function toggleDebug() {
    const next = !debugMode
    try {
      await api.setLogLevel(next ? 'DEBUG' : 'INFO')
      setDebugMode(next)
    } catch (e) {
      console.error('Failed to set log level', e)
    }
  }

  useEffect(() => {
    if (wsMsg?.data?.status) {
      setCaptureActive(['capturing', 'building'].includes(wsMsg.data.status))
    } else {
      api.getTimelapsStatus()
        .then((s) => setCaptureActive(['capturing', 'building'].includes(s.status)))
        .catch(() => {})
    }
  }, [wsMsg])

  // Close panel when clicking outside
  useEffect(() => {
    if (!showQuality) return
    function handleClick(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setShowQuality(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showQuality])

  async function handleQualityChange(mode) {
    if (changing) return
    setChanging(true)
    setShowQuality(false)
    try {
      const res = await api.setStreamQuality(mode.width, mode.height)
      setStreamRes(res)
      // Force the img to reconnect after a brief pause for the backend to restart
      await new Promise((r) => setTimeout(r, 800))
      setStreamKey(Date.now())
    } catch (e) {
      console.error('Quality change failed:', e)
    } finally {
      setChanging(false)
    }
  }

  const resLabel = streamRes ? `${streamRes.width}×${streamRes.height}` : null

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <TopBar
        title="Live Camera"
        action={
          camInfo && (
            <span className="text-xs text-zinc-400 bg-zinc-800 px-3 py-1 rounded-xl">
              {camInfo.model} · MJPEG
            </span>
          )
        }
      />

      <div className="flex-1 flex items-center justify-center bg-black relative">
        {captureActive && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-amber-900/80 border border-amber-700 text-amber-200 text-sm px-4 py-2 rounded-2xl">
            <i className="fa-solid fa-camera mr-2" />
            Camera in use — capturing timelapse.{' '}
            <Link to="/capture" className="underline">View progress</Link>
          </div>
        )}

        {camInfo?.available === false ? (
          <div className="text-center space-y-4 text-zinc-500">
            <i className="fa-solid fa-video-slash text-5xl" />
            <p>Camera unavailable</p>
          </div>
        ) : (
          <>
            {changing && (
              <div className="absolute inset-0 z-20 bg-black/70 flex flex-col items-center justify-center gap-3">
                <i className="fa-solid fa-spinner fa-spin text-3xl text-cyan-400" />
                <span className="text-zinc-300 text-sm">Restarting stream…</span>
              </div>
            )}
            <img
              key={streamKey}
              src={`/api/stream?t=${streamKey}`}
              alt="Live MJPEG stream"
              className="max-w-5xl w-full rounded-3xl shadow-2xl border border-zinc-700"
            />
          </>
        )}

        {/* Quality toggle button — bottom-right of stream area */}
        {modes.length > 0 && !captureActive && (
          <div ref={panelRef} className="absolute bottom-4 right-4 z-30">
            {showQuality && (
              <div className="mb-2 bg-zinc-900 border border-zinc-700 rounded-2xl p-4 shadow-2xl w-72">
                <QualitySelector
                  modes={modes}
                  model={model}
                  selectedWidth={streamRes?.width}
                  selectedHeight={streamRes?.height}
                  onChange={handleQualityChange}
                  compact
                />
              </div>
            )}
            <button
              onClick={() => setShowQuality((v) => !v)}
              className={[
                'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all shadow-lg',
                showQuality
                  ? 'bg-cyan-500 text-black'
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700 border border-zinc-600',
              ].join(' ')}
            >
              <i className="fa-solid fa-sliders" />
              {resLabel ?? 'Quality'}
            </button>
          </div>
        )}
      </div>

      <div className="bg-zinc-900 border-t border-zinc-800 px-8 py-4 flex items-center gap-8 text-sm text-zinc-400 shrink-0">
        <span>Format: MJPEG</span>
        {resLabel && <span className="font-mono">{resLabel}</span>}
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${camInfo?.available ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          {camInfo?.available ? 'Streaming' : 'Waiting for camera'}
        </span>
        <button
          onClick={toggleDebug}
          title="Toggle verbose server logging"
          className={[
            'ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all',
            debugMode
              ? 'bg-amber-900/60 text-amber-300 border border-amber-700'
              : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300 border border-zinc-700',
          ].join(' ')}
        >
          <i className="fa-solid fa-bug" />
          {debugMode ? 'Debug ON' : 'Debug'}
        </button>
      </div>
    </div>
  )
}

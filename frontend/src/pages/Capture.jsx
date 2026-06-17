import { useEffect, useState } from 'react'
import { TopBar } from '../components/TopBar.jsx'
import { ProgressRing } from '../components/ProgressRing.jsx'
import { QualitySelector } from '../components/QualitySelector.jsx'
import { useCapabilities } from '../hooks/useCapabilities.js'
import { useStatus } from '../hooks/useStatus.js'
import { api } from '../api.js'

const DURATIONS = [
  { label: '5 min', value: 5 },
  { label: '10 min', value: 10 },
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 hr', value: 60 },
  { label: '2 hr', value: 120 },
  { label: '4 hr', value: 240 },
  { label: '8 hr', value: 480 },
]

const FPS_OPTIONS = [5, 10, 15, 24, 30]

const STATUS_COLORS = {
  idle:       'bg-zinc-800 text-zinc-400',
  capturing:  'bg-emerald-900/50 text-emerald-300',
  building:   'bg-amber-900/50 text-amber-300',
  done:       'bg-cyan-900/50 text-cyan-300',
  error:      'bg-red-900/50 text-red-300',
  cancelled:  'bg-zinc-800 text-zinc-400',
}

function useElapsed(startedAt) {
  const [elapsed, setElapsed] = useState('')
  useEffect(() => {
    if (!startedAt) { setElapsed(''); return }
    const start = new Date(startedAt + 'Z').getTime()
    const tick = () => {
      const s = Math.floor((Date.now() - start) / 1000)
      setElapsed(`${Math.floor(s / 60)}m ${s % 60}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [startedAt])
  return elapsed
}

export default function Capture() {
  const { modes, model } = useCapabilities()
  const wsMsg = useStatus()

  const [interval, setIntervalSec] = useState(5)
  const [duration, setDuration] = useState(10)
  const [fps, setFps] = useState(24)
  const [selectedMode, setSelectedMode] = useState(null)

  const [status, setStatus] = useState({ status: 'idle', captured: 0, total: 0, started_at: null })
  const [error, setError] = useState('')

  const [previewStatus, setPreviewStatus] = useState({ generating: false, ready: false, url: null })
  const elapsed = useElapsed(status.status === 'capturing' ? status.started_at : null)

  // Pick default mode (highest-res full-FOV)
  useEffect(() => {
    if (modes.length && !selectedMode) {
      const fullFov = [...modes].filter(m => m.full_fov).sort((a, b) => b.width * b.height - a.width * a.height)
      setSelectedMode(fullFov[0] || modes[modes.length - 1])
    }
  }, [modes])

  // Poll status
  useEffect(() => {
    api.getTimelapsStatus().then(setStatus).catch(() => {})
  }, [])

  useEffect(() => {
    if (wsMsg?.data) {
      setStatus(prev => ({
        ...prev,
        status: wsMsg.data.status || prev.status,
        captured: wsMsg.data.captured ?? prev.captured,
        total: wsMsg.data.total ?? prev.total,
      }))
    }
  }, [wsMsg])

  const canStart = ['idle', 'done', 'error', 'cancelled'].includes(status.status)
  const canStop = ['capturing', 'building'].includes(status.status)

  const handleStart = async () => {
    if (!selectedMode) return
    setError('')
    try {
      await api.startTimelapse({
        interval,
        duration,
        fps,
        capture_width: selectedMode.width,
        capture_height: selectedMode.height,
      })
      const s = await api.getTimelapsStatus()
      setStatus(s)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleStop = async () => {
    await api.stopTimelapse()
    const s = await api.getTimelapsStatus()
    setStatus(s)
  }

  const handlePreview = async () => {
    setPreviewStatus({ generating: true, ready: false, url: null })
    await api.triggerPreview()
    // Poll until ready
    const poll = setInterval(async () => {
      const ps = await api.getPreviewStatus()
      setPreviewStatus(ps)
      if (ps.ready || !ps.generating) clearInterval(poll)
    }, 2000)
  }

  const pct = status.total > 0 ? status.captured / status.total : 0
  const isBuilding = status.status === 'building'

  const estFinish = status.status === 'capturing' && status.captured > 0 && status.started_at
    ? (() => {
        const elapsed_s = (Date.now() - new Date(status.started_at + 'Z').getTime()) / 1000
        const rate = status.captured / elapsed_s
        const remaining = (status.total - status.captured) / (rate || 1)
        return `~${Math.ceil(remaining / 60)} min`
      })()
    : null

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <TopBar title="Capture" />
      <div className="flex-1 overflow-auto p-8">
        <div className="grid grid-cols-5 gap-8">

          {/* Controls panel */}
          <div className="col-span-2 bg-zinc-900 rounded-3xl p-8 space-y-8">
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Sequence Settings</h3>

              <div>
                <label className="text-xs text-zinc-400 mb-2 block">
                  Interval: <span className="text-zinc-200 font-medium">{interval}s</span>
                </label>
                <input
                  type="range" min={1} max={120} value={interval}
                  onChange={e => setIntervalSec(Number(e.target.value))}
                  className="w-full accent-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs text-zinc-400 mb-2 block">Duration</label>
                <select
                  value={duration}
                  onChange={e => setDuration(Number(e.target.value))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-400 text-zinc-200"
                >
                  {DURATIONS.map(d => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-zinc-400 mb-2 block">Output FPS</label>
                <div className="flex gap-2">
                  {FPS_OPTIONS.map(f => (
                    <button
                      key={f}
                      onClick={() => setFps(f)}
                      className={`flex-1 py-2 rounded-2xl text-sm font-medium transition-colors ${
                        fps === f
                          ? 'bg-cyan-500 text-black'
                          : 'border border-zinc-700 hover:bg-zinc-800 text-zinc-300'
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <QualitySelector
              modes={modes}
              model={model}
              selectedWidth={selectedMode?.width}
              selectedHeight={selectedMode?.height}
              onChange={setSelectedMode}
            />

            {error && (
              <div className="text-red-400 text-xs bg-red-950/50 rounded-2xl px-4 py-3">{error}</div>
            )}

            <div className="space-y-3 pt-2">
              <button
                onClick={handleStart}
                disabled={!canStart}
                className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed text-black font-semibold py-5 text-lg rounded-3xl transition-colors"
              >
                START CAPTURE
              </button>
              <button
                onClick={handleStop}
                disabled={!canStop}
                className="w-full border border-red-800 text-red-400 hover:bg-red-950 disabled:opacity-40 disabled:cursor-not-allowed rounded-3xl py-3 transition-colors"
              >
                STOP
              </button>
            </div>
          </div>

          {/* Status + preview panel */}
          <div className="col-span-3 space-y-6">
            <div className="bg-zinc-900 rounded-3xl p-8 flex flex-col items-center gap-6">
              <span className={`text-xs px-4 py-1.5 rounded-full font-medium ${STATUS_COLORS[status.status] || STATUS_COLORS.idle}`}>
                {status.status}
              </span>

              <ProgressRing
                value={status.captured}
                max={status.total || 1}
                size={120}
                spin={isBuilding}
              />

              <div className="text-center">
                <div className="text-4xl font-semibold">
                  {status.captured}
                  <span className="text-xl text-zinc-400"> / {status.total || '—'}</span>
                </div>
                <div className="text-sm text-zinc-400 font-mono mt-1">{elapsed}</div>
                {estFinish && (
                  <div className="text-xs text-zinc-500 mt-1">Finishes in {estFinish}</div>
                )}
              </div>

              {status.status === 'capturing' && status.captured > 0 && (
                <div className="w-full">
                  <div className="text-xs text-zinc-500 mb-2 text-center">Latest frame</div>
                  <img
                    key={status.captured}
                    src={api.latestFrameUrl(status.captured)}
                    alt={`Frame ${status.captured}`}
                    className="w-full rounded-2xl border border-zinc-700 object-cover"
                  />
                  <div className="text-xs text-zinc-600 text-right mt-1 font-mono">
                    #{status.captured}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-zinc-900 rounded-3xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <i className="fa-solid fa-film text-zinc-400" />
                <span className="text-sm font-medium text-zinc-300">Frame Preview</span>
              </div>

              {previewStatus.ready ? (
                <>
                  <video
                    src="/api/preview/file"
                    controls
                    className="w-full rounded-2xl mt-2"
                    key={previewStatus.url}
                  />
                  <p className="text-xs text-zinc-500 mt-2">
                    Temporary preview — original frames preserved
                  </p>
                </>
              ) : previewStatus.generating ? (
                <div className="flex items-center gap-3 text-sm text-zinc-400 py-4">
                  <i className="fa-solid fa-spinner animate-spin" />
                  Building preview…
                </div>
              ) : (
                <div className="space-y-3">
                  {status.status === 'idle' ? (
                    <div className="text-center py-6 text-zinc-700">
                      <i className="fa-solid fa-film text-3xl" />
                    </div>
                  ) : (
                    <button
                      onClick={handlePreview}
                      disabled={status.status !== 'capturing' || status.captured === 0}
                      className="w-full border border-zinc-700 hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed rounded-3xl px-5 py-3 text-sm text-zinc-300"
                    >
                      GENERATE PREVIEW
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

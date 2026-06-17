import { useEffect, useState } from 'react'
import { TopBar } from '../components/TopBar.jsx'
import { QualitySelector } from '../components/QualitySelector.jsx'
import { useCapabilities } from '../hooks/useCapabilities.js'
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

export default function Settings() {
  const { modes, model } = useCapabilities()
  const [settings, setSettings] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [deleteState, setDeleteState] = useState('idle') // idle | confirm | deleting | done
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {})
  }, [])

  if (!settings) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500">
        <i className="fa-solid fa-spinner fa-spin mr-2" /> Loading…
      </div>
    )
  }

  const streamMode = modes.find(m => m.width === settings.stream_width && m.height === settings.stream_height)
  const captureMode = modes.find(m => m.width === settings.capture_width && m.height === settings.capture_height)

  async function save(patch) {
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const updated = await api.updateSettings(patch)
      setSettings(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteAll() {
    setDeleteState('deleting')
    try {
      await api.deleteAllData()
      setDeleteState('done')
    } catch (e) {
      setError(e.message)
      setDeleteState('idle')
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <TopBar
        title="Settings"
        action={
          saved && (
            <span className="text-xs text-emerald-400 bg-emerald-950/60 px-3 py-1 rounded-xl">
              <i className="fa-solid fa-check mr-1" /> Saved
            </span>
          )
        }
      />

      <div className="flex-1 overflow-auto p-8 space-y-8 max-w-3xl">

        {/* Stream defaults */}
        <section className="bg-zinc-900 rounded-3xl p-8 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-zinc-200">Default Stream Resolution</h2>
            <p className="text-sm text-zinc-500 mt-1">Applied when the server starts and when you change it here.</p>
          </div>
          <QualitySelector
            modes={modes}
            model={model}
            selectedWidth={settings.stream_width}
            selectedHeight={settings.stream_height}
            onChange={(m) => save({ stream_width: m.width, stream_height: m.height })}
          />
        </section>

        {/* Capture defaults */}
        <section className="bg-zinc-900 rounded-3xl p-8 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-zinc-200">Default Capture Settings</h2>
            <p className="text-sm text-zinc-500 mt-1">Pre-filled on the Capture page each session.</p>
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-2 block">
              Interval: <span className="text-zinc-200 font-medium">{settings.capture_interval}s</span>
            </label>
            <input
              type="range" min={1} max={120} value={settings.capture_interval}
              onChange={e => setSettings(s => ({ ...s, capture_interval: Number(e.target.value) }))}
              onMouseUp={e => save({ capture_interval: Number(e.target.value) })}
              onTouchEnd={e => save({ capture_interval: Number(e.target.value) })}
              className="w-full accent-cyan-400"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-2 block">Duration</label>
            <select
              value={settings.capture_duration}
              onChange={e => save({ capture_duration: Number(e.target.value) })}
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
                  onClick={() => save({ capture_fps: f })}
                  className={`flex-1 py-2 rounded-2xl text-sm font-medium transition-colors ${
                    settings.capture_fps === f
                      ? 'bg-cyan-500 text-black'
                      : 'border border-zinc-700 hover:bg-zinc-800 text-zinc-300'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <QualitySelector
            modes={modes}
            model={model}
            selectedWidth={settings.capture_width}
            selectedHeight={settings.capture_height}
            onChange={(m) => save({ capture_width: m.width, capture_height: m.height })}
          />

          {error && (
            <p className="text-xs text-red-400 bg-red-950/40 rounded-2xl px-4 py-3">{error}</p>
          )}
        </section>

        {/* Danger zone */}
        <section className="bg-zinc-900 rounded-3xl p-8 space-y-4 border border-red-900/40">
          <div>
            <h2 className="text-base font-semibold text-red-400">Danger Zone</h2>
            <p className="text-sm text-zinc-500 mt-1">Permanently deletes all captured frames, finished videos, and database records. This cannot be undone.</p>
          </div>

          {deleteState === 'idle' && (
            <button
              onClick={() => setDeleteState('confirm')}
              className="border border-red-800 text-red-400 hover:bg-red-950 rounded-2xl px-6 py-3 text-sm transition-colors"
            >
              <i className="fa-solid fa-trash mr-2" />
              Delete All Captures &amp; Videos
            </button>
          )}

          {deleteState === 'confirm' && (
            <div className="bg-red-950/40 border border-red-800 rounded-2xl p-5 space-y-4">
              <p className="text-sm text-red-300 font-medium">
                <i className="fa-solid fa-triangle-exclamation mr-2" />
                This will permanently delete every video and captured frame on this device. Are you sure?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDeleteAll}
                  className="bg-red-700 hover:bg-red-600 text-white rounded-2xl px-5 py-2 text-sm font-medium transition-colors"
                >
                  Yes, delete everything
                </button>
                <button
                  onClick={() => setDeleteState('idle')}
                  className="border border-zinc-700 text-zinc-300 hover:bg-zinc-800 rounded-2xl px-5 py-2 text-sm transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {deleteState === 'deleting' && (
            <div className="flex items-center gap-3 text-sm text-zinc-400">
              <i className="fa-solid fa-spinner fa-spin" /> Deleting…
            </div>
          )}

          {deleteState === 'done' && (
            <div className="text-sm text-emerald-400">
              <i className="fa-solid fa-check mr-2" /> All data deleted.
            </div>
          )}
        </section>

      </div>
    </div>
  )
}

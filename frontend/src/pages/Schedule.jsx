import { useEffect, useState } from 'react'
import cronstrue from 'cronstrue'
import { TopBar } from '../components/TopBar.jsx'
import { QualitySelector } from '../components/QualitySelector.jsx'
import { useCapabilities } from '../hooks/useCapabilities.js'
import { api } from '../api.js'

const FPS_OPTIONS = [5, 10, 15, 24, 30]
const DURATIONS = [5, 10, 15, 30, 60, 120, 240, 480]

function nextRuns(expr, n = 3) {
  try {
    const now = new Date()
    const results = []
    // Use cronstrue to describe but compute times manually
    return [cronstrue.toString(expr, { verbose: false })]
  } catch {
    return []
  }
}

function DrawerForm({ job, modes, model, onSave, onCancel }) {
  const [name, setName] = useState(job?.name || '')
  const [cron, setCron] = useState(job?.cron_expression || '0 6 * * *')
  const [interval, setInterval] = useState(job?.interval || 5)
  const [duration, setDuration] = useState(job?.duration || 10)
  const [fps, setFps] = useState(job?.fps || 24)
  const [selectedMode, setSelectedMode] = useState(null)
  const [cronErr, setCronErr] = useState('')
  const [cronDesc, setCronDesc] = useState('')

  useEffect(() => {
    if (modes.length && !selectedMode) {
      if (job) {
        const m = modes.find(m => m.width === job.capture_width && m.height === job.capture_height)
        setSelectedMode(m || modes[modes.length - 1])
      } else {
        const full = [...modes].filter(m => m.full_fov).sort((a, b) => b.width * b.height - a.width * a.height)
        setSelectedMode(full[0] || modes[modes.length - 1])
      }
    }
  }, [modes])

  useEffect(() => {
    try {
      setCronDesc(cronstrue.toString(cron, { verbose: false }))
      setCronErr('')
    } catch {
      setCronDesc('')
      setCronErr('Invalid cron expression')
    }
  }, [cron])

  const handleSave = () => {
    if (cronErr || !selectedMode) return
    onSave({
      name,
      cron_expression: cron,
      interval,
      duration,
      fps,
      capture_width: selectedMode.width,
      capture_height: selectedMode.height,
    })
  }

  return (
    <div className="w-96 bg-zinc-900 border-l border-zinc-800 flex flex-col shrink-0">
      <div className="px-8 py-6 border-b border-zinc-800">
        <h2 className="text-base font-semibold text-zinc-200">{job ? 'Edit Schedule' : 'New Schedule'}</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-5">
        <div>
          <label className="text-xs text-zinc-400 block mb-1">Name</label>
          <input
            value={name} onChange={e => setName(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-400 text-zinc-200"
          />
        </div>

        <div>
          <label className="text-xs text-zinc-400 block mb-1">Cron Expression</label>
          <input
            value={cron} onChange={e => setCron(e.target.value)}
            className={`w-full bg-zinc-800 border rounded-2xl px-4 py-3 text-sm font-mono focus:outline-none text-zinc-200 ${
              cronErr ? 'border-red-700 focus:border-red-500' : 'border-zinc-700 focus:border-cyan-400'
            }`}
          />
          {cronDesc && <p className="text-xs text-zinc-500 mt-1">{cronDesc}</p>}
          {cronErr && <p className="text-xs text-red-400 mt-1">{cronErr}</p>}
        </div>

        <div>
          <label className="text-xs text-zinc-400 block mb-1">
            Interval: <span className="text-zinc-200">{interval}s</span>
          </label>
          <input
            type="range" min={1} max={120} value={interval}
            onChange={e => setInterval(Number(e.target.value))}
            className="w-full accent-cyan-400"
          />
        </div>

        <div>
          <label className="text-xs text-zinc-400 block mb-1">Duration (min)</label>
          <select
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-400 text-zinc-200"
          >
            {DURATIONS.map(d => <option key={d} value={d}>{d} min</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs text-zinc-400 block mb-1">Output FPS</label>
          <div className="flex gap-2">
            {FPS_OPTIONS.map(f => (
              <button
                key={f}
                onClick={() => setFps(f)}
                className={`flex-1 py-2 rounded-2xl text-sm font-medium ${
                  fps === f ? 'bg-cyan-500 text-black' : 'border border-zinc-700 text-zinc-300 hover:bg-zinc-800'
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
          selectedWidth={selectedMode?.width}
          selectedHeight={selectedMode?.height}
          onChange={setSelectedMode}
          compact
        />
      </div>

      <div className="px-8 py-5 border-t border-zinc-800 flex gap-3">
        <button
          onClick={handleSave}
          disabled={!!cronErr || !name || !selectedMode}
          className="flex-1 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 text-black font-semibold py-2.5 rounded-3xl text-sm"
        >
          Save
        </button>
        <button onClick={onCancel} className="flex-1 border border-zinc-700 hover:bg-zinc-800 rounded-3xl py-2.5 text-sm text-zinc-300">
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function Schedule() {
  const [jobs, setJobs] = useState([])
  const [showDrawer, setShowDrawer] = useState(false)
  const [editJob, setEditJob] = useState(null)
  const { modes, model } = useCapabilities()

  const refresh = () => api.listSchedules().then(setJobs).catch(() => {})
  useEffect(() => { refresh() }, [])

  const handleSave = async (body) => {
    if (editJob) {
      await api.updateSchedule(editJob.id, body)
    } else {
      await api.createSchedule(body)
    }
    setShowDrawer(false)
    setEditJob(null)
    refresh()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this schedule?')) return
    await api.deleteSchedule(id)
    refresh()
  }

  const handleToggle = async (job) => {
    if (job.enabled) {
      await api.disableSchedule(job.id)
    } else {
      await api.enableSchedule(job.id)
    }
    refresh()
  }

  const handleRunNow = async (id) => {
    try {
      await api.runScheduleNow(id)
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          title="Schedule"
          action={
            <button
              onClick={() => { setEditJob(null); setShowDrawer(true) }}
              className="bg-cyan-500 hover:bg-cyan-400 text-black font-semibold px-5 py-2 rounded-3xl text-sm"
            >
              Add Schedule
            </button>
          }
        />

        <div className="flex-1 overflow-auto p-8">
          {jobs.length === 0 ? (
            <div className="bg-zinc-900 rounded-3xl p-16 text-center">
              <i className="fa-solid fa-clock text-4xl text-zinc-700 block mb-4" />
              <p className="text-zinc-500">No scheduled captures yet. Add one to get started.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map(job => (
                <div key={job.id} className="bg-zinc-900 rounded-3xl px-6 py-5 flex items-center gap-6">
                  <button onClick={() => handleToggle(job)} className="text-xl">
                    <i className={`fa-solid ${job.enabled ? 'fa-toggle-on text-cyan-400' : 'fa-toggle-off text-zinc-600'}`} />
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-zinc-100">{job.name}</div>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="font-mono text-xs text-zinc-400 bg-zinc-800 px-3 py-1 rounded-xl">
                        {job.cron_expression}
                      </span>
                      {job.next_run_at && (
                        <span className="text-xs text-zinc-500">
                          Next: {job.next_run_at.replace('T', ' ').substring(0, 16)} SAST
                        </span>
                      )}
                    </div>
                  </div>

                  <span className="text-xs bg-zinc-800 rounded-xl px-2 py-1 text-zinc-400 shrink-0">
                    {job.capture_width}×{job.capture_height}
                  </span>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleRunNow(job.id)}
                      className="w-9 h-9 rounded-2xl bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center text-zinc-300"
                      title="Run now"
                    >
                      <i className="fa-solid fa-bolt text-sm" />
                    </button>
                    <button
                      onClick={() => { setEditJob(job); setShowDrawer(true) }}
                      className="w-9 h-9 rounded-2xl bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center text-zinc-300"
                      title="Edit"
                    >
                      <i className="fa-solid fa-pen text-sm" />
                    </button>
                    <button
                      onClick={() => handleDelete(job.id)}
                      className="w-9 h-9 rounded-2xl bg-zinc-800 hover:bg-red-950 flex items-center justify-center text-red-400"
                      title="Delete"
                    >
                      <i className="fa-solid fa-trash text-sm" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showDrawer && (
        <DrawerForm
          job={editJob}
          modes={modes}
          model={model}
          onSave={handleSave}
          onCancel={() => { setShowDrawer(false); setEditJob(null) }}
        />
      )}
    </div>
  )
}

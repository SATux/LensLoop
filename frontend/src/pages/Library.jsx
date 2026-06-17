import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { TopBar } from '../components/TopBar.jsx'
import { VideoPlayer } from '../components/VideoPlayer.jsx'
import { useVideos } from '../hooks/useVideos.js'
import { api } from '../api.js'

function fmtSize(bytes) {
  if (bytes > 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes > 1e6) return `${(bytes / 1e6).toFixed(1)} MB`
  return `${(bytes / 1e3).toFixed(0)} KB`
}

function fmtDur(s) {
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}m ${Math.round(s % 60)}s` : `${Math.round(s)}s`
}

export default function Library() {
  const { videos, loading, refresh } = useVideos()
  const [selectedId, setSelectedId] = useState(null)
  const [search, setSearch] = useState('')
  const location = useLocation()

  useEffect(() => {
    if (location.state?.selectedId) {
      setSelectedId(location.state.selectedId)
    }
  }, [location.state])

  const filtered = videos.filter(v =>
    v.filename.toLowerCase().includes(search.toLowerCase()) ||
    v.created_at.includes(search)
  )

  const selected = videos.find(v => v.id === selectedId)

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this video permanently?')) return
    await api.deleteVideo(id)
    if (selectedId === id) setSelectedId(null)
    refresh()
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left panel */}
      <div className="w-80 bg-zinc-900 border-r border-zinc-800 flex flex-col shrink-0">
        <div className="px-4 py-4 border-b border-zinc-800 flex items-center gap-3">
          <span className="font-medium text-zinc-200 text-sm">Library</span>
          <span className="bg-zinc-800 rounded-full px-2 py-0.5 text-xs text-zinc-400">
            {videos.length}
          </span>
        </div>

        <div className="px-3 py-3 border-b border-zinc-800">
          <div className="relative">
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search…"
              className="w-full bg-zinc-800 rounded-2xl py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500 text-zinc-200"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8 text-zinc-600 text-sm">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-zinc-600 text-sm">No videos</div>
          ) : (
            filtered.map(v => (
              <div
                key={v.id}
                onClick={() => setSelectedId(v.id)}
                className={`group flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-800 rounded-2xl mx-2 my-1 ${
                  selectedId === v.id ? 'bg-zinc-800 ring-1 ring-cyan-400' : ''
                }`}
              >
                <img
                  src={api.thumbnailUrl(v.id)}
                  alt=""
                  className="w-16 h-10 object-cover rounded-xl shrink-0 bg-zinc-700"
                  onError={e => { e.target.style.display = 'none' }}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-zinc-200 truncate">{v.filename}</div>
                  <div className="text-xs text-zinc-500">{new Date(v.created_at + 'Z').toLocaleDateString()}</div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDelete(v.id) }}
                  className="opacity-0 group-hover:opacity-100 text-red-400 text-xs px-1"
                >
                  <i className="fa-solid fa-trash" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center text-zinc-700 space-y-3 flex-col">
            <i className="fa-solid fa-film text-5xl" />
            <p className="text-sm">Select a recording to play</p>
          </div>
        ) : (
          <>
            <TopBar
              title={selected.filename}
              action={
                <span className="text-xs text-zinc-400">
                  {new Date(selected.created_at + 'Z').toLocaleDateString()}
                </span>
              }
            />

            <div className="flex items-center gap-3 px-6 py-3 bg-zinc-900 border-b border-zinc-800 shrink-0 flex-wrap">
              <a
                href={api.videoFileUrl(selected.id)}
                download={selected.filename}
                className="w-9 h-9 rounded-2xl bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center text-zinc-300"
                title="Download"
              >
                <i className="fa-solid fa-download text-sm" />
              </a>
              <button
                onClick={() => handleDelete(selected.id)}
                className="w-9 h-9 rounded-2xl bg-zinc-800 hover:bg-red-950 flex items-center justify-center text-red-400"
                title="Delete"
              >
                <i className="fa-solid fa-trash text-sm" />
              </button>
              {[
                { label: fmtDur(selected.duration_seconds) },
                { label: `${selected.fps} fps` },
                { label: `${selected.width}×${selected.height}` },
                { label: fmtSize(selected.size_bytes) },
                { label: `${selected.frame_count} frames` },
              ].map(({ label }) => (
                <span key={label} className="text-xs bg-zinc-800 rounded-xl px-3 py-1 text-zinc-400">
                  {label}
                </span>
              ))}
            </div>

            <VideoPlayer src={api.videoFileUrl(selected.id)} />
          </>
        )}
      </div>
    </div>
  )
}

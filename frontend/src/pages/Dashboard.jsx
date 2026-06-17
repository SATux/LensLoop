import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/TopBar.jsx'
import { StatCard } from '../components/StatCard.jsx'
import { ProgressRing } from '../components/ProgressRing.jsx'
import { api } from '../api.js'

function VideoCard({ video, onClick }) {
  const date = new Date(video.created_at + 'Z').toLocaleDateString()
  const dur = video.duration_seconds ? `${Math.round(video.duration_seconds)}s` : '—'
  return (
    <div
      className="bg-zinc-900 rounded-3xl overflow-hidden cursor-pointer hover:ring-2 hover:ring-cyan-400 transition-all"
      onClick={onClick}
    >
      <div className="h-48 bg-zinc-800 flex items-center justify-center">
        <img
          src={api.thumbnailUrl(video.id)}
          alt={video.filename}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.target.style.display = 'none'
          }}
        />
      </div>
      <div className="p-4">
        <div className="text-sm font-medium text-zinc-200 truncate">{video.filename}</div>
        <div className="text-xs text-zinc-500 mt-1">{date} · {dur} · {video.frame_count} frames</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [camInfo, setCamInfo] = useState(null)
  const [videos, setVideos] = useState([])
  const [schedules, setSchedules] = useState([])
  const [captureStatus, setCaptureStatus] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.getCameraInfo().then(setCamInfo).catch(() => {})
    api.listVideos().then(setVideos).catch(() => {})
    api.listSchedules().then(setSchedules).catch(() => {})
    api.getTimelapsStatus().then(setCaptureStatus).catch(() => {})
  }, [])

  const nextSchedule = schedules
    .filter((s) => s.enabled && s.next_run_at)
    .sort((a, b) => a.next_run_at.localeCompare(b.next_run_at))[0]

  const isActive = captureStatus && ['capturing', 'building'].includes(captureStatus.status)

  return (
    <div className="flex-1 overflow-auto p-8 space-y-8">
      <TopBar title="Dashboard" />

      {isActive && (
        <div className="bg-zinc-900 border border-amber-800 rounded-3xl p-6 flex items-center gap-6">
          <ProgressRing
            value={captureStatus.captured}
            max={captureStatus.total}
            size={64}
            spin={captureStatus.status === 'building'}
          />
          <div className="flex-1">
            <div className="text-sm font-medium text-amber-300 capitalize">{captureStatus.status}</div>
            <div className="text-xs text-zinc-400 mt-1">
              {captureStatus.captured} / {captureStatus.total} frames
            </div>
          </div>
          <button
            onClick={() => navigate('/capture')}
            className="text-sm text-cyan-400 hover:text-cyan-300"
          >
            Go to Capture →
          </button>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <StatCard
          icon="fa-camera"
          label="Camera"
          value={camInfo ? (camInfo.available ? '●' : '○') : '…'}
          sub={camInfo ? (camInfo.available ? `${camInfo.model} — ready` : 'Offline') : 'Checking…'}
          subColor={camInfo?.available ? 'text-emerald-400' : 'text-red-400'}
        />
        <StatCard
          icon="fa-images"
          label="Total Videos"
          value={videos.length}
          sub="in library"
        />
        <StatCard
          icon="fa-clock"
          label="Next Scheduled"
          value={nextSchedule ? '⏰' : '—'}
          sub={nextSchedule
            ? nextSchedule.next_run_at.replace('T', ' ').substring(0, 16) + ' SAST'
            : 'None scheduled'}
        />
      </div>

      {videos.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-zinc-200 mb-4">Recent Captures</h2>
          <div className="grid grid-cols-3 gap-6">
            {videos.slice(0, 3).map((v) => (
              <VideoCard
                key={v.id}
                video={v}
                onClick={() => navigate('/library', { state: { selectedId: v.id } })}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TopBar } from '../components/TopBar.jsx'
import { api } from '../api.js'
import { useStatus } from '../hooks/useStatus.js'

export default function LiveStream() {
  const [camInfo, setCamInfo] = useState(null)
  const wsMsg = useStatus()
  const [captureActive, setCaptureActive] = useState(false)

  useEffect(() => {
    api.getCameraInfo().then(setCamInfo).catch(() => {})
  }, [])

  useEffect(() => {
    if (wsMsg?.data?.status) {
      setCaptureActive(['capturing', 'building'].includes(wsMsg.data.status))
    } else {
      api.getTimelapsStatus()
        .then((s) => setCaptureActive(['capturing', 'building'].includes(s.status)))
        .catch(() => {})
    }
  }, [wsMsg])

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
          <img
            src="/api/stream"
            alt="Live MJPEG stream"
            className="max-w-5xl w-full rounded-3xl shadow-2xl border border-zinc-700"
          />
        )}
      </div>

      <div className="bg-zinc-900 border-t border-zinc-800 px-8 py-4 flex gap-8 text-sm text-zinc-400 shrink-0">
        <span>Format: MJPEG</span>
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${camInfo?.available ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          {camInfo?.available ? 'Streaming' : 'Waiting for camera'}
        </span>
      </div>
    </div>
  )
}

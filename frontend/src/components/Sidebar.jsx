import { NavLink } from 'react-router-dom'
import { ActiveCaptureBanner } from './ActiveCaptureBanner.jsx'
import { ProgressBar } from './ProgressBar.jsx'
import { useStatus } from '../hooks/useStatus.js'
import { api } from '../api.js'
import { useEffect, useState } from 'react'

const NAV = [
  { to: '/',          icon: 'fa-house',   label: 'Dashboard'   },
  { to: '/live',      icon: 'fa-video',   label: 'Live Stream' },
  { to: '/capture',   icon: 'fa-camera',  label: 'Capture'     },
  { to: '/schedule',  icon: 'fa-clock',   label: 'Schedule'    },
  { to: '/library',   icon: 'fa-images',  label: 'Library'     },
]

function useDiskUsage() {
  const [disk, setDisk] = useState(null)
  useEffect(() => {
    // Approximate via video list sizes
    api.listVideos()
      .then((vids) => {
        const used = vids.reduce((s, v) => s + (v.size_bytes || 0), 0)
        setDisk({ usedGB: (used / 1e9).toFixed(1), pct: Math.min(100, (used / 32e9) * 100) })
      })
      .catch(() => {})
  }, [])
  return disk
}

export function Sidebar() {
  const wsMsg = useStatus()
  const [captureStatus, setCaptureStatus] = useState(null)
  const disk = useDiskUsage()

  useEffect(() => {
    if (wsMsg?.data) {
      setCaptureStatus(prev => ({
        ...(prev || {}),
        status: wsMsg.data.status || prev?.status,
        captured: wsMsg.data.captured ?? prev?.captured,
        total: wsMsg.data.total ?? prev?.total,
        started_at: wsMsg.data.started_at ?? prev?.started_at,
      }))
    }
  }, [wsMsg])

  useEffect(() => {
    api.getTimelapsStatus()
      .then((s) => setCaptureStatus(s))
      .catch(() => {})
  }, [])

  const handleStop = () => {
    api.stopTimelapse()
      .then(() => api.getTimelapsStatus())
      .then((s) => setCaptureStatus(s))
      .catch(() => {})
  }

  return (
    <aside className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col shrink-0 h-screen">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-zinc-800">
        <img
          src="/LensLoop.png"
          alt="LensLoop"
          className="w-full h-auto block"
          style={{ imageRendering: 'auto' }}
        />
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm transition-colors ${
                isActive
                  ? 'bg-zinc-800 text-white font-medium'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
              }`
            }
          >
            <i className={`fa-solid ${icon} w-4`} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Storage + capture widget */}
      <div className="px-3 pb-4">
        <div className="bg-zinc-800 rounded-3xl p-4 space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="text-zinc-400">Storage</span>
            {disk && <span className="text-cyan-400 font-medium">{disk.usedGB} GB used</span>}
          </div>
          {disk && <ProgressBar value={disk.pct} max={100} />}
          <ActiveCaptureBanner status={captureStatus} onStop={handleStop} />
        </div>
      </div>
    </aside>
  )
}

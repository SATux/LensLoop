import { useEffect, useState } from 'react'
import { api } from '../api.js'

export function TopBar({ title, action }) {
  const [camOk, setCamOk] = useState(null)

  useEffect(() => {
    api.getCameraInfo()
      .then((d) => setCamOk(d.available))
      .catch(() => setCamOk(false))
    const id = setInterval(() => {
      api.getCameraInfo()
        .then((d) => setCamOk(d.available))
        .catch(() => setCamOk(false))
    }, 15000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="h-14 border-b border-zinc-800 bg-zinc-900 px-8 flex items-center justify-between shrink-0">
      <h1 className="text-base font-semibold text-zinc-100">{title}</h1>
      <div className="flex items-center gap-4">
        {camOk !== null && (
          <span
            className={`flex items-center gap-1.5 text-xs ${camOk ? 'text-emerald-400' : 'text-red-400'}`}
            title={camOk ? 'Camera ready' : 'Camera offline'}
          >
            <i className="fa-solid fa-circle text-[8px]" />
            {camOk ? 'Camera ready' : 'Camera offline'}
          </span>
        )}
        {action}
      </div>
    </div>
  )
}

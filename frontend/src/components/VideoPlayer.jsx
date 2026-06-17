import { useRef, useState } from 'react'

export function VideoPlayer({ src }) {
  const [error, setError] = useState(false)

  if (!src) return null

  return (
    <div className="flex-1 flex flex-col bg-black">
      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-red-400 space-y-2">
            <i className="fa-solid fa-circle-exclamation text-3xl" />
            <p className="text-sm">Video unavailable — it may have been deleted</p>
            <button onClick={() => setError(false)} className="text-xs text-zinc-500 underline">
              Retry
            </button>
          </div>
        </div>
      ) : (
        <video
          key={src}
          src={src}
          controls
          preload="metadata"
          className="w-full h-full object-contain rounded-b-3xl"
          onError={() => setError(true)}
        />
      )}
    </div>
  )
}

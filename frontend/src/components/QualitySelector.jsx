export function QualitySelector({ modes, model, selectedWidth, selectedHeight, onChange, compact = false }) {
  if (!modes || modes.length === 0) {
    return (
      <div className="bg-zinc-800 rounded-2xl p-4 text-center text-zinc-500 text-sm">
        <i className="fa-solid fa-triangle-exclamation mr-2 text-amber-400" />
        Camera offline — quality unavailable
      </div>
    )
  }

  const grid = compact ? 'grid grid-cols-1 gap-2' : 'grid grid-cols-2 gap-3'

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-medium text-zinc-300">Capture Quality</span>
        {model && (
          <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded-full uppercase">
            {model}
          </span>
        )}
      </div>
      <div className={grid}>
        {modes.map((m) => {
          const selected = m.width === selectedWidth && m.height === selectedHeight
          return (
            <button
              key={`${m.width}x${m.height}`}
              onClick={() => onChange(m)}
              className={[
                'rounded-2xl p-4 text-left cursor-pointer border-2 transition-all',
                selected
                  ? 'border-cyan-400 bg-zinc-700'
                  : 'border-transparent bg-zinc-800 hover:border-zinc-600',
              ].join(' ')}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-zinc-100">{m.label}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  m.full_fov ? 'bg-emerald-900/60 text-emerald-300' : 'bg-zinc-700 text-zinc-400'
                }`}>
                  {m.full_fov ? (
                    <><i className="fa-solid fa-expand mr-1" />Full FOV</>
                  ) : (
                    <><i className="fa-solid fa-crop mr-1" />Cropped</>
                  )}
                </span>
              </div>
              <div className="font-mono text-xs text-zinc-400 mb-1">
                {m.width}×{m.height}
              </div>
              <div className="text-xs text-zinc-400">
                {m.megapixels} MP · up to {Math.round(m.max_fps)} fps
              </div>
              <div className="text-xs text-zinc-500 mt-1">{m.description}</div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

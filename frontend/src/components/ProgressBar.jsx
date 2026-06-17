export function ProgressBar({ value, max, className = '' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className={`h-1.5 bg-zinc-700 rounded-full overflow-hidden ${className}`}>
      <div
        className="h-full bg-cyan-400 rounded-full transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

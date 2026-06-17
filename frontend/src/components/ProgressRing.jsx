export function ProgressRing({ value, max, size = 64, spin = false }) {
  const r = (size - 8) / 2
  const circ = 2 * Math.PI * r
  const pct = max > 0 ? Math.min(1, value / max) : 0
  const dash = pct * circ

  return (
    <svg width={size} height={size} className={spin ? 'animate-spin' : ''}>
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#27272a" strokeWidth="6"
      />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#22d3ee" strokeWidth="6"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  )
}

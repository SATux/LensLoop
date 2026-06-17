export function StatCard({ icon, label, value, sub, subColor = 'text-zinc-400' }) {
  return (
    <div className="bg-zinc-900 rounded-3xl p-6 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium">
        <i className={`fa-solid ${icon}`} />
        {label}
      </div>
      <div className="text-5xl font-semibold text-zinc-100">{value}</div>
      <div className={`text-sm ${subColor}`}>{sub}</div>
    </div>
  )
}

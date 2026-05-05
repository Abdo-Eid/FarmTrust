import { clsx } from 'clsx'

interface StatCardProps {
  label: string
  value: string | number
  icon: string
  color?: 'default' | 'green' | 'amber' | 'red' | 'indigo'
  sublabel?: string
}

export function StatCard({ label, value, icon, color = 'default', sublabel }: StatCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
          <p className={clsx(
            'text-2xl font-bold mt-1',
            color === 'default' && 'text-gray-900',
            color === 'green'   && 'text-green-700',
            color === 'amber'   && 'text-amber-700',
            color === 'red'     && 'text-red-700',
            color === 'indigo'  && 'text-indigo-700',
          )}>
            {value}
          </p>
          {sublabel && <p className="text-xs text-gray-400 mt-0.5">{sublabel}</p>}
        </div>
        <div className={clsx(
          'w-9 h-9 rounded-md flex items-center justify-center flex-shrink-0',
          color === 'default' && 'bg-gray-100',
          color === 'green'   && 'bg-green-100',
          color === 'amber'   && 'bg-amber-100',
          color === 'red'     && 'bg-red-100',
          color === 'indigo'  && 'bg-indigo-100',
        )}>
          <span className={clsx(
            'material-symbols-outlined text-lg',
            color === 'default' && 'text-gray-500',
            color === 'green'   && 'text-green-600',
            color === 'amber'   && 'text-amber-600',
            color === 'red'     && 'text-red-600',
            color === 'indigo'  && 'text-indigo-600',
          )}>
            {icon}
          </span>
        </div>
      </div>
    </div>
  )
}

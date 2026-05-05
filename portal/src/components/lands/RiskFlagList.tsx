import { clsx } from 'clsx'
import { FLAG_LABELS, FLAG_ICONS } from '@/lib/constants'
import type { RiskFlag } from '@/lib/types'

interface RiskFlagListProps {
  flags: RiskFlag[]
  className?: string
}

export function RiskFlagList({ flags, className }: RiskFlagListProps) {
  if (flags.length === 0) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600">
        <span className="material-symbols-outlined text-sm">check_circle</span>
        No risk flags
      </span>
    )
  }

  return (
    <div className={clsx('flex flex-wrap gap-2', className)}>
      {flags.map(flag => (
        <span
          key={flag}
          className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 border border-red-200 rounded-full text-xs font-medium"
        >
          <span className="material-symbols-outlined text-xs">{FLAG_ICONS[flag]}</span>
          {FLAG_LABELS[flag]}
        </span>
      ))}
    </div>
  )
}

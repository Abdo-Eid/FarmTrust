import { clsx } from 'clsx'
import { LAND_STATUS_COLORS, LAND_STATUS_LABELS } from '@/lib/constants'
import type { LandStatus, JobStatus } from '@/lib/types'

interface LandStatusBadgeProps {
  status?: LandStatus
  jobStatus?: JobStatus
  size?: 'sm' | 'md' | 'lg'
}

export function LandStatusBadge({ status, jobStatus, size = 'md' }: LandStatusBadgeProps) {
  if (!status) {
    const isProcessing = jobStatus === 'running'
    const isQueued = jobStatus === 'queued'
    const isFailed = jobStatus === 'failed'

    return (
      <span className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full border font-medium',
        size === 'sm' && 'text-xs',
        size === 'md' && 'text-xs',
        size === 'lg' && 'text-sm',
        isProcessing && 'bg-indigo-50 text-indigo-700 border-indigo-200',
        isQueued     && 'bg-gray-100 text-gray-600 border-gray-200',
        isFailed     && 'bg-red-50 text-red-700 border-red-200',
      )}>
        {isProcessing && <span className="material-symbols-outlined text-xs animate-spin">progress_activity</span>}
        {isQueued     && <span className="material-symbols-outlined text-xs">schedule</span>}
        {isFailed     && <span className="material-symbols-outlined text-xs">error</span>}
        {isProcessing ? 'Processing' : isQueued ? 'Queued' : 'Failed'}
      </span>
    )
  }

  return (
    <span className={clsx(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full border font-medium',
      size === 'sm' && 'text-xs',
      size === 'md' && 'text-xs',
      size === 'lg' && 'text-sm px-3 py-1',
      LAND_STATUS_COLORS[status],
    )}>
      {LAND_STATUS_LABELS[status]}
    </span>
  )
}

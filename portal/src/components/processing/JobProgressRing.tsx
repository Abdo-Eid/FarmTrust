import { ProgressRing } from '@/components/ui/ProgressRing'
import type { JobStatus } from '@/lib/types'

interface JobProgressRingProps {
  percent: number
  status: JobStatus
  phase?: string
  sceneProgress?: string
}

export function JobProgressRing({ percent, status, phase, sceneProgress }: JobProgressRingProps) {
  const color =
    status === 'succeeded'  ? '#22c55e' :
    status === 'failed'     ? '#ef4444' :
    status === 'cancelled'  ? '#94a3b8' :
    status === 'queued'     ? '#94a3b8' :
    '#1abc9c'

  const label =
    status === 'queued'    ? 'QUEUED' :
    status === 'failed'    ? 'FAILED' :
    status === 'cancelled' ? 'STOPPED' :
    status === 'succeeded' ? '100%' :
    `${percent}%`

  const sublabel =
    status === 'running'   ? 'Running...' :
    status === 'queued'    ? 'Waiting for worker' :
    status === 'succeeded' ? 'Complete' :
    status === 'failed'    ? 'Error' :
    status === 'cancelled' ? 'Cancelled' :
    undefined

  return (
    <div className="flex flex-col items-center gap-4">
      <ProgressRing
        percent={status === 'succeeded' ? 100 : status === 'queued' || status === 'cancelled' ? 0 : percent}
        size={200}
        strokeWidth={12}
        label={label}
        sublabel={sublabel}
        color={color}
      />
      {phase && status === 'running' && (
        <p className="text-xs text-gray-500 text-center">
          Current phase: <span className="font-medium text-gray-700">{phase}</span>
        </p>
      )}
      {sceneProgress && status === 'running' && phase === 'satellite_fetch' && (
        <p className="text-xs text-teal-600 text-center font-medium">
          {sceneProgress}
        </p>
      )}
    </div>
  )
}

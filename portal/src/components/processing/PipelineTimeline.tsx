import { clsx } from 'clsx'
import { PIPELINE_PHASES, PHASE_ORDER } from '@/lib/constants'
import type { JobPhase, JobStatus } from '@/lib/types'
import { format } from 'date-fns'

interface PipelineTimelineProps {
  status: JobStatus
  currentPhase?: JobPhase
  startedAt?: string
  completedAt?: string
}

export function PipelineTimeline({ status, currentPhase, startedAt, completedAt }: PipelineTimelineProps) {
  const currentIdx = currentPhase ? PHASE_ORDER.indexOf(currentPhase) : -1

  return (
    <div className="space-y-0">
      {PIPELINE_PHASES.map((phase, idx) => {
        const isDone      = status === 'succeeded' || idx < currentIdx
        const isCancelled = status === 'cancelled' && idx === currentIdx
        const isCurrent   = status === 'running' && idx === currentIdx
        const isPending   = !isDone && !isCurrent && !isCancelled

        return (
          <div key={phase.phase} className="flex items-stretch gap-4">
            {/* Timeline line + icon */}
            <div className="flex flex-col items-center">
              <div className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border-2 z-10',
                isDone      && 'bg-green-500 border-green-500',
                isCurrent   && 'bg-teal-600 border-teal-600 ring-4 ring-teal-100',
                isCancelled && 'bg-gray-400 border-gray-400',
                isPending   && 'bg-white border-gray-200',
              )}>
                {isDone ? (
                  <span className="material-symbols-outlined text-white text-sm">check</span>
                ) : isCurrent ? (
                  <span className="material-symbols-outlined text-white text-sm animate-spin">progress_activity</span>
                ) : isCancelled ? (
                  <span className="material-symbols-outlined text-white text-sm">stop</span>
                ) : (
                  <span className="material-symbols-outlined text-gray-300 text-sm">{phase.icon}</span>
                )}
              </div>
              {idx < PIPELINE_PHASES.length - 1 && (
                <div className={clsx(
                  'w-0.5 flex-1 min-h-[2rem]',
                  isDone ? 'bg-green-300' : 'bg-gray-200'
                )} />
              )}
            </div>

            {/* Label */}
            <div className="pb-5 flex-1">
              <p className={clsx(
                'text-sm font-medium',
                isDone      && 'text-gray-700',
                isCurrent   && 'text-teal-700',
                isCancelled && 'text-gray-500',
                isPending   && 'text-gray-400',
              )}>
                {phase.label}
              </p>
              {isDone && idx === 0 && startedAt && (
                <p className="text-xs text-gray-400">{format(new Date(startedAt), 'HH:mm:ss')}</p>
              )}
              {isDone && idx === PIPELINE_PHASES.length - 1 && completedAt && (
                <p className="text-xs text-gray-400">Completed {format(new Date(completedAt), 'HH:mm:ss')}</p>
              )}
              {isCurrent && (
                <p className="text-xs text-teal-500 mt-0.5">In progress...</p>
              )}
              {isCancelled && (
                <p className="text-xs text-gray-400 mt-0.5">Stopped by user</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

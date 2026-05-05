import { clsx } from 'clsx'
import {
  CONFIDENCE_LABELS,
  CONFIDENCE_BORDER_COLORS,
  CONFIDENCE_BG_COLORS,
} from '@/lib/constants'
import type { Confidence } from '@/lib/types'

interface ConfidenceBandProps {
  confidence: Confidence
}

export function ConfidenceBand({ confidence }: ConfidenceBandProps) {
  return (
    <div
      className={clsx(
        'border-l-4 pl-4 pr-3 py-3 rounded-r-md',
        CONFIDENCE_BORDER_COLORS[confidence.status],
        CONFIDENCE_BG_COLORS[confidence.status],
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={clsx(
          'text-xs font-semibold uppercase tracking-wide',
          confidence.status === 'high'   && 'text-green-700',
          confidence.status === 'medium' && 'text-amber-700',
          confidence.status === 'low'    && 'text-red-700',
        )}>
          {CONFIDENCE_LABELS[confidence.status]}
        </span>
      </div>
      <p className="text-xs text-gray-600 leading-relaxed">{confidence.rationale}</p>
    </div>
  )
}

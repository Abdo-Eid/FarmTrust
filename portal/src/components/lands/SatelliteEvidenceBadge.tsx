import { clsx } from 'clsx'
import { SATELLITE_EVIDENCE_COLORS, SATELLITE_EVIDENCE_LABELS } from '@/lib/constants'
import type { SatelliteEvidenceCoverage } from '@/lib/types'

interface SatelliteEvidenceBadgeProps {
  coverage?: SatelliteEvidenceCoverage
  showRationale?: boolean
}

export function SatelliteEvidenceBadge({ coverage, showRationale = false }: SatelliteEvidenceBadgeProps) {
  if (!coverage) return <span className="text-gray-300 text-xs">—</span>

  return (
    <div className="space-y-1">
      <span className={clsx(
        'inline-flex px-2 py-0.5 rounded-full border text-xs font-medium',
        SATELLITE_EVIDENCE_COLORS[coverage.status],
      )}>
        {SATELLITE_EVIDENCE_LABELS[coverage.status]}
      </span>
      {showRationale && (
        <p className="text-xs text-gray-600 leading-relaxed">{coverage.rationale}</p>
      )}
    </div>
  )
}

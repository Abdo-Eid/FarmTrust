import { ConfidenceBand } from '@/components/lands/ConfidenceBand'
import type { Confidence } from '@/lib/types'

interface ConfidenceSectionProps {
  confidence: Confidence
}

export function ConfidenceSection({ confidence }: ConfidenceSectionProps) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Assessment Confidence</p>
      <ConfidenceBand confidence={confidence} />
    </div>
  )
}

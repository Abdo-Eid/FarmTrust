import { clsx } from 'clsx'
import {
  LAND_STATUS_LABELS, LAND_STATUS_COLORS,
  SEASON_LABELS, SEASON_COLORS,
  RISK_TIER_LABELS, RISK_TIER_COLORS,
} from '@/lib/constants'
import { TrendIndicator } from '@/components/lands/TrendIndicator'
import type { LandResult } from '@/lib/types'

interface DecisionBriefProps {
  land: LandResult
}

export function DecisionBrief({ land }: DecisionBriefProps) {
  const { land_status, trend_2y, season_performance, risk_tier } = land
  const requiresManualReview = land.assessment_status === 'manual_review_required'

  return (
    <div className="bg-white border border-gray-200 rounded-md shadow-panel overflow-hidden">
      {/* Primary status — full width, prominent */}
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-start gap-6 flex-wrap">
          {/* Land Status — largest, most prominent */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Land Status</p>
            {requiresManualReview ? (
              <span className="inline-flex items-center px-4 py-1.5 rounded-full border text-sm font-semibold bg-amber-50 text-amber-800 border-amber-200">
                Manual Review Required
              </span>
            ) : land_status ? (
              <span className={clsx(
                'inline-flex items-center px-4 py-1.5 rounded-full border text-sm font-semibold',
                LAND_STATUS_COLORS[land_status]
              )}>
                {LAND_STATUS_LABELS[land_status]}
              </span>
            ) : (
              <span className="text-gray-400 text-sm">—</span>
            )}
          </div>

          <div className="w-px h-10 bg-gray-100 self-center" />

          {/* 2-Year Trend */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">2-Year Trend</p>
            {requiresManualReview ? (
              <span className="text-gray-400 text-sm">Not issued</span>
            ) : trend_2y ? (
              <TrendIndicator trend={trend_2y} size="md" />
            ) : (
              <span className="text-gray-400 text-sm">—</span>
            )}
          </div>

          <div className="w-px h-10 bg-gray-100 self-center" />

          {/* Activity Window Performance */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Last Activity Window</p>
            {requiresManualReview ? (
              <span className="text-gray-400 text-sm">Not issued</span>
            ) : season_performance ? (
              <span className={clsx(
                'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium',
                SEASON_COLORS[season_performance]
              )}>
                {SEASON_LABELS[season_performance]}
              </span>
            ) : (
              <span className="text-gray-400 text-sm">—</span>
            )}
          </div>

          <div className="w-px h-10 bg-gray-100 self-center" />

          {/* Risk Tier */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Risk Tier</p>
            {requiresManualReview ? (
              <span className="text-gray-400 text-sm">Not issued</span>
            ) : risk_tier ? (
              <span className={clsx(
                'inline-flex items-center px-3 py-1 rounded-full border text-xs font-semibold',
                RISK_TIER_COLORS[risk_tier]
              )}>
                {RISK_TIER_LABELS[risk_tier]}
              </span>
            ) : (
              <span className="text-gray-400 text-sm">—</span>
            )}
          </div>
        </div>
      </div>

      {/* Interpretation note */}
      <div className="px-6 py-3 bg-gray-50">
        <p className="text-xs text-gray-500">
          {requiresManualReview
            ? 'Satellite evidence is insufficient for a final automated assessment. Manual review is required.'
            : 'Decision-support outputs derived from the satellite observation window.'}
          {!requiresManualReview && risk_tier === 'low' && ' No current risk flags were issued by the assessment.'}
          {!requiresManualReview && risk_tier === 'medium' && ' Review risk flags and evidence limitations before making external decisions.'}
          {!requiresManualReview && risk_tier === 'high' && ' Additional review is recommended before relying on this assessment.'}
        </p>
      </div>
    </div>
  )
}

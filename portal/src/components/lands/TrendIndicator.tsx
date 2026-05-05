import { clsx } from 'clsx'
import { TREND_LABELS, TREND_ICONS, TREND_COLORS } from '@/lib/constants'
import type { Trend2Y } from '@/lib/types'

interface TrendIndicatorProps {
  trend: Trend2Y
  size?: 'sm' | 'md'
}

export function TrendIndicator({ trend, size = 'md' }: TrendIndicatorProps) {
  return (
    <span className={clsx('inline-flex items-center gap-1 font-medium', TREND_COLORS[trend])}>
      <span className={clsx(
        'material-symbols-outlined',
        size === 'sm' ? 'text-sm' : 'text-base'
      )}>
        {TREND_ICONS[trend]}
      </span>
      <span className={size === 'sm' ? 'text-xs' : 'text-sm'}>
        {TREND_LABELS[trend]}
      </span>
    </span>
  )
}

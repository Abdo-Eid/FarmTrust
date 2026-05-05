import type { Indicators } from '@/lib/types'

interface IndicatorsGridProps {
  indicators: Indicators
}

const NEIGHBOR_LABELS = {
  above_avg: 'Above District Avg',
  avg:       'At District Avg',
  below_avg: 'Below District Avg',
} as const

const NEIGHBOR_COLORS = {
  above_avg: 'text-green-600',
  avg:       'text-amber-600',
  below_avg: 'text-red-600',
} as const

interface IndicatorCellProps {
  label: string
  value: React.ReactNode
  unit?: string
  icon: string
}

function IndicatorCell({ label, value, unit, icon }: IndicatorCellProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
      <div className="flex items-center gap-2 mb-2">
        <span className="material-symbols-outlined text-gray-400 text-base">{icon}</span>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-bold text-gray-900">{value}</span>
        {unit && <span className="text-xs text-gray-400">{unit}</span>}
      </div>
    </div>
  )
}

export function IndicatorsGrid({ indicators }: IndicatorsGridProps) {
  const neighbor = indicators.neighbor_comparison
  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Key Indicators</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <IndicatorCell
          label="NDVI Peak"
          value={indicators.ndvi_peak?.toFixed(2) ?? '—'}
          icon="eco"
        />
        <IndicatorCell
          label="Vegetation AUC"
          value={indicators.ndvi_auc?.toFixed(1) ?? '—'}
          unit="(24mo)"
          icon="show_chart"
        />
        <IndicatorCell
          label="Cloud-Free Scenes"
          value={indicators.cloud_free_scenes ?? '—'}
          unit="scenes"
          icon="cloud_off"
        />
        <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-gray-400 text-base">compare</span>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">vs. Neighbors</p>
          </div>
          <p className={`text-sm font-semibold ${neighbor ? NEIGHBOR_COLORS[neighbor] : 'text-gray-400'}`}>
            {neighbor ? NEIGHBOR_LABELS[neighbor] : '—'}
          </p>
        </div>
      </div>
    </div>
  )
}

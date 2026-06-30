import type { Indicators } from '@/lib/types'

interface IndicatorsGridProps {
  indicators: Indicators
}

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
          label="NDVI p95 Peak"
          value={indicators.ndvi_p95_peak?.toFixed(2) ?? '—'}
          icon="stacked_line_chart"
        />
        <IndicatorCell
          label="Field Spread"
          value={indicators.ndvi_spread_median?.toFixed(2) ?? '—'}
          icon="grain"
        />
        <IndicatorCell
          label="Vegetation AUC"
          value={indicators.ndvi_auc?.toFixed(1) ?? '—'}
          unit="(24mo)"
          icon="show_chart"
        />
        <IndicatorCell
          label="EVI Confirmation"
          value={indicators.evi_peak?.toFixed(2) ?? '—'}
          icon="verified"
        />
        <IndicatorCell
          label="Moisture Signal"
          value={indicators.ndmi_median?.toFixed(2) ?? '—'}
          icon="water_drop"
        />
        <IndicatorCell
          label="Surface-Water Signal"
          value={indicators.mndwi_median?.toFixed(2) ?? '—'}
          icon="waves"
        />
        <IndicatorCell
          label="Cloud-Free Scenes"
          value={indicators.cloud_free_scenes ?? '—'}
          unit="scenes"
          icon="cloud_off"
        />
        <IndicatorCell
          label="Observation Coverage"
          value={
            indicators.observation_coverage !== undefined
              ? `${(indicators.observation_coverage * 100).toFixed(1)}`
              : '—'
          }
          unit="%"
          icon="fact_check"
        />
      </div>
    </div>
  )
}

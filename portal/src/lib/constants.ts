import type { LandStatus, Trend2Y, SeasonPerformance, ConfidenceLevel, SatelliteEvidenceCoverageStatus, RiskTier, RiskFlag, JobPhase } from './types'

export const LAND_STATUS_LABELS: Record<LandStatus, string> = {
  active: 'Active',
  intermittent: 'Intermittent',
  inactive: 'Inactive',
  encroachment: 'Encroachment',
}

export const LAND_STATUS_COLORS: Record<LandStatus, string> = {
  active: 'bg-green-100 text-green-800 border-green-200',
  intermittent: 'bg-amber-100 text-amber-800 border-amber-200',
  inactive: 'bg-red-100 text-red-800 border-red-200',
  encroachment: 'bg-red-100 text-red-900 border-red-300',
}

export const TREND_LABELS: Record<Trend2Y, string> = {
  improving: 'Improving',
  stable: 'Stable',
  declining: 'Declining',
}

export const TREND_ICONS: Record<Trend2Y, string> = {
  improving: 'trending_up',
  stable: 'trending_flat',
  declining: 'trending_down',
}

export const TREND_COLORS: Record<Trend2Y, string> = {
  improving: 'text-green-600',
  stable: 'text-amber-600',
  declining: 'text-red-600',
}

export const SEASON_LABELS: Record<SeasonPerformance, string> = {
  good: 'Good',
  interrupted: 'Interrupted',
  weak: 'Weak',
}

export const SEASON_COLORS: Record<SeasonPerformance, string> = {
  good: 'bg-green-100 text-green-800',
  interrupted: 'bg-amber-100 text-amber-800',
  weak: 'bg-red-100 text-red-800',
}

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  high: 'High Assessment Confidence',
  medium: 'Medium Assessment Confidence',
  low: 'Low Assessment Confidence',
}

export const CONFIDENCE_BORDER_COLORS: Record<ConfidenceLevel, string> = {
  high: 'border-green-500',
  medium: 'border-amber-500',
  low: 'border-red-500',
}

export const CONFIDENCE_BG_COLORS: Record<ConfidenceLevel, string> = {
  high: 'bg-green-50',
  medium: 'bg-amber-50',
  low: 'bg-red-50',
}

export const SATELLITE_EVIDENCE_LABELS: Record<SatelliteEvidenceCoverageStatus, string> = {
  good: 'Good Coverage',
  fair: 'Fair Coverage',
  limited: 'Limited Coverage',
  insufficient: 'Insufficient Evidence',
}

export const SATELLITE_EVIDENCE_COLORS: Record<SatelliteEvidenceCoverageStatus, string> = {
  good: 'bg-green-100 text-green-800 border-green-200',
  fair: 'bg-blue-100 text-blue-800 border-blue-200',
  limited: 'bg-amber-100 text-amber-800 border-amber-200',
  insufficient: 'bg-red-100 text-red-800 border-red-200',
}

export const RISK_TIER_LABELS: Record<RiskTier, string> = {
  low: 'Low Risk',
  medium: 'Medium Risk',
  high: 'High Risk',
}

export const RISK_TIER_COLORS: Record<RiskTier, string> = {
  low: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  high: 'bg-red-100 text-red-800 border-red-200',
}

export const FLAG_LABELS: Record<RiskFlag, string> = {
  waterlogging: 'Waterlogging',
  salinity: 'Salinity',
  abandonment: 'Abandonment',
  encroachment: 'Encroachment',
}

export const FLAG_ICONS: Record<RiskFlag, string> = {
  waterlogging: 'water_drop',
  salinity: 'science',
  abandonment: 'grass',
  encroachment: 'warning',
}

export const PIPELINE_PHASES: Array<{ phase: JobPhase; label: string; icon: string }> = [
  { phase: 'aoi_validation',      label: 'AOI Validation',       icon: 'verified' },
  { phase: 'satellite_fetch',     label: 'Satellite Data Fetch',  icon: 'satellite_alt' },
  { phase: 'vegetation_analysis', label: 'Vegetation Analysis',   icon: 'eco' },
  { phase: 'risk_modeling',       label: 'Risk Modeling',         icon: 'analytics' },
  { phase: 'report_generation',   label: 'Report Generation',     icon: 'description' },
]

export const PHASE_ORDER: JobPhase[] = [
  'aoi_validation',
  'satellite_fetch',
  'vegetation_analysis',
  'risk_modeling',
  'report_generation',
]

export const GOVERNORATES = [
  'Alexandria', 'Aswan', 'Asyut', 'Beheira', 'Beni Suef',
  'Cairo', 'Dakahlia', 'Damietta', 'Faiyum', 'Gharbia',
  'Giza', 'Ismailia', 'Kafr el-Sheikh', 'Luxor', 'Matruh',
  'Minya', 'Monufia', 'New Valley', 'North Sinai', 'Port Said',
  'Qalyubia', 'Qena', 'Red Sea', 'Sharqia', 'Sohag',
  'South Sinai', 'Suez',
]

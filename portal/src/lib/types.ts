export type LandStatus = 'active' | 'intermittent' | 'inactive' | 'encroachment'
export type Trend2Y = 'improving' | 'stable' | 'declining'
export type SeasonPerformance = 'good' | 'interrupted' | 'weak'
export type ConfidenceLevel = 'high' | 'medium' | 'low'
export type RiskTier = 'low' | 'medium' | 'high'
export type RiskFlag = 'waterlogging' | 'salinity' | 'abandonment' | 'encroachment'
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'
export type JobPhase = 'aoi_validation' | 'satellite_fetch' | 'vegetation_analysis' | 'risk_modeling' | 'report_generation'

export interface Confidence {
  status: ConfidenceLevel
  rationale: string
}

export interface Indicators {
  ndvi_peak?: number
  ndvi_auc?: number
  cloud_free_scenes?: number
  neighbor_comparison?: 'above_avg' | 'avg' | 'below_avg'
  observation_coverage?: number
}

export interface NDVIPoint {
  date: string
  ndvi: number
  evi?: number
  cloud_coverage: number
  flag?: string
}

export interface SeasonRecord {
  season: string
  start_date: string
  end_date: string
  ndvi_peak: number
  outcome: SeasonPerformance
  anomaly?: string
}

export interface LandResult {
  id: string
  name: string
  governorate: string
  district?: string
  area_feddan: number
  submitted_at: string
  job_id: string
  job_status: JobStatus
  geometry?: GeoJSON.Geometry
  land_status?: LandStatus
  trend_2y?: Trend2Y
  season_performance?: SeasonPerformance
  flags?: RiskFlag[]
  confidence?: Confidence
  risk_tier?: RiskTier
  indicators?: Indicators
  report_summary?: string
  ndvi_series?: NDVIPoint[]
  season_records?: SeasonRecord[]
}

export interface JobState {
  id: string
  land_id: string
  status: JobStatus
  phase?: JobPhase
  progress: number
  started_at?: string
  completed_at?: string
  error?: string
  logs: string[]
}

export interface User {
  id: string
  name: string
  email: string
  institution: string
  role: 'analyst' | 'admin'
  status: 'active' | 'suspended'
  last_login?: string
}

export interface Column<T> {
  key: keyof T | string
  label: string
  sortable?: boolean
  render?: (value: unknown, row: T) => React.ReactNode
  width?: string
}

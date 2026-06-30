import type { LandGeoJSON } from "./geo";

export type LandStatus =
    | "active"
    | "intermittent"
    | "inactive"
    | "encroachment";
export type Trend2Y = "improving" | "stable" | "declining";
export type SeasonPerformance = "good" | "interrupted" | "weak";
export type AssessmentStatus = "complete" | "manual_review_required";
export type ConfidenceLevel = "high" | "medium" | "low";
export type SatelliteEvidenceCoverageStatus =
    | "good"
    | "fair"
    | "limited"
    | "insufficient";
export type RiskTier = "low" | "medium" | "high";
export type RiskFlag =
    | "waterlogging"
    | "salinity"
    | "abandonment"
    | "encroachment";
export type JobStatus =
    | "queued"
    | "running"
    | "succeeded"
    | "failed"
    | "cancelled";
export type JobPhase =
    | "aoi_validation"
    | "satellite_fetch"
    | "vegetation_analysis"
    | "risk_modeling"
    | "report_generation";

export interface Confidence {
    status: ConfidenceLevel;
    rationale: string;
}

export interface SatelliteEvidenceCoverage {
    status: SatelliteEvidenceCoverageStatus;
    rationale: string;
}

export interface Indicators {
    ndvi_peak?: number;
    ndvi_p95_peak?: number;
    ndvi_spread_median?: number;
    ndvi_auc?: number;
    evi_peak?: number;
    ndmi_median?: number;
    mndwi_median?: number;
    cloud_free_scenes?: number;
    observation_coverage?: number;
}

export interface NDVIPoint {
    date: string;
    ndvi: number;
    evi?: number;
    cloud_coverage: number;
    flag?: string;
}

export interface SeasonRecord {
    season: string;
    start_date: string;
    end_date: string;
    ndvi_peak: number;
    outcome: SeasonPerformance;
    anomaly?: string;
}

export type AOIMethod = "polygon";

export interface CreateLandPayload {
    name: string;
    governorate: string;
    district?: string;
    notes?: string;
    method: AOIMethod;
    geometry: LandGeoJSON;
    area_feddan: number;
    lookback_days?: number;
}

export interface LandResult {
    id: string;
    name: string;
    governorate: string;
    district?: string;
    area_feddan: number;
    submitted_at: string;
    job_id: string;
    job_status: JobStatus;
    assessment_status?: AssessmentStatus;
    geometry?: GeoJSON.Geometry;
    land_status?: LandStatus;
    trend_2y?: Trend2Y;
    season_performance?: SeasonPerformance;
    flags?: RiskFlag[];
    satellite_evidence_coverage?: SatelliteEvidenceCoverage;
    confidence?: Confidence;
    risk_tier?: RiskTier;
    indicators?: Indicators;
    report_summary?: string;
    ndvi_series?: NDVIPoint[];
    season_records?: SeasonRecord[];
}

export interface LandGroupResult {
    id: string;
    name: string;
    governorate: string;
    district?: string;
    notes?: string;
    area_feddan: number;
    submitted_at: string;
    job_id: string;
    primary_land_id: string;
    aoi_count: number;
    job_status: JobStatus;
    assessment_status?: AssessmentStatus;
    land_status?: LandStatus;
    trend_2y?: Trend2Y;
    season_performance?: SeasonPerformance;
    risk_tier?: RiskTier;
    confidence?: Confidence;
    satellite_evidence_coverage?: SatelliteEvidenceCoverage;
    children: LandResult[];
}

export interface JobState {
    id: string;
    land_id: string;
    status: JobStatus;
    phase?: JobPhase;
    progress: number;
    scene_total?: number;
    scene_done?: number;
    started_at?: string;
    completed_at?: string;
    error?: string;
    logs: string[];
}

export interface Column<T> {
    key: keyof T | string;
    label: string;
    sortable?: boolean;
    render?: (value: unknown, row: T) => React.ReactNode;
    width?: string;
}

// --- Report evidence packet (T-11 Layer 5/6) ---------------------------------

export type ClaimLayer = "observed" | "interpreted" | "confidence" | "watch";
export type ClaimConfidence =
    | "strong"
    | "moderate"
    | "limited"
    | "provisional"
    | "none";
export type RiskKind = "land_risk" | "evidence_limitation";
export type RiskSeverity = "high" | "moderate" | "low";
export type TrackStatus =
    | "improving"
    | "declining"
    | "stable"
    | "too_soon_to_tell";

export type ClaimType =
    | "measured_observation"
    | "deterministic_pipeline_result"
    | "model_derived_analysis"
    | "interpretation"
    | "boundary_exclusion"
    | "user_provided_local_context"
    | "unknown";

export interface PacketClaim {
    id: string;
    layer: ClaimLayer;
    claim: string;
    confidence: ClaimConfidence;
    rests_on: string;
    // Per-claim provenance (packet v1.1) — optional; consumed by the assistant.
    claim_type?: ClaimType;
    provenance_level?: number;
    source?: string;
    method?: string;
    allowed_use?: string[];
    restriction?: string;
}

export interface PacketCycle {
    season_id?: string;
    start_date?: string;
    peak_date?: string;
    end_date?: string;
    season_calendar_label?: string;
    lifecycle_status?: string;
    is_open?: boolean;
    peak_ndvi?: number;
    duration_days?: number;
    detection_status?: string;
    cycle_split_merged?: boolean;
}

export interface PacketActivityRecord {
    cycles: PacketCycle[];
    complete_window_count: number;
    open_window_count: number;
    borderline_window_count: number;
}

export interface PacketTrackRecord {
    seasons_observed: number;
    seasons_for_certifiable_trend: number;
    fraction: number;
    status_so_far: TrackStatus;
    provisional: boolean;
    note: string;
}

export interface PacketRiskItem {
    item: string;
    kind: RiskKind;
    severity: RiskSeverity;
    reason: string;
    code?: string;
}

export interface PacketHeadline {
    state_label: string;
    cropping_intensity?: string;
    overall_confidence: ConfidenceLevel;
    summary: string;
}

export interface PacketIndicators {
    values: Record<string, number | null>;
    interpretation_notes: Record<string, string>;
}

// --- Bounded report assistant (T-04 / T-11 Layer 7) --------------------------

export interface AssistantLine {
    text: string;
    claim_type: string;
    source?: string;
    confidence?: string;
    section?: string;
}

export interface AssistantResponse {
    lines: AssistantLine[];
    source_mode: "llm" | "deterministic";
    fallback_used: boolean;
    model?: string;
}

export interface ChatTurn {
    role: "user" | "assistant";
    content: string;
}

export interface ChatRequest {
    question: string;
    history?: ChatTurn[];
}

export interface EvidencePacket {
    packet_version: string;
    schema: string;
    aoi_id: string;
    assessment_status?: AssessmentStatus;
    source_artifacts: string[];
    interval: {
        start_date?: string;
        end_date?: string;
        duration_days?: number;
    };
    headline: PacketHeadline;
    claims: PacketClaim[];
    layers: Record<string, string[]>;
    activity_record: PacketActivityRecord;
    track_record: PacketTrackRecord;
    risk_register: PacketRiskItem[];
    limitations: string[];
    boundaries: string[];
    indicators: PacketIndicators;
    local_context: unknown[];
}

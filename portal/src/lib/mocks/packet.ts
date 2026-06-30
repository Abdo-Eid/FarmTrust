import type {
    ClaimConfidence,
    ClaimType,
    ConfidenceLevel,
    EvidencePacket,
    LandResult,
    PacketClaim,
    PacketCycle,
    PacketRiskItem,
    TrackStatus,
} from "../types";

// Derives a faithful evidence packet from a mock land so the report card (and
// later the assistant) demo across every land state with no backend. Kept in
// sync with the mock lands by construction rather than hand-authored per land.

const BOUNDARIES = [
    "Harvested yield, tonnage, or output volume",
    "Price, revenue, input costs, or net income",
    "Water rights or allocation",
    "Ownership, title, or legal status",
    "Crop identity (not proven from satellite)",
    "Pest, disease, or in-field damage",
];

const INDICATOR_NOTES: Record<string, string> = {
    ndvi_peak: "Peak canopy greenness. A vigour signal, not a yield or income measure.",
    ndvi_p95_peak: "Greenness of the densest pixels. Reads canopy density, not output.",
    ndvi_spread_median: "Within-field greenness spread. A field-uniformity signal, not a crop-split proof.",
    evi_peak: "Enhanced vegetation index peak. Corroborates the NDVI cycle.",
    ndmi_median: "Canopy-moisture signal. Context only, not an irrigation or water-right claim.",
    mndwi_median: "Surface-water signal. Staying low rules out a standing-water/flood read.",
};

const STRENGTH: Record<ConfidenceLevel, ClaimConfidence> = {
    high: "strong",
    medium: "moderate",
    low: "limited",
};

const TREND_TO_STATUS: Record<string, TrackStatus> = {
    improving: "improving",
    declining: "declining",
    stable: "stable",
};

function calendarLabel(dateStr?: string): string {
    if (!dateStr) return "transition";
    const m = new Date(dateStr).getUTCMonth() + 1;
    return m >= 5 && m <= 10 ? "summer" : "winter";
}

function stateLabel(land: LandResult, seasons: number): string {
    switch (land.land_status) {
        case "active":
            return seasons >= 2 ? "Active — multiple cycles observed" : "Active — limited history";
        case "intermittent":
            return "Intermittent activity";
        case "inactive":
            return "Low activity — absence-gated";
        case "encroachment":
            return "Possible land-use change";
        default:
            return "Not assessed — satellite evidence insufficient";
    }
}

function severityFromTier(land: LandResult): PacketRiskItem["severity"] {
    return land.risk_tier === "high" ? "high" : land.risk_tier === "medium" ? "moderate" : "low";
}

function titleCase(s: string): string {
    return s.replace(/_/g, " ").replace(/^./, (m) => m.toUpperCase());
}

// Mirrors farmtrust_core.report.evidence_packet._provenance_for so demo lands
// carry the same per-claim claim_type the backend attaches (packet v1.1).
const CLAIM_TYPE_BY_ID: Record<string, ClaimType> = {
    observation_coverage: "measured_observation",
    activity_cycles_observed: "deterministic_pipeline_result",
    cycle_lifecycle_observed: "model_derived_analysis",
    calendar_pattern_observed: "model_derived_analysis",
    no_cycle_observed: "deterministic_pipeline_result",
    worked_field_interpreted: "interpretation",
    intermittent_interpreted: "interpretation",
    idle_interpreted: "interpretation",
    unclear_interpreted: "interpretation",
    conf_active_cultivation: "deterministic_pipeline_result",
    conf_stability: "model_derived_analysis",
    conf_crop_identity: "boundary_exclusion",
    conf_yield: "boundary_exclusion",
    watch_short_record: "measured_observation",
    watch_yield_invisible: "boundary_exclusion",
};
const LAYER_DEFAULT_TYPE: Record<string, ClaimType> = {
    observed: "measured_observation",
    interpreted: "interpretation",
    confidence: "deterministic_pipeline_result",
    watch: "deterministic_pipeline_result",
};
function claimTypeFor(id: string, layer: string): ClaimType {
    if (CLAIM_TYPE_BY_ID[id]) return CLAIM_TYPE_BY_ID[id];
    if (id.startsWith("watch_")) return "deterministic_pipeline_result";
    return LAYER_DEFAULT_TYPE[layer] ?? "unknown";
}

export function mockEvidencePacket(land: LandResult): EvidencePacket {
    const seasons = land.season_records ?? [];
    const seasonCount = seasons.length;
    const conf: ConfidenceLevel = land.confidence?.status ?? "medium";
    const baseStrength = STRENGTH[conf];
    const coverage = land.satellite_evidence_coverage?.status ?? "fair";
    const flags = land.flags ?? [];
    const ind = land.indicators;

    const cycles: PacketCycle[] = seasons.map((s, i) => {
        const start = new Date(s.start_date).getTime();
        const end = new Date(s.end_date).getTime();
        return {
            season_id: `season_0${i + 1}`,
            start_date: s.start_date,
            peak_date: new Date((start + end) / 2).toISOString().slice(0, 10),
            end_date: s.end_date,
            season_calendar_label: calendarLabel(s.start_date),
            lifecycle_status: "complete",
            is_open: false,
            peak_ndvi: s.ndvi_peak,
            duration_days: Math.round((end - start) / 86_400_000),
            detection_status: "confirmed",
            cycle_split_merged: false,
        };
    });

    const claims: PacketClaim[] = [];
    const dur = seasonCount >= 2 ? "2-year" : "observed";

    // Observed
    claims.push({
        id: "observation_coverage",
        layer: "observed",
        claim: `Satellite observation coverage over the ${dur} window is ${coverage}.`,
        confidence: baseStrength,
        rests_on: land.satellite_evidence_coverage?.rationale ?? "",
    });
    if (seasonCount > 0) {
        claims.push({
            id: "activity_cycles_observed",
            layer: "observed",
            claim: `Greenness completed ${seasonCount} vegetation activity cycle(s), each rising from and returning toward a low baseline.`,
            confidence: coverage === "good" || coverage === "fair" ? "strong" : "moderate",
            rests_on: `${ind?.cloud_free_scenes ?? "Multiple"} clean observations.`,
        });
        const labels = Array.from(new Set(cycles.map((c) => c.season_calendar_label)));
        if (labels.length) {
            claims.push({
                id: "calendar_pattern_observed",
                layer: "observed",
                claim: `Cycle peaks fall in ${labels.join(", ")} months of the year.`,
                confidence: "moderate",
                rests_on: "Peak-month mapping to a broad regional calendar; a summer/winter descriptor only, not a crop label.",
            });
        }
    } else {
        claims.push({
            id: "no_cycle_observed",
            layer: "observed",
            claim: "No clear vegetation activity cycle was detected in the observed window.",
            confidence: baseStrength,
            rests_on: land.report_summary ?? "",
        });
    }

    // Interpreted
    if (land.land_status === "active") {
        claims.push({
            id: "worked_field_interpreted",
            layer: "interpreted",
            claim: "The greenness rhythm is consistent with a worked, actively cropped field — not idle or abandoned ground.",
            confidence: "moderate",
            rests_on: "Recent vegetation activity observed.",
        });
    } else if (land.land_status === "intermittent") {
        claims.push({
            id: "intermittent_interpreted",
            layer: "interpreted",
            claim: "Activity appears intermittent across the window rather than continuous.",
            confidence: baseStrength,
            rests_on: land.confidence?.rationale ?? "",
        });
    } else if (land.land_status === "inactive") {
        claims.push({
            id: "idle_interpreted",
            layer: "interpreted",
            claim: "Sustained low greenness is consistent with idle or fallow ground — which is not the same as abandonment.",
            confidence: baseStrength,
            rests_on: land.confidence?.rationale ?? "",
        });
    } else {
        claims.push({
            id: "unclear_interpreted",
            layer: "interpreted",
            claim: "A non-vegetated or land-use-change signal is present and needs external verification.",
            confidence: "limited",
            rests_on: land.report_summary ?? "",
        });
    }

    // Confidence
    if (land.land_status === "active" || land.land_status === "intermittent") {
        claims.push({
            id: "conf_active_cultivation",
            layer: "confidence",
            claim: "Confidence that the land is actively cultivated.",
            confidence: baseStrength,
            rests_on: `${coverage} coverage.`,
        });
    }
    claims.push({
        id: "conf_stability",
        layer: "confidence",
        claim: "Confidence in multi-year stability or trend.",
        confidence: seasonCount >= 5 ? "moderate" : "provisional",
        rests_on: "Short record; treat stability as provisional until a longer record accrues.",
    });
    claims.push({
        id: "conf_crop_identity",
        layer: "confidence",
        claim: "Confidence in specific crop identity.",
        confidence: "none",
        rests_on: "Crop identity is not inferred from the satellite signal.",
    });
    claims.push({
        id: "conf_yield",
        layer: "confidence",
        claim: "Confidence in yield, output, or income.",
        confidence: "none",
        rests_on: "Greenness is not yield; output and income are outside satellite scope.",
    });

    // Watch
    for (const f of flags) {
        claims.push({
            id: `watch_${f}`,
            layer: "watch",
            claim: `A ${titleCase(f).toLowerCase()} signal was flagged for review.`,
            confidence: "moderate",
            rests_on: `Risk flag: ${f}.`,
        });
    }
    if (seasonCount < 5) {
        claims.push({
            id: "watch_short_record",
            layer: "watch",
            claim: "The satellite track record is short, so one atypical season is hard to separate from normal year-to-year variation.",
            confidence: "moderate",
            rests_on: "Limited history.",
        });
    }
    if (seasonCount > 0) {
        claims.push({
            id: "watch_yield_invisible",
            layer: "watch",
            claim: "Yield, crop health, and pest or disease damage are not observable from greenness.",
            confidence: "none",
            rests_on: "Greenness is a canopy signal, not an output measure.",
        });
    }

    // Attach per-claim provenance (mirrors the backend post-pass).
    for (const c of claims) c.claim_type = claimTypeFor(c.id, c.layer);

    const layers: Record<string, string[]> = { observed: [], interpreted: [], confidence: [], watch: [] };
    for (const c of claims) layers[c.layer]?.push(c.id);

    const risk_register: PacketRiskItem[] = [
        ...flags.map((f) => ({
            item: titleCase(f),
            kind: "land_risk" as const,
            severity: severityFromTier(land),
            reason: `Flagged from the assessment (${f}).`,
            code: f,
        })),
        ...(seasonCount < 5
            ? [{
                  item: "Short satellite record",
                  kind: "evidence_limitation" as const,
                  severity: "low" as const,
                  reason: "Track record is too short for a long-term claim.",
              }]
            : []),
        ...(coverage === "limited" || coverage === "insufficient"
            ? [{
                  item: "Gaps at key cycle stages",
                  kind: "evidence_limitation" as const,
                  severity: "moderate" as const,
                  reason: land.satellite_evidence_coverage?.rationale ?? "Observation gaps limit boundary evidence.",
              }]
            : []),
    ];

    const startDate = seasons[0]?.start_date;
    const endDate = seasons[seasons.length - 1]?.end_date;
    const fraction = Math.round(Math.min(seasonCount / 5, 1) * 1000) / 1000;
    const label = stateLabel(land, seasonCount);

    return {
        packet_version: "1.0",
        schema: "farmtrust_report_evidence_packet",
        aoi_id: land.id,
        assessment_status: land.assessment_status ?? "complete",
        source_artifacts: ["land_assessment.json", "season_windows.json", "quality_metrics.json", "run_metadata.json"],
        interval: {
            start_date: startDate,
            end_date: endDate,
            duration_days:
                startDate && endDate
                    ? Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86_400_000)
                    : undefined,
        },
        headline: {
            state_label: label,
            cropping_intensity: seasonCount > 0 ? `${seasonCount} observed cycle(s) (provisional)` : undefined,
            overall_confidence: conf,
            summary: `${label}. ${seasonCount} vegetation activity cycle(s) detected at ${conf} confidence. Evidence is satellite greenness only — not crop identity, yield, or financial outcome.`,
        },
        claims,
        layers,
        activity_record: {
            cycles,
            complete_window_count: cycles.length,
            open_window_count: 0,
            borderline_window_count: 0,
        },
        track_record: {
            seasons_observed: seasonCount,
            seasons_for_certifiable_trend: 5,
            fraction,
            status_so_far: TREND_TO_STATUS[land.trend_2y ?? ""] ?? "too_soon_to_tell",
            provisional: seasonCount < 5,
            note: `${seasonCount} of ~5 seasons toward a certifiable use-stability claim; treat stability as provisional until a longer record accrues.`,
        },
        risk_register,
        limitations: [
            "Cycle boundary dates are model-derived from a smoothed daily curve, not direct observations.",
            "Findings are from a single parcel's own history; there is no peer or neighbour baseline.",
            "Crop identity, rotation, and management are not inferred from the satellite signal alone.",
        ],
        boundaries: BOUNDARIES,
        indicators: {
            values: {
                ndvi_peak: ind?.ndvi_peak ?? null,
                ndvi_p95_peak: ind?.ndvi_p95_peak ?? null,
                ndvi_spread_median: ind?.ndvi_spread_median ?? null,
                evi_peak: ind?.evi_peak ?? null,
                ndmi_median: ind?.ndmi_median ?? null,
                mndwi_median: ind?.mndwi_median ?? null,
            },
            interpretation_notes: INDICATOR_NOTES,
        },
        local_context: [],
    };
}

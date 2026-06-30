import type {
    ClaimConfidence,
    ClaimLayer,
    ConfidenceLevel,
    RiskSeverity,
    TrackStatus,
} from "@/lib/types";

/** Visual vocabulary for the four evidence layers. */
export const LAYER_META: Record<
    ClaimLayer,
    { label: string; icon: string; blurb: string; border: string; bg: string; text: string; badge: string }
> = {
    observed: {
        label: "Observed",
        icon: "visibility",
        blurb: "What the satellite shows — measured or closely derived",
        border: "border-teal-600",
        bg: "bg-teal-50",
        text: "text-teal-700",
        badge: "bg-teal-100 text-teal-800 border-teal-200",
    },
    interpreted: {
        label: "Interpreted",
        icon: "lightbulb",
        blurb: "What the pattern may suggest — see per-item confidence",
        border: "border-indigo-600",
        bg: "bg-indigo-50",
        text: "text-indigo-700",
        badge: "bg-indigo-100 text-indigo-800 border-indigo-200",
    },
    confidence: {
        label: "Confidence",
        icon: "verified",
        blurb: "How sure — and on what basis",
        border: "border-amber-600",
        bg: "bg-amber-50",
        text: "text-amber-700",
        badge: "bg-amber-100 text-amber-800 border-amber-200",
    },
    watch: {
        label: "Watch",
        icon: "warning",
        blurb: "Caution — limits and caveats",
        border: "border-red-600",
        bg: "bg-red-50",
        text: "text-red-700",
        badge: "bg-red-100 text-red-800 border-red-200",
    },
};

export const LAYER_ORDER: ClaimLayer[] = ["observed", "interpreted", "confidence", "watch"];

/** Per-claim confidence pill colours. */
export const CONFIDENCE_PILL: Record<ClaimConfidence, string> = {
    strong: "bg-green-100 text-green-800 border-green-200",
    moderate: "bg-amber-100 text-amber-800 border-amber-200",
    limited: "bg-gray-100 text-gray-700 border-gray-200",
    provisional: "bg-slate-100 text-slate-700 border-slate-200",
    none: "bg-gray-50 text-gray-500 border-gray-200",
};

export const SEVERITY_PILL: Record<RiskSeverity, string> = {
    high: "bg-red-100 text-red-800 border-red-200",
    moderate: "bg-amber-100 text-amber-800 border-amber-200",
    low: "bg-gray-100 text-gray-700 border-gray-200",
};

export const OVERALL_CONFIDENCE_PILL: Record<ConfidenceLevel, string> = {
    high: "bg-green-100 text-green-800 border-green-200",
    medium: "bg-amber-100 text-amber-800 border-amber-200",
    low: "bg-red-100 text-red-800 border-red-200",
};

export const TRACK_STATUS_LABEL: Record<TrackStatus, string> = {
    improving: "Improving",
    declining: "Declining",
    stable: "Stable",
    too_soon_to_tell: "Too soon to tell",
};

/** Broad summer/winter calendar descriptors — NOT crop labels. */
export const CALENDAR_STYLE: Record<string, { fill: string; label: string }> = {
    summer: { fill: "#f59e0b", label: "Summer" },
    winter: { fill: "#1abc9c", label: "Winter" },
    transition: { fill: "#94a3b8", label: "Transition" },
};

export function calendarStyle(label?: string) {
    return (label && CALENDAR_STYLE[label]) || CALENDAR_STYLE.transition;
}

export const INDICATOR_LABEL: Record<string, string> = {
    ndvi_peak: "NDVI peak",
    ndvi_p95_peak: "NDVI p95 peak",
    ndvi_spread_median: "NDVI spread (median)",
    evi_peak: "EVI peak",
    ndmi_median: "NDMI (median)",
    mndwi_median: "MNDWI (median)",
};

export function humanizeKey(key: string): string {
    return INDICATOR_LABEL[key] ?? key.replace(/_/g, " ");
}

/** Claim-type pills for the assistant — provenance at a glance (T-04). */
export const CLAIM_TYPE_PILL: Record<string, string> = {
    measured_observation: "bg-green-100 text-green-800 border-green-200",
    deterministic_pipeline_result: "bg-teal-100 text-teal-800 border-teal-200",
    model_derived_analysis: "bg-indigo-100 text-indigo-800 border-indigo-200",
    interpretation: "bg-amber-100 text-amber-800 border-amber-200",
    boundary_exclusion: "bg-gray-800 text-gray-100 border-gray-700",
    user_provided_local_context: "bg-slate-100 text-slate-700 border-slate-200",
    unknown: "bg-gray-100 text-gray-600 border-gray-200",
};

export const CLAIM_TYPE_LABEL: Record<string, string> = {
    measured_observation: "Measured",
    deterministic_pipeline_result: "Pipeline",
    model_derived_analysis: "Model-derived",
    interpretation: "Interpretation",
    boundary_exclusion: "Out of scope",
    user_provided_local_context: "Local context",
    unknown: "Unknown",
};

export function claimTypePill(claimType?: string): string {
    return CLAIM_TYPE_PILL[claimType ?? "unknown"] ?? CLAIM_TYPE_PILL.unknown;
}

export function claimTypeLabel(claimType?: string): string {
    return CLAIM_TYPE_LABEL[claimType ?? "unknown"] ?? "Unknown";
}

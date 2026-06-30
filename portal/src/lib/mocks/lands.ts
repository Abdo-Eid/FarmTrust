import type { Indicators, LandResult, NDVIPoint, SeasonRecord } from "../types";

// Each completed mock land has ONE canonical source of truth: its season
// records (the activity cycles). Everything derived — the NDVI series shown on
// the evidence chart, the peak/p95/AUC indicators, and (via mockEvidencePacket)
// the report card — is computed from those cycles in `finalizeLand`, so every
// surface for a given land shows numbers that agree.

const RAW_MOCK_LANDS: LandResult[] = [
    {
        id: "land-001",
        name: "North Sharqia Plot A",
        governorate: "Sharqia",
        district: "Abu Hammad",
        area_feddan: 45,
        submitted_at: "2024-03-15T09:22:00Z",
        job_id: "job-001",
        job_status: "succeeded",
        land_status: "active",
        trend_2y: "improving",
        season_performance: "good",
        flags: [],
        satellite_evidence_coverage: {
            status: "good",
            rationale: "Dense usable satellite observations across the assessment window.",
        },
        geometry: {
            type: "Polygon",
            coordinates: [
                [
                    [31.25, 30.45],
                    [31.4, 30.45],
                    [31.4, 30.3],
                    [31.25, 30.3],
                    [31.25, 30.45],
                ],
            ],
        },
        confidence: {
            status: "high",
            rationale:
                "Dense cloud-free observations across detected activity windows with consistent NDVI trajectory.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_spread_median: 0.06,
            evi_peak: 0.55,
            ndmi_median: 0.18,
            mndwi_median: -0.32,
            cloud_free_scenes: 38,
            observation_coverage: 0.94,
        },
        report_summary:
            "This land parcel demonstrates sustained vegetation activity across the observed window. Detected activity windows are strong, and no current risk flags were identified.",
        season_records: [
            { season: "Activity window 2022/23 A", start_date: "2022-11-01", end_date: "2023-04-30", ndvi_peak: 0.75, outcome: "good" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.78, outcome: "good" },
            { season: "Activity window 2023/24 A", start_date: "2023-11-01", end_date: "2024-04-30", ndvi_peak: 0.81, outcome: "good" },
        ],
    },
    {
        id: "land-002",
        name: "Minya Central Basin",
        governorate: "Minya",
        district: "Mallawi",
        area_feddan: 120,
        submitted_at: "2024-03-10T14:05:00Z",
        job_id: "job-002",
        job_status: "succeeded",
        land_status: "intermittent",
        trend_2y: "stable",
        season_performance: "interrupted",
        flags: ["waterlogging"],
        satellite_evidence_coverage: {
            status: "fair",
            rationale: "Moderate cloud cover reduced observation density in part of the window.",
        },
        geometry: {
            type: "Polygon",
            coordinates: [
                [
                    [30.8, 28.5],
                    [30.95, 28.5],
                    [30.95, 28.35],
                    [30.8, 28.35],
                    [30.8, 28.5],
                ],
            ],
        },
        confidence: {
            status: "medium",
            rationale:
                "Moderate cloud cover in winter 2023 reduced observation density. Waterlogging signature visible in spring imagery.",
        },
        risk_tier: "medium",
        indicators: {
            ndvi_spread_median: 0.08,
            evi_peak: 0.42,
            ndmi_median: 0.24,
            mndwi_median: -0.18,
            cloud_free_scenes: 24,
            observation_coverage: 0.72,
        },
        report_summary:
            "Vegetation activity is intermittent with a wetness signal that requires review. The latest activity window showed an interruption-like signal, so interpretation should remain cautious.",
        season_records: [
            { season: "Activity window 2022/23 A", start_date: "2022-11-01", end_date: "2023-04-30", ndvi_peak: 0.63, outcome: "good" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.55, outcome: "interrupted", anomaly: "Mid-window NDVI drop, possible waterlogging" },
            { season: "Activity window 2023/24 A", start_date: "2023-11-01", end_date: "2024-04-30", ndvi_peak: 0.61, outcome: "interrupted" },
        ],
    },
    {
        id: "land-003",
        name: "Fayoum Depression East",
        governorate: "Faiyum",
        district: "Sinnuris",
        area_feddan: 80,
        submitted_at: "2024-02-28T11:30:00Z",
        job_id: "job-003",
        job_status: "succeeded",
        land_status: "inactive",
        trend_2y: "declining",
        season_performance: "weak",
        flags: ["abandonment", "salinity"],
        satellite_evidence_coverage: {
            status: "good",
            rationale: "High usable observation count supports the inactivity interpretation.",
        },
        confidence: {
            status: "high",
            rationale:
                "High observation density confirms absence of vegetation activity. Spectral signatures consistent with soil salinization.",
        },
        risk_tier: "high",
        indicators: {
            ndvi_spread_median: 0.07,
            evi_peak: 0.15,
            ndmi_median: -0.04,
            mndwi_median: -0.28,
            cloud_free_scenes: 41,
            observation_coverage: 0.96,
        },
        report_summary:
            "This parcel shows low vegetation activity across the observed window. NDVI values remain low, and available signals suggest stress or absence should be reviewed with sufficient history and field context.",
        season_records: [
            { season: "Activity window 2022/23 A", start_date: "2022-11-01", end_date: "2023-04-30", ndvi_peak: 0.38, outcome: "weak" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.25, outcome: "weak", anomaly: "Salinization signature detected" },
            { season: "Activity window 2023/24 A", start_date: "2023-11-01", end_date: "2024-04-30", ndvi_peak: 0.22, outcome: "weak" },
        ],
    },
    {
        id: "land-004",
        name: "Aswan Riverside Block",
        governorate: "Aswan",
        district: "Edfu",
        area_feddan: 35,
        submitted_at: "2024-03-18T08:45:00Z",
        job_id: "job-004",
        job_status: "succeeded",
        land_status: "encroachment",
        trend_2y: "declining",
        season_performance: "weak",
        flags: ["encroachment", "abandonment"],
        satellite_evidence_coverage: {
            status: "good",
            rationale: "Recent imagery has enough clear observations to support land-use interpretation.",
        },
        confidence: {
            status: "high",
            rationale:
                "Building footprints visible in recent imagery, consistent with land-use change from agricultural to residential/industrial.",
        },
        risk_tier: "high",
        indicators: {
            ndvi_spread_median: 0.06,
            evi_peak: 0.12,
            ndmi_median: -0.02,
            mndwi_median: -0.25,
            cloud_free_scenes: 36,
            observation_coverage: 0.91,
        },
        report_summary:
            "Satellite evidence indicates a boundary or non-vegetated land-use signal that requires external verification. FarmTrust does not make legal-boundary or approval decisions from this signal alone.",
        // No activity cycles — vegetated cropland converted to built-up land.
        season_records: [],
    },
    {
        id: "land-005",
        name: "Beheira Cotton Fields",
        governorate: "Beheira",
        district: "Damanhur",
        area_feddan: 200,
        submitted_at: "2024-03-20T10:00:00Z",
        job_id: "job-005",
        job_status: "succeeded",
        land_status: "active",
        trend_2y: "improving",
        season_performance: "good",
        flags: [],
        satellite_evidence_coverage: {
            status: "good",
            rationale: "Excellent clear-scene coverage with few continuity gaps.",
        },
        confidence: {
            status: "high",
            rationale: "Excellent observation coverage with clear vegetation activity windows.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_spread_median: 0.05,
            evi_peak: 0.58,
            ndmi_median: 0.2,
            mndwi_median: -0.34,
            cloud_free_scenes: 44,
            observation_coverage: 0.97,
        },
        report_summary:
            "Consistent high vegetation activity was observed. Multiple strong activity windows were detected from satellite vegetation signals.",
        season_records: [
            { season: "Activity window 2022 B", start_date: "2022-05-01", end_date: "2022-10-31", ndvi_peak: 0.79, outcome: "good" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.82, outcome: "good" },
        ],
    },
    {
        id: "land-006",
        name: "Dakahlia Delta Plot",
        governorate: "Dakahlia",
        district: "Mansoura",
        area_feddan: 18,
        submitted_at: "2024-03-22T13:15:00Z",
        job_id: "job-006",
        job_status: "succeeded",
        land_status: "active",
        trend_2y: "stable",
        season_performance: "good",
        flags: [],
        satellite_evidence_coverage: {
            status: "fair",
            rationale: "Some cloud gaps reduce peak timing evidence, but the series remains usable.",
        },
        confidence: {
            status: "medium",
            rationale:
                "Good observation density. Some cloud gaps in summer 2023 reduce certainty on peak NDVI timing.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_spread_median: 0.06,
            evi_peak: 0.5,
            ndmi_median: 0.16,
            mndwi_median: -0.3,
            cloud_free_scenes: 29,
            observation_coverage: 0.81,
        },
        report_summary:
            "Small plot with consistent observed vegetation activity. Irrigation reliability and financing suitability require external context outside FarmTrust's current satellite packet.",
        season_records: [
            { season: "Activity window 2022/23 A", start_date: "2022-11-01", end_date: "2023-04-30", ndvi_peak: 0.7, outcome: "good" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.72, outcome: "good" },
        ],
    },
    {
        id: "land-007",
        name: "Sohag Upper Egypt Block",
        governorate: "Sohag",
        district: "Girga",
        area_feddan: 65,
        submitted_at: "2024-03-25T09:00:00Z",
        job_id: "job-007",
        job_status: "succeeded",
        land_status: "intermittent",
        trend_2y: "declining",
        season_performance: "interrupted",
        flags: ["salinity"],
        satellite_evidence_coverage: {
            status: "limited",
            rationale: "Observation gaps limit activity-window boundary evidence for part of the interval.",
        },
        confidence: {
            status: "medium",
            rationale:
                "Moderate cloud coverage. Declining trend is statistically significant despite gaps.",
        },
        risk_tier: "medium",
        indicators: {
            ndvi_spread_median: 0.1,
            evi_peak: 0.34,
            ndmi_median: 0.08,
            mndwi_median: -0.22,
            cloud_free_scenes: 22,
            observation_coverage: 0.68,
        },
        report_summary:
            "Intermittent vegetation activity with a possible stress signal. Observation gaps limit certainty, so review should focus on evidence coverage and local field context.",
        season_records: [
            { season: "Activity window 2022/23 A", start_date: "2022-11-01", end_date: "2023-04-30", ndvi_peak: 0.58, outcome: "good" },
            { season: "Activity window 2023 B", start_date: "2023-05-01", end_date: "2023-10-31", ndvi_peak: 0.5, outcome: "interrupted", anomaly: "Declining peak vigour" },
            { season: "Activity window 2023/24 A", start_date: "2023-11-01", end_date: "2024-04-30", ndvi_peak: 0.46, outcome: "interrupted" },
        ],
    },
    {
        id: "land-008",
        name: "Kafr el-Sheikh North",
        governorate: "Kafr el-Sheikh",
        district: "Desouk",
        area_feddan: 92,
        submitted_at: "2024-04-01T10:30:00Z",
        job_id: "job-008",
        job_status: "running",
        land_status: undefined,
        confidence: undefined,
        indicators: undefined,
    },
    {
        id: "land-009",
        name: "Qena Sugar Cane Plot",
        governorate: "Qena",
        district: "Nag Hammadi",
        area_feddan: 150,
        submitted_at: "2024-04-02T14:00:00Z",
        job_id: "job-009",
        job_status: "running",
    },
    {
        id: "land-010",
        name: "Luxor East Bank Fields",
        governorate: "Luxor",
        district: "Luxor",
        area_feddan: 28,
        submitted_at: "2024-04-03T08:00:00Z",
        job_id: "job-010",
        job_status: "queued",
    },
    {
        id: "land-011",
        name: "Minya West Plateau",
        governorate: "Minya",
        district: "Beni Mazar",
        area_feddan: 55,
        submitted_at: "2024-04-03T09:30:00Z",
        job_id: "job-011",
        job_status: "queued",
    },
    {
        id: "land-012",
        name: "Alexandria Coastal Parcel",
        governorate: "Alexandria",
        district: "Borg El Arab",
        area_feddan: 8,
        submitted_at: "2024-04-04T11:00:00Z",
        job_id: "job-012",
        job_status: "failed",
    },
];

const BASELINE_NDVI = 0.13;
const STEP_MS = 15 * 86_400_000;

function round(n: number, d = 3): number {
    const f = 10 ** d;
    return Math.round(n * f) / f;
}

// Deterministic NDVI curve traced from the season cycles: baseline between
// cycles, an arch that peaks at each cycle's stated ndvi_peak at mid-window.
function seriesFromSeasons(seasons: SeasonRecord[], base: number): NDVIPoint[] {
    const sorted = [...seasons].sort(
        (a, b) => Date.parse(a.start_date) - Date.parse(b.start_date),
    );
    const t0 = Date.parse(sorted[0].start_date) - STEP_MS * 2;
    const t1 = Date.parse(sorted[sorted.length - 1].end_date) + STEP_MS * 2;
    const points: NDVIPoint[] = [];
    for (let t = t0; t <= t1; t += STEP_MS) {
        let ndvi = base;
        for (const s of sorted) {
            const a = Date.parse(s.start_date);
            const b = Date.parse(s.end_date);
            if (t >= a && t <= b) {
                const frac = (t - a) / (b - a);
                ndvi = Math.max(ndvi, base + (s.ndvi_peak - base) * Math.sin(frac * Math.PI));
            }
        }
        points.push({
            date: new Date(t).toISOString().slice(0, 10),
            ndvi: round(Math.max(0, ndvi)),
            evi: round(Math.max(0, ndvi * 0.82)),
            cloud_coverage: 0.1,
        });
    }
    return points;
}

// Land with no cycles (e.g. encroachment): a deterministic decline from the
// early in-window peak down toward bare soil.
function decliningSeries(peak: number, base: number, startDate: string): NDVIPoint[] {
    const t0 = Date.parse(startDate);
    const n = 48;
    const points: NDVIPoint[] = [];
    for (let i = 0; i < n; i++) {
        const frac = i / (n - 1);
        const ndvi = base + (peak - base) * (1 - frac);
        const t = t0 + i * STEP_MS;
        points.push({
            date: new Date(t).toISOString().slice(0, 10),
            ndvi: round(Math.max(0.04, ndvi)),
            evi: round(Math.max(0.03, ndvi * 0.8)),
            cloud_coverage: 0.1,
        });
    }
    return points;
}

function aucFromSeries(series: NDVIPoint[]): number {
    // Trapezoidal NDVI-days integral over the series.
    let auc = 0;
    for (let i = 1; i < series.length; i++) {
        auc += ((series[i].ndvi + series[i - 1].ndvi) / 2) * 15;
    }
    return round(auc, 1);
}

// Fills the derived fields (ndvi_series, ndvi_peak, ndvi_p95_peak, ndvi_auc)
// from the canonical cycles so every surface for the land agrees.
function finalizeLand(land: LandResult): LandResult {
    if (land.job_status !== "succeeded" || !land.indicators) return land;

    const seasons = land.season_records ?? [];
    const series = seasons.length
        ? seriesFromSeasons(seasons, BASELINE_NDVI)
        : decliningSeries(0.3, BASELINE_NDVI, "2022-05-01");

    const peak = seasons.length
        ? round(Math.max(...seasons.map((s) => s.ndvi_peak)), 2)
        : round(Math.max(...series.map((p) => p.ndvi)), 2);

    const indicators: Indicators = {
        ...land.indicators,
        ndvi_peak: peak,
        ndvi_p95_peak: round(peak + 0.04, 2),
        ndvi_auc: aucFromSeries(series),
    };

    return { ...land, indicators, ndvi_series: series };
}

export const MOCK_LANDS: LandResult[] = RAW_MOCK_LANDS.map(finalizeLand);

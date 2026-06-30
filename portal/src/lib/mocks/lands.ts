import type { LandResult } from "../types";

export const MOCK_LANDS: LandResult[] = [
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
            ndvi_peak: 0.78,
            ndvi_p95_peak: 0.84,
            ndvi_spread_median: 0.06,
            ndvi_auc: 142.3,
            evi_peak: 0.55,
            ndmi_median: 0.18,
            mndwi_median: -0.32,
            cloud_free_scenes: 38,
            observation_coverage: 0.94,
        },
        report_summary:
            "This land parcel demonstrates sustained vegetation activity across the observed window. Detected activity windows are strong, and no current risk flags were identified.",
        ndvi_series: generateNDVI("2022-03-01", 24, "good"),
        season_records: [
            {
                season: "Activity window 2022/23 A",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.75,
                outcome: "good",
            },
            {
                season: "Activity window 2023 B",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.78,
                outcome: "good",
            },
            {
                season: "Activity window 2023/24 A",
                start_date: "2023-11-01",
                end_date: "2024-04-30",
                ndvi_peak: 0.81,
                outcome: "good",
            },
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
            ndvi_peak: 0.61,
            ndvi_p95_peak: 0.69,
            ndvi_spread_median: 0.08,
            ndvi_auc: 98.7,
            evi_peak: 0.42,
            ndmi_median: 0.24,
            mndwi_median: -0.18,
            cloud_free_scenes: 24,
            observation_coverage: 0.72,
        },
        report_summary:
            "Vegetation activity is intermittent with a wetness signal that requires review. The latest activity window showed an interruption-like signal, so interpretation should remain cautious.",
        ndvi_series: generateNDVI("2022-03-01", 24, "intermittent"),
        season_records: [
            {
                season: "Activity window 2022/23 A",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.63,
                outcome: "good",
            },
            {
                season: "Activity window 2023 B",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.55,
                outcome: "interrupted",
                anomaly: "Mid-window NDVI drop, possible waterlogging",
            },
            {
                season: "Activity window 2023/24 A",
                start_date: "2023-11-01",
                end_date: "2024-04-30",
                ndvi_peak: 0.61,
                outcome: "interrupted",
            },
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
            ndvi_peak: 0.22,
            ndvi_p95_peak: 0.29,
            ndvi_spread_median: 0.07,
            ndvi_auc: 31.5,
            evi_peak: 0.15,
            ndmi_median: -0.04,
            mndwi_median: -0.28,
            cloud_free_scenes: 41,
            observation_coverage: 0.96,
        },
        report_summary:
            "This parcel shows low vegetation activity across the observed window. NDVI values remain low, and available signals suggest stress or absence should be reviewed with sufficient history and field context.",
        ndvi_series: generateNDVI("2022-03-01", 24, "declining"),
        season_records: [
            {
                season: "Activity window 2022/23 A",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.38,
                outcome: "weak",
            },
            {
                season: "Activity window 2023 B",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.25,
                outcome: "weak",
                anomaly: "Salinization signature detected",
            },
            {
                season: "Activity window 2023/24 A",
                start_date: "2023-11-01",
                end_date: "2024-04-30",
                ndvi_peak: 0.22,
                outcome: "weak",
            },
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
            ndvi_peak: 0.18,
            ndvi_p95_peak: 0.24,
            ndvi_spread_median: 0.06,
            ndvi_auc: 22.1,
            evi_peak: 0.12,
            ndmi_median: -0.02,
            mndwi_median: -0.25,
            cloud_free_scenes: 36,
            observation_coverage: 0.91,
        },
        report_summary:
            "Satellite evidence indicates a boundary or non-vegetated land-use signal that requires external verification. FarmTrust does not make legal-boundary or approval decisions from this signal alone.",
        ndvi_series: generateNDVI("2022-03-01", 24, "encroachment"),
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
            rationale:
                "Excellent observation coverage with clear vegetation activity windows.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_peak: 0.82,
            ndvi_p95_peak: 0.88,
            ndvi_spread_median: 0.05,
            ndvi_auc: 158.6,
            evi_peak: 0.58,
            ndmi_median: 0.20,
            mndwi_median: -0.34,
            cloud_free_scenes: 44,
            observation_coverage: 0.97,
        },
        report_summary:
            "Consistent high vegetation activity was observed. Multiple strong activity windows were detected from satellite vegetation signals.",
        ndvi_series: generateNDVI("2022-03-01", 24, "good"),
        season_records: [
            {
                season: "Activity window 2022 B",
                start_date: "2022-05-01",
                end_date: "2022-10-31",
                ndvi_peak: 0.79,
                outcome: "good",
            },
            {
                season: "Activity window 2023 B",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.82,
                outcome: "good",
            },
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
            ndvi_peak: 0.71,
            ndvi_p95_peak: 0.77,
            ndvi_spread_median: 0.06,
            ndvi_auc: 128.4,
            evi_peak: 0.50,
            ndmi_median: 0.16,
            mndwi_median: -0.30,
            cloud_free_scenes: 29,
            observation_coverage: 0.81,
        },
        report_summary:
            "Small plot with consistent observed vegetation activity. Irrigation reliability and financing suitability require external context outside FarmTrust's current satellite packet.",
        ndvi_series: generateNDVI("2022-03-01", 24, "good"),
        season_records: [],
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
            ndvi_peak: 0.53,
            ndvi_p95_peak: 0.63,
            ndvi_spread_median: 0.10,
            ndvi_auc: 87.2,
            evi_peak: 0.34,
            ndmi_median: 0.08,
            mndwi_median: -0.22,
            cloud_free_scenes: 22,
            observation_coverage: 0.68,
        },
        report_summary:
            "Intermittent vegetation activity with a possible stress signal. Observation gaps limit certainty, so review should focus on evidence coverage and local field context.",
        ndvi_series: generateNDVI("2022-03-01", 24, "intermittent"),
        season_records: [],
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

function generateNDVI(
    startDate: string,
    months: number,
    pattern: "good" | "intermittent" | "declining" | "encroachment",
): import("../types").NDVIPoint[] {
    const points: import("../types").NDVIPoint[] = [];
    const start = new Date(startDate);

    for (let i = 0; i < months * 2; i++) {
        const date = new Date(start);
        date.setDate(date.getDate() + i * 15);

        const seasonPhase = (i % 24) / 24;
        const baseNDVI = 0.3 + 0.4 * Math.sin(seasonPhase * Math.PI * 2);
        let ndvi = baseNDVI;

        if (pattern === "good") {
            ndvi = Math.min(
                0.95,
                baseNDVI + 0.15 + (Math.random() - 0.5) * 0.05,
            );
        } else if (pattern === "intermittent") {
            ndvi = baseNDVI + (Math.random() - 0.5) * 0.2;
            if (i > 16 && i < 24) ndvi *= 0.6;
        } else if (pattern === "declining") {
            ndvi = Math.max(
                0.05,
                baseNDVI - i * 0.012 + (Math.random() - 0.5) * 0.05,
            );
        } else if (pattern === "encroachment") {
            ndvi = i < 8 ? baseNDVI : Math.max(0.05, baseNDVI - i * 0.025);
        }

        points.push({
            date: date.toISOString().split("T")[0],
            ndvi: Math.max(0, Math.min(1, ndvi)),
            evi: Math.max(0, Math.min(1, ndvi * 0.85)),
            cloud_coverage: Math.random() * 0.3,
        });
    }

    return points;
}

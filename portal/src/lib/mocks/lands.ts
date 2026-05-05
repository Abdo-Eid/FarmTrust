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
                "Dense cloud-free observations across both seasons with consistent NDVI trajectory.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_peak: 0.78,
            ndvi_auc: 142.3,
            cloud_free_scenes: 38,
            neighbor_comparison: "above_avg",
            observation_coverage: 0.94,
        },
        report_summary:
            "This land parcel demonstrates sustained active cultivation across the observed 24-month period. Vegetation indices are consistently above the district median, and both winter and summer seasons show healthy crop cycles. No risk flags identified. Recommended for standard financing consideration.",
        ndvi_series: generateNDVI("2022-03-01", 24, "good"),
        season_records: [
            {
                season: "Winter 2022/23",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.75,
                outcome: "good",
            },
            {
                season: "Summer 2023",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.78,
                outcome: "good",
            },
            {
                season: "Winter 2023/24",
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
            ndvi_auc: 98.7,
            cloud_free_scenes: 24,
            neighbor_comparison: "avg",
            observation_coverage: 0.72,
        },
        report_summary:
            "Cultivation activity is intermittent with evidence of seasonal waterlogging in the northern section. The 2-year trend is stable, but the last season showed a mid-cycle interruption consistent with excess irrigation or drainage failure. Recommend conditional financing with drainage assessment requirement.",
        ndvi_series: generateNDVI("2022-03-01", 24, "intermittent"),
        season_records: [
            {
                season: "Winter 2022/23",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.63,
                outcome: "good",
            },
            {
                season: "Summer 2023",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.55,
                outcome: "interrupted",
                anomaly: "Mid-season NDVI drop, possible waterlogging",
            },
            {
                season: "Winter 2023/24",
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
        confidence: {
            status: "high",
            rationale:
                "High observation density confirms absence of vegetation activity. Spectral signatures consistent with soil salinization.",
        },
        risk_tier: "high",
        indicators: {
            ndvi_peak: 0.22,
            ndvi_auc: 31.5,
            cloud_free_scenes: 41,
            neighbor_comparison: "below_avg",
            observation_coverage: 0.96,
        },
        report_summary:
            "This parcel shows near-complete cessation of agricultural activity over the last 18 months. NDVI values are at bare-soil levels, and spectral analysis indicates progressive salinization. Long-term trend is strongly declining. Not recommended for agricultural financing without land rehabilitation evidence.",
        ndvi_series: generateNDVI("2022-03-01", 24, "declining"),
        season_records: [
            {
                season: "Winter 2022/23",
                start_date: "2022-11-01",
                end_date: "2023-04-30",
                ndvi_peak: 0.38,
                outcome: "weak",
            },
            {
                season: "Summer 2023",
                start_date: "2023-05-01",
                end_date: "2023-10-31",
                ndvi_peak: 0.25,
                outcome: "weak",
                anomaly: "Salinization signature detected",
            },
            {
                season: "Winter 2023/24",
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
        confidence: {
            status: "high",
            rationale:
                "Building footprints visible in recent imagery, consistent with land-use change from agricultural to residential/industrial.",
        },
        risk_tier: "high",
        indicators: {
            ndvi_peak: 0.18,
            ndvi_auc: 22.1,
            cloud_free_scenes: 36,
            neighbor_comparison: "below_avg",
            observation_coverage: 0.91,
        },
        report_summary:
            "Satellite imagery indicates significant encroachment on agricultural land. Building structures are visible in the northern quadrant, accounting for approximately 40% of the registered area. Agricultural use has ceased in affected areas. Financing not recommended pending legal land-use verification.",
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
        confidence: {
            status: "high",
            rationale:
                "Excellent observation coverage with clear seasonal cycles consistent with cotton cultivation patterns.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_peak: 0.82,
            ndvi_auc: 158.6,
            cloud_free_scenes: 44,
            neighbor_comparison: "above_avg",
            observation_coverage: 0.97,
        },
        report_summary:
            "Premium agricultural land with consistent high-performance cultivation. Cotton cultivation pattern clearly identifiable from spectral signatures. Two full crop cycles observed with strong yields. Recommended for financing.",
        ndvi_series: generateNDVI("2022-03-01", 24, "good"),
        season_records: [
            {
                season: "Summer 2022",
                start_date: "2022-05-01",
                end_date: "2022-10-31",
                ndvi_peak: 0.79,
                outcome: "good",
            },
            {
                season: "Summer 2023",
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
        confidence: {
            status: "medium",
            rationale:
                "Good observation density. Some cloud gaps in summer 2023 reduce certainty on peak NDVI timing.",
        },
        risk_tier: "low",
        indicators: {
            ndvi_peak: 0.71,
            ndvi_auc: 128.4,
            cloud_free_scenes: 29,
            neighbor_comparison: "avg",
            observation_coverage: 0.81,
        },
        report_summary:
            "Small productive plot with consistent activity. Delta location provides reliable irrigation access. Suitable for small-scale agricultural financing.",
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
        confidence: {
            status: "medium",
            rationale:
                "Moderate cloud coverage. Declining trend is statistically significant despite gaps.",
        },
        risk_tier: "medium",
        indicators: {
            ndvi_peak: 0.53,
            ndvi_auc: 87.2,
            cloud_free_scenes: 22,
            neighbor_comparison: "below_avg",
            observation_coverage: 0.68,
        },
        report_summary:
            "Intermittent cultivation with a declining 2-year trend. Salinity indicators are emerging in the southern section. Recommend cautious financing with annual reassessment condition.",
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

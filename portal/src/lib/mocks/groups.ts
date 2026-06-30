import type { LandGroupResult, LandResult } from "../types";
import { MOCK_LANDS } from "./lands";

const PREFIX = "mock-group-";

// A mock land is presented as a single-AOI submission group. Keep the list and
// detail routes in sync by deriving both from this one shape.
export function mockGroupForLand(land: LandResult): LandGroupResult {
    return {
        id: `${PREFIX}${land.id}`,
        name: land.name,
        governorate: land.governorate,
        district: land.district,
        area_feddan: land.area_feddan,
        submitted_at: land.submitted_at,
        job_id: land.job_id,
        primary_land_id: land.id,
        aoi_count: 1,
        job_status: land.job_status,
        assessment_status: land.assessment_status,
        land_status: land.land_status,
        trend_2y: land.trend_2y,
        season_performance: land.season_performance,
        risk_tier: land.risk_tier,
        confidence: land.confidence,
        satellite_evidence_coverage: land.satellite_evidence_coverage,
        children: [land],
    };
}

export function mockGroups(): LandGroupResult[] {
    return MOCK_LANDS.map(mockGroupForLand);
}

export function findMockGroup(groupId: string): LandGroupResult | undefined {
    if (!groupId.startsWith(PREFIX)) return undefined;
    const land = MOCK_LANDS.find((l) => l.id === groupId.slice(PREFIX.length));
    return land ? mockGroupForLand(land) : undefined;
}

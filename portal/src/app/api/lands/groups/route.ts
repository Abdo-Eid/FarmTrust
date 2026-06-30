import { NextResponse } from 'next/server'
import { MOCK_LANDS } from '@/lib/mocks'

const FASTAPI_URL = process.env.FASTAPI_URL ?? 'http://localhost:8000'

function mockGroups() {
  return MOCK_LANDS.map((land) => ({
    id: `mock-group-${land.id}`,
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
  }))
}

export async function GET() {
  try {
    const res = await fetch(`${FASTAPI_URL}/lands/groups`, { cache: 'no-store' })
    if (!res.ok) return NextResponse.json(mockGroups())
    const realGroups = await res.json()
    return NextResponse.json([...mockGroups(), ...realGroups])
  } catch {
    return NextResponse.json(mockGroups())
  }
}

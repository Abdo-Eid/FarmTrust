import { NextResponse } from 'next/server'
import { MOCK_LANDS } from '@/lib/mocks'

export async function GET() {
  return NextResponse.json(MOCK_LANDS)
}

export async function POST(req: Request) {
  const body = await req.json()
  const newLand = {
    id: `land-${String(MOCK_LANDS.length + 1).padStart(3, '0')}`,
    name: body.name ?? 'Unnamed Land',
    governorate: body.governorate ?? 'Unknown',
    district: body.district,
    area_feddan: body.area_feddan ?? 10,
    method: body.method ?? 'polygon',
    geometry: body.geometry ?? null,
    notes: body.notes,
    submitted_at: new Date().toISOString(),
    job_id: `job-${String(MOCK_LANDS.length + 1).padStart(3, '0')}`,
    job_status: 'queued' as const,
  }
  return NextResponse.json(newLand, { status: 201 })
}

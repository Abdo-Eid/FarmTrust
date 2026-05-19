import { NextResponse } from 'next/server'
import { MOCK_LANDS } from '@/lib/mocks'

const FASTAPI_URL = process.env.FASTAPI_URL ?? 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${FASTAPI_URL}/lands`, { cache: 'no-store' })
    if (!res.ok) return NextResponse.json(MOCK_LANDS)
    const realLands = await res.json()
    return NextResponse.json([...MOCK_LANDS, ...realLands])
  } catch {
    return NextResponse.json(MOCK_LANDS)
  }
}

export async function POST(req: Request) {
  const body = await req.json()
  try {
    const res = await fetch(`${FASTAPI_URL}/lands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: 'FastAPI backend is unavailable' }, { status: 503 })
  }
}

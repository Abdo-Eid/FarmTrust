import { NextResponse } from 'next/server'
import { mockGroups } from '@/lib/mocks/groups'

const FASTAPI_URL = process.env.FASTAPI_URL ?? 'http://localhost:8000'

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

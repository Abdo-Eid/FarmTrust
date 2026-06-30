import { NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL ?? 'http://localhost:8000'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  if (id.startsWith('mock-group-')) {
    return NextResponse.json({ error: 'Mock submission detail is not available' }, { status: 404 })
  }

  try {
    const res = await fetch(`${FASTAPI_URL}/lands/groups/${id}`, { cache: 'no-store' })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: 'FastAPI backend is unavailable' }, { status: 503 })
  }
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  if (id.startsWith('mock-group-')) {
    return NextResponse.json({ error: 'Mock submissions cannot be deleted' }, { status: 403 })
  }

  try {
    const res = await fetch(`${FASTAPI_URL}/lands/groups/${id}`, {
      method: 'DELETE',
      cache: 'no-store',
    })
    if (res.status === 204) return new NextResponse(null, { status: 204 })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: 'FastAPI backend is unavailable' }, { status: 503 })
  }
}

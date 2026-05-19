import { NextResponse } from "next/server";
import { MOCK_LANDS } from "@/lib/mocks";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function POST(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;

    // Mock jobs cannot be cancelled
    const isMockJob = MOCK_LANDS.some((land) => land.job_id === id);
    if (isMockJob) {
        return NextResponse.json({ error: "Cannot cancel mock jobs" }, { status: 409 });
    }

    try {
        const res = await fetch(`${FASTAPI_URL}/jobs/${id}/cancel`, {
            method: "POST",
            cache: "no-store",
        });
        return NextResponse.json(await res.json(), { status: res.status });
    } catch {
        return NextResponse.json({ error: "FastAPI backend is unavailable" }, { status: 503 });
    }
}

import { NextResponse } from "next/server";
import { MOCK_LANDS } from "@/lib/mocks";
import { mockNarrate } from "@/lib/mocks/assistant";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function POST(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;

    const mock = MOCK_LANDS.find((l) => l.id === id);
    if (mock) {
        if (mock.job_status !== "succeeded") {
            return NextResponse.json(
                { detail: "Evidence packet not yet generated" },
                { status: 404 },
            );
        }
        return NextResponse.json(mockNarrate(mock));
    }

    try {
        const res = await fetch(`${FASTAPI_URL}/lands/${id}/assistant/narrate`, {
            method: "POST",
            cache: "no-store",
        });
        const body = await res.text();
        return new NextResponse(body, {
            status: res.status,
            headers: {
                "content-type": res.headers.get("content-type") ?? "application/json",
            },
        });
    } catch {
        return NextResponse.json(
            { error: "FastAPI backend is unavailable" },
            { status: 503 },
        );
    }
}

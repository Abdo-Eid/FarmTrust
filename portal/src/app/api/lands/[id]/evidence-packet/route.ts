import { NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    try {
        const res = await fetch(`${FASTAPI_URL}/lands/${id}/evidence-packet`, {
            cache: "no-store",
        });
        // Forward the real status + body (even on 4xx/5xx with a non-JSON body),
        // so the client sees the true failure rather than a fabricated 503.
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

import { NextResponse } from "next/server";
import { MOCK_LANDS } from "@/lib/mocks";
import { mockChat } from "@/lib/mocks/assistant";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function POST(
    req: Request,
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
        return NextResponse.json(mockChat(mock));
    }

    const payload = await req.text();
    try {
        const res = await fetch(`${FASTAPI_URL}/lands/${id}/assistant/chat`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: payload,
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

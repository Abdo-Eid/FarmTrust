import { NextResponse } from "next/server";
import { MOCK_LANDS } from "@/lib/mocks";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const land = MOCK_LANDS.find((l) => l.id === id);
    if (land) return NextResponse.json(land);

    try {
        const res = await fetch(`${FASTAPI_URL}/lands/${id}`, { cache: "no-store" });
        return NextResponse.json(await res.json(), { status: res.status });
    } catch {
        return NextResponse.json({ error: "FastAPI backend is unavailable" }, { status: 503 });
    }
}

export async function DELETE(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;

    // Mock lands cannot be deleted
    if (MOCK_LANDS.some((l) => l.id === id)) {
        return NextResponse.json({ error: "Mock lands cannot be deleted" }, { status: 403 });
    }

    try {
        const res = await fetch(`${FASTAPI_URL}/lands/${id}`, {
            method: "DELETE",
            cache: "no-store",
        });
        if (res.status === 204) return new NextResponse(null, { status: 204 });
        return NextResponse.json(await res.json(), { status: res.status });
    } catch {
        return NextResponse.json({ error: "FastAPI backend is unavailable" }, { status: 503 });
    }
}

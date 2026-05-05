import { NextResponse } from "next/server";
import { MOCK_LANDS } from "@/lib/mocks";

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const land = MOCK_LANDS.find((l) => l.id === id);
    if (!land)
        return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(land);
}

import { NextResponse } from "next/server";
import { getMockJob } from "@/lib/mocks";

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const job = getMockJob(id);
    return NextResponse.json(job);
}

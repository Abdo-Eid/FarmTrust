import { MOCK_LANDS } from "@/lib/mocks";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;

    // Mock jobs are not backed by a real pipeline; SSE not available.
    const isMockJob = MOCK_LANDS.some((land) => land.job_id === id);
    if (isMockJob) {
        return new Response(null, { status: 404 });
    }

    try {
        const upstream = await fetch(`${FASTAPI_URL}/jobs/${id}/events`, {
            headers: { Accept: "text/event-stream" },
            cache: "no-store",
        });

        if (!upstream.ok || !upstream.body) {
            return new Response(null, { status: upstream.status });
        }

        return new Response(upstream.body, {
            headers: {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        });
    } catch {
        return new Response(null, { status: 503 });
    }
}

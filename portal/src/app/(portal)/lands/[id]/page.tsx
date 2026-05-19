"use client";
import { useEffect, useState } from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useLand } from "@/hooks/useLand";
import { useJobPolling } from "@/hooks/useJobPolling";
import { useJobEvents } from "@/hooks/useJobEvents";
import { TopBar } from "@/components/layout/TopBar";
import { PageHeader } from "@/components/layout/PageHeader";
import { JobProgressRing } from "@/components/processing/JobProgressRing";
import { PipelineTimeline } from "@/components/processing/PipelineTimeline";
import { LogViewer } from "@/components/processing/LogViewer";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { PIPELINE_PHASES } from "@/lib/constants";
import { formatFeddan } from "@/lib/geo";
import { api } from "@/lib/api";

export default function LandProcessingPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const [cancelling, setCancelling] = useState(false);
    const { data: land, isLoading: landLoading } = useLand(id);
    // SSE-first: open a streaming connection to the backend for real jobs.
    // useJobEvents writes updates into the TanStack Query cache directly.
    // useJobPolling is kept as fallback (mock jobs, SSE not available).
    const { connected: eventsConnected } = useJobEvents(land?.job_id);
    const { data: job } = useJobPolling(land?.job_id, { disabled: eventsConnected });

    const handleCancel = async () => {
        if (!land?.job_id || cancelling) return;
        setCancelling(true);
        try {
            await api.jobs.cancel(land.job_id);
        } catch {
            // backend will mark it cancelled; SSE/polling will reflect it
        } finally {
            setCancelling(false);
        }
    };

    useEffect(() => {
        if (job?.status === "succeeded") {
            const timer = setTimeout(
                () => router.push(`/lands/${id}/summary`),
                1500,
            );
            return () => clearTimeout(timer);
        }
    }, [job?.status, id, router]);

    const isActive = job?.status === "running" || job?.status === "queued";
    const sceneProgressLabel =
        isActive &&
        job?.phase === "satellite_fetch" &&
        job?.scene_total
            ? `${job.scene_done ?? 0} / ${job.scene_total} scenes`
            : null;

    const currentPhaseLabel = job?.phase
        ? PIPELINE_PHASES.find((p) => p.phase === job.phase)?.label
        : undefined;

    if (landLoading) {
        return (
            <div className="p-6 space-y-4">
                <SkeletonCard className="h-24" />
                <SkeletonCard className="h-64" />
            </div>
        );
    }

    if (!land) {
        return (
            <div className="p-6 text-center text-gray-500">
                Land not found.{" "}
                <button
                    onClick={() => router.push("/lands")}
                    className="text-teal-700 underline"
                >
                    Back to list
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-full bg-sand">
            <TopBar
                breadcrumbs={[
                    { label: "Lands", href: "/lands" },
                    { label: land.name },
                    { label: "Processing" },
                ]}
                actions={
                    <Button
                        variant="ghost"
                        size="sm"
                        icon="arrow_back"
                        onClick={() => router.push("/lands")}
                    >
                        Back
                    </Button>
                }
            />

            <PageHeader
                title={land.name}
                subtitle="Satellite analysis in progress"
                meta={[
                    { icon: "location_on", value: land.governorate },
                    {
                        icon: "straighten",
                        value: formatFeddan(land.area_feddan),
                    },
                ]}
            />

            <div className="p-6">
                {/* Failed state */}
                {job?.status === "failed" && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md flex items-start gap-3">
                        <span className="material-symbols-outlined text-red-500 text-xl mt-0.5">
                            error
                        </span>
                        <div>
                            <p className="text-sm font-semibold text-red-800">
                                Analysis Failed
                            </p>
                            <p className="text-xs text-red-600 mt-0.5">
                                {job.error ??
                                    "An unexpected error occurred during processing."}
                            </p>
                            <p className="text-xs text-red-400 mt-2">
                                Contact support or resubmit the land for
                                analysis.
                            </p>
                        </div>
                    </div>
                )}

                {/* Cancelled state */}
                {job?.status === "cancelled" && (
                    <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-md flex items-start gap-3">
                        <span className="material-symbols-outlined text-gray-400 text-xl mt-0.5">
                            cancel
                        </span>
                        <div>
                            <p className="text-sm font-semibold text-gray-700">
                                Analysis Cancelled
                            </p>
                            <p className="text-xs text-gray-500 mt-0.5">
                                The pipeline was stopped before completion. You
                                can resubmit this land for a new analysis.
                            </p>
                        </div>
                    </div>
                )}

                {/* Succeeded — redirect notice */}
                {job?.status === "succeeded" && (
                    <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md flex items-center gap-3">
                        <span className="material-symbols-outlined text-green-500 text-xl">
                            check_circle
                        </span>
                        <p className="text-sm text-green-800 font-medium">
                            Analysis complete — redirecting to summary...
                        </p>
                    </div>
                )}

                <div className="grid grid-cols-[1fr_1.5fr] gap-6">
                    {/* Left: Progress ring */}
                    <div className="bg-white border border-gray-200 rounded-md p-8 shadow-panel flex flex-col items-center justify-center gap-6">
                        <JobProgressRing
                            percent={job?.progress ?? 0}
                            status={job?.status ?? "queued"}
                            phase={currentPhaseLabel}
                            sceneProgress={sceneProgressLabel ?? undefined}
                        />
                        {job?.started_at && (
                            <div className="text-center">
                                <p className="text-xs text-gray-400">Started</p>
                                <p className="text-xs font-medium text-gray-600">
                                    {new Date(
                                        job.started_at,
                                    ).toLocaleTimeString("en-EG", {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                        second: "2-digit",
                                    })}
                                </p>
                            </div>
                        )}
                        {isActive && (
                            <Button
                                variant="ghost"
                                size="sm"
                                icon="stop_circle"
                                loading={cancelling}
                                onClick={handleCancel}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                                Stop Pipeline
                            </Button>
                        )}
                    </div>

                    {/* Right: Pipeline timeline */}
                    <div className="bg-white border border-gray-200 rounded-md p-6 shadow-panel">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-5">
                            Pipeline Phases
                        </h3>
                        <PipelineTimeline
                            status={job?.status ?? "queued"}
                            currentPhase={job?.phase}
                            startedAt={job?.started_at}
                            completedAt={job?.completed_at}
                        />
                    </div>
                </div>

                {/* Logs */}
                {job && job.logs.length > 0 && (
                    <div className="mt-6">
                        <LogViewer logs={job.logs} maxHeight="240px" />
                    </div>
                )}
            </div>
        </div>
    );
}

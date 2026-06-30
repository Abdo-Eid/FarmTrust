"use client";

import { use, useState } from "react";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { useLandGroup } from "@/hooks/useLandGroup";
import { useJobEvents } from "@/hooks/useJobEvents";
import { useJobPolling } from "@/hooks/useJobPolling";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { LandStatusBadge } from "@/components/lands/LandStatusBadge";
import { SatelliteEvidenceBadge } from "@/components/lands/SatelliteEvidenceBadge";
import { TrendIndicator } from "@/components/lands/TrendIndicator";
import { JobProgressRing } from "@/components/processing/JobProgressRing";
import { PipelineTimeline } from "@/components/processing/PipelineTimeline";
import { LogViewer } from "@/components/processing/LogViewer";
import { PIPELINE_PHASES, RISK_TIER_COLORS, RISK_TIER_LABELS } from "@/lib/constants";
import { api } from "@/lib/api";
import { formatFeddan } from "@/lib/geo";

export default function LandGroupPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const [cancelling, setCancelling] = useState(false);
    const { data: group, isLoading } = useLandGroup(id);
    const { connected } = useJobEvents(group?.job_id);
    const { data: job } = useJobPolling(group?.job_id, { disabled: connected });

    const status = job?.status ?? group?.job_status ?? "queued";
    const isActive = status === "queued" || status === "running";
    const currentPhaseLabel = job?.phase
        ? PIPELINE_PHASES.find((p) => p.phase === job.phase)?.label
        : undefined;
    const sceneProgressLabel =
        isActive && job?.phase === "satellite_fetch" && job.scene_total
            ? `${job.scene_done ?? 0} / ${job.scene_total} scenes`
            : undefined;

    const completedCount = group?.children.filter((land) => land.assessment_status).length ?? 0;
    const manualReviewCount = group?.children.filter((land) => land.assessment_status === "manual_review_required").length ?? 0;

    async function handleCancel() {
        if (!group?.job_id || cancelling) return;
        if (!confirm("Stop this shared pipeline for all AOIs in this submission?")) return;
        setCancelling(true);
        try {
            await api.jobs.cancel(group.job_id);
        } finally {
            setCancelling(false);
        }
    }

    if (isLoading) {
        return (
            <div className="p-6 space-y-4">
                <SkeletonCard className="h-24" />
                <SkeletonCard className="h-64" />
            </div>
        );
    }

    if (!group) {
        return (
            <div className="p-6 text-center text-gray-500">
                Submission not found.{" "}
                <button onClick={() => router.push("/lands")} className="text-teal-700 underline">
                    Back to submissions
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-full bg-sand">
            <TopBar
                breadcrumbs={[
                    { label: "Submissions", href: "/lands" },
                    { label: group.name },
                ]}
                actions={
                    <Button variant="ghost" size="sm" icon="arrow_back" onClick={() => router.push("/lands")}>
                        Back
                    </Button>
                }
            />

            <div className="p-6 space-y-6">
                <section className="bg-white border border-gray-200 rounded-md shadow-panel p-6">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                                Assessment Submission
                            </p>
                            <h1 className="mt-1 text-2xl font-semibold text-gray-900">{group.name}</h1>
                            <p className="mt-1 text-sm text-gray-500">
                                {group.governorate}{group.district ? ` · ${group.district}` : ""} · {group.aoi_count} AOI{group.aoi_count === 1 ? "" : "s"} · {formatFeddan(group.area_feddan)} total
                            </p>
                            <p className="mt-2 text-xs text-gray-400">
                                Submitted {format(new Date(group.submitted_at), "dd MMM yyyy")} · Shared job {group.job_id}
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            <LandStatusBadge status={group.land_status} jobStatus={status} assessmentStatus={group.assessment_status} />
                            {isActive && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    icon="stop_circle"
                                    loading={cancelling}
                                    onClick={handleCancel}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                    Stop Shared Pipeline
                                </Button>
                            )}
                        </div>
                    </div>
                </section>

                <section className="grid gap-4 md:grid-cols-4">
                    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
                        <p className="text-xs text-gray-400">AOIs</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{group.aoi_count}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
                        <p className="text-xs text-gray-400">Completed</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{completedCount}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
                        <p className="text-xs text-gray-400">Manual Review</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{manualReviewCount}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
                        <p className="text-xs text-gray-400">Worst Risk</p>
                        {group.risk_tier ? (
                            <span className={`mt-2 inline-flex px-2 py-0.5 rounded-full border text-xs font-medium ${RISK_TIER_COLORS[group.risk_tier]}`}>
                                {RISK_TIER_LABELS[group.risk_tier]}
                            </span>
                        ) : (
                            <p className="mt-1 text-2xl font-semibold text-gray-300">—</p>
                        )}
                    </div>
                </section>

                {status !== "succeeded" && (
                    <section className="grid gap-6 lg:grid-cols-[320px_1fr]">
                        <div className="bg-white border border-gray-200 rounded-md p-6 shadow-panel flex flex-col items-center gap-5">
                            <JobProgressRing
                                percent={job?.progress ?? 0}
                                status={status}
                                phase={currentPhaseLabel}
                                sceneProgress={sceneProgressLabel}
                            />
                            <p className="text-xs text-center text-gray-500">
                                One shared satellite download is used for this submission; each AOI is analyzed separately.
                            </p>
                        </div>
                        <div className="bg-white border border-gray-200 rounded-md p-6 shadow-panel">
                            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-5">
                                Shared Pipeline
                            </h3>
                            <PipelineTimeline
                                status={status}
                                currentPhase={job?.phase}
                                startedAt={job?.started_at}
                                completedAt={job?.completed_at}
                            />
                        </div>
                    </section>
                )}

                <section className="bg-white border border-gray-200 rounded-md shadow-panel overflow-hidden">
                    <div className="px-5 py-4 border-b border-gray-100">
                        <h2 className="text-sm font-semibold text-gray-900">Child AOIs</h2>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Reports and evidence remain separate for each land polygon.
                        </p>
                    </div>
                    <div className="divide-y divide-gray-100">
                        {group.children.map((land) => (
                            <div key={land.id} className="px-5 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                <div>
                                    <p className="text-sm font-medium text-gray-900">{land.name}</p>
                                    <p className="text-xs text-gray-400">{formatFeddan(land.area_feddan)}</p>
                                </div>
                                <div className="flex flex-wrap items-center gap-3">
                                    <LandStatusBadge status={land.land_status} jobStatus={status} assessmentStatus={land.assessment_status} />
                                    <SatelliteEvidenceBadge coverage={land.satellite_evidence_coverage} />
                                    {land.trend_2y && <TrendIndicator trend={land.trend_2y} size="sm" />}
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => router.push(status === "succeeded" ? `/lands/${land.id}/summary` : `/lands/${land.id}`)}
                                    >
                                        {status === "succeeded" ? "Open Report" : "Open Status"}
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {job && job.logs.length > 0 && (
                    <LogViewer logs={job.logs} maxHeight="240px" />
                )}
            </div>
        </div>
    );
}

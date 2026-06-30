"use client";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useLand } from "@/hooks/useLand";
import { TopBar } from "@/components/layout/TopBar";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { RiskFlagList } from "@/components/lands/RiskFlagList";
import { SatelliteEvidenceBadge } from "@/components/lands/SatelliteEvidenceBadge";
import { DecisionBrief } from "@/components/summary/DecisionBrief";
import { ConfidenceSection } from "@/components/summary/ConfidenceSection";
import { IndicatorsGrid } from "@/components/summary/IndicatorsGrid";
import { ReportSummaryText } from "@/components/summary/ReportSummaryText";
import { formatFeddan } from "@/lib/geo";

export default function LandSummaryPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const queryClient = useQueryClient();
    const { data: land, isLoading } = useLand(id);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    async function handleDelete() {
        if (!confirm('Delete this land and all its pipeline data? This cannot be undone.')) return;
        setDeleting(true);
        setDeleteError(null);
        try {
            await api.lands.delete(id);
            await queryClient.invalidateQueries({ queryKey: ['lands'] });
            router.push('/lands');
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Delete failed';
            const match = msg.match(/API error \d+: (.+)/);
            setDeleteError(match ? (() => { try { return JSON.parse(match[1]).detail } catch { return match[1] } })() : msg);
            setDeleting(false);
        }
    }

    if (isLoading) {
        return (
            <div className="p-6 space-y-4">
                <SkeletonCard className="h-20" />
                <SkeletonCard className="h-32" />
                <SkeletonCard className="h-24" />
                <SkeletonCard className="h-40" />
            </div>
        );
    }

    if (!land || land.job_status !== "succeeded") {
        return (
            <div className="p-6 text-center text-gray-500">
                <p>Summary not available.</p>
                <button
                    onClick={() => router.push("/lands")}
                    className="text-teal-700 underline text-sm mt-2"
                >
                    Back to lands
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
                    { label: "Summary" },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            icon="delete"
                            loading={deleting}
                            onClick={handleDelete}
                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        >
                            Delete
                        </Button>
                        <div className="w-px h-4 bg-gray-200" />
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="map"
                            onClick={() =>
                                router.push(`/lands/${land.id}/workbench`)
                            }
                        >
                            Workbench
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="table_chart"
                            onClick={() =>
                                router.push(`/lands/${land.id}/evidence`)
                            }
                        >
                            Evidence
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="summarize"
                            onClick={() =>
                                router.push(`/lands/${land.id}/packet`)
                            }
                        >
                            Report Card
                        </Button>
                        <Button
                            variant="primary"
                            size="sm"
                            icon="download"
                            onClick={() =>
                                router.push(`/lands/${land.id}/report`)
                            }
                        >
                            Export PDF
                        </Button>
                    </div>
                }
            />

            {deleteError && (
                <div className="mx-6 mt-4 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-md px-4 py-3 text-sm">
                    <span className="material-symbols-outlined text-base">error</span>
                    <span>{deleteError}</span>
                    <button onClick={() => setDeleteError(null)} className="ml-auto text-red-400 hover:text-red-600">
                        <span className="material-symbols-outlined text-base">close</span>
                    </button>
                </div>
            )}

            {/* Identity header band — teal gradient (only here) */}
            <PageHeader
                title={land.name}
                subtitle="Land Assessment Summary"
                meta={[
                    {
                        icon: "location_on",
                        value: `${land.governorate}${land.district ? ` · ${land.district}` : ""}`,
                    },
                    {
                        icon: "straighten",
                        value: formatFeddan(land.area_feddan),
                    },
                    {
                        icon: "calendar_today",
                        value: `Submitted ${format(new Date(land.submitted_at), "dd MMM yyyy")}`,
                    },
                ]}
            />

            {/* Content — visual priority order (non-negotiable) */}
            <div className="p-6 space-y-5">
                {/* Priority 1: Decision Brief */}
                <DecisionBrief land={land} />

                {/* Priority 2: Satellite Evidence Coverage */}
                {land.satellite_evidence_coverage && (
                    <div>
                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                            Satellite Evidence Coverage
                        </p>
                        <div className="bg-white border border-gray-200 rounded-md px-4 py-3 shadow-panel">
                            <SatelliteEvidenceBadge coverage={land.satellite_evidence_coverage} showRationale />
                        </div>
                    </div>
                )}

                {/* Priority 3: Assessment Confidence */}
                {land.confidence && (
                    <ConfidenceSection confidence={land.confidence} />
                )}

                {/* Priority 4: Risk Flags */}
                <div>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                        Risk Flags
                    </p>
                    <div className="bg-white border border-gray-200 rounded-md px-4 py-3 shadow-panel">
                        <RiskFlagList flags={land.flags ?? []} assessmentStatus={land.assessment_status} />
                    </div>
                </div>

                {/* Priority 5: Indicators */}
                {land.indicators && (
                    <IndicatorsGrid indicators={land.indicators} />
                )}

                {/* Priority 6: Report Summary */}
                {land.report_summary && (
                    <ReportSummaryText text={land.report_summary} />
                )}

                {/* Priority 7: Evidence Links */}
                <div className="bg-white border border-gray-200 rounded-md p-4 shadow-panel">
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                        Further Analysis
                    </p>
                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={() =>
                                router.push(`/lands/${land.id}/workbench`)
                            }
                            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors text-sm text-gray-700"
                        >
                            <span className="material-symbols-outlined text-teal-600 text-base">
                                map
                            </span>
                            Open Geospatial Workbench
                        </button>
                        <button
                            onClick={() =>
                                router.push(`/lands/${land.id}/evidence`)
                            }
                            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors text-sm text-gray-700"
                        >
                            <span className="material-symbols-outlined text-teal-600 text-base">
                                table_chart
                            </span>
                            View Data Tables
                        </button>
                        <button
                            onClick={() =>
                                router.push(`/lands/${land.id}/report`)
                            }
                            className="flex items-center gap-2 px-4 py-2.5 bg-teal-700 rounded-md hover:bg-teal-800 transition-colors text-sm text-white"
                        >
                            <span className="material-symbols-outlined text-base">
                                download
                            </span>
                            Download PDF Report
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

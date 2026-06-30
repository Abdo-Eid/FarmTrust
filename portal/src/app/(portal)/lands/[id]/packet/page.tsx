"use client";
import { use } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import * as Tabs from "@radix-ui/react-tabs";
import { useLand } from "@/hooks/useLand";
import { useEvidencePacket } from "@/hooks/useEvidencePacket";
import { TopBar } from "@/components/layout/TopBar";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { EvidencePacketReport } from "@/components/report/EvidencePacketReport";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { formatFeddan } from "@/lib/geo";

export default function LandPacketPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const { data: land, isLoading: landLoading, isError: landError, refetch: refetchLand } = useLand(id);
    const { data: packet, isLoading: packetLoading, isError } = useEvidencePacket(id);

    if (landLoading) {
        return (
            <div className="p-6 space-y-4">
                <SkeletonCard className="h-20" />
                <SkeletonCard className="h-40" />
                <SkeletonCard className="h-40" />
            </div>
        );
    }

    if (landError) {
        return (
            <div className="p-6 text-center text-gray-500">
                <p>Could not load this land.</p>
                <button
                    onClick={() => refetchLand()}
                    className="text-teal-700 underline text-sm mt-2"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!land || land.job_status !== "succeeded") {
        return (
            <div className="p-6 text-center text-gray-500">
                <p>Report card not available.</p>
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
                    { label: "Report Card" },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="dashboard"
                            onClick={() => router.push(`/lands/${land.id}/summary`)}
                        >
                            Summary
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="table_chart"
                            onClick={() => router.push(`/lands/${land.id}/evidence`)}
                        >
                            Evidence
                        </Button>
                        <Button
                            variant="primary"
                            size="sm"
                            icon="download"
                            onClick={() => router.push(`/lands/${land.id}/report`)}
                        >
                            Export PDF
                        </Button>
                    </div>
                }
            />

            <PageHeader
                title={land.name}
                subtitle="Lender Report Card"
                meta={[
                    {
                        icon: "location_on",
                        value: `${land.governorate}${land.district ? ` · ${land.district}` : ""}`,
                    },
                    { icon: "straighten", value: formatFeddan(land.area_feddan) },
                    {
                        icon: "calendar_today",
                        value: `Submitted ${format(new Date(land.submitted_at), "dd MMM yyyy")}`,
                    },
                ]}
            />

            <div className="p-6">
                {packetLoading ? (
                    <div className="space-y-4">
                        <SkeletonCard className="h-24" />
                        <SkeletonCard className="h-48" />
                        <SkeletonCard className="h-40" />
                    </div>
                ) : isError || !packet ? (
                    <div className="bg-white border border-gray-200 rounded-md p-6 shadow-panel text-center">
                        <span className="material-symbols-outlined text-3xl text-gray-300">summarize</span>
                        <p className="text-sm text-gray-600 mt-2">
                            The report card has not been generated for this land yet.
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                            It is produced at the end of the analysis. Try re-running the assessment if this
                            persists.
                        </p>
                    </div>
                ) : (
                    <Tabs.Root defaultValue="report" className="w-full">
                        <Tabs.List className="border-b border-gray-200 bg-transparent flex gap-0 mb-5">
                            <Tabs.Trigger
                                value="report"
                                className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
                            >
                                <span className="material-symbols-outlined text-base align-middle mr-1">summarize</span>
                                Report
                            </Tabs.Trigger>
                            <Tabs.Trigger
                                value="assistant"
                                className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
                            >
                                <span className="material-symbols-outlined text-base align-middle mr-1">forum</span>
                                Ask the assistant
                            </Tabs.Trigger>
                        </Tabs.List>

                        <Tabs.Content value="report">
                            <EvidencePacketReport packet={packet} />
                        </Tabs.Content>
                        <Tabs.Content value="assistant">
                            <AssistantPanel landId={land.id} />
                        </Tabs.Content>
                    </Tabs.Root>
                )}
            </div>
        </div>
    );
}

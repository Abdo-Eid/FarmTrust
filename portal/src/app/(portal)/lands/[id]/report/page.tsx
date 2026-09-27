"use client";

import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useLand } from "@/hooks/useLand";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { z } from "zod";
import { Skeleton } from "@/components/ui/Skeleton";

// Form validation schema
const reportFormSchema = z.object({
    analystName: z
        .string()
        .min(2, "Analyst name must be at least 2 characters"),
    institution: z.string().min(1, "Institution is required"),
    reportDate: z.string().min(1, "Report date is required"),
    reportType: z.enum(["full", "executive", "risk"]),
    includeVegetation: z.boolean(),
    includeRiskFlags: z.boolean(),
    includeSummary: z.boolean(),
});

type ReportFormData = z.infer<typeof reportFormSchema>;

export default function ReportPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const { data: land, isLoading } = useLand(id);

    const [formValues, setFormValues] = useState<ReportFormData>({
        analystName: "",
        institution: "",
        reportDate: new Date().toISOString().split("T")[0],
        reportType: "full",
        includeVegetation: true,
        includeRiskFlags: true,
        includeSummary: true,
    });

    if (isLoading) {
        return (
            <div>
                <PageHeader
                    title="Loading..."
                    subtitle="Report Export"
                    actions={
                        <Button
                            variant="secondary"
                            onClick={() => router.back()}
                        >
                            Back
                        </Button>
                    }
                />
                <div className="p-6">
                    <Skeleton className="h-96 mb-4" />
                </div>
            </div>
        );
    }

    if (!land) {
        return (
            <div>
                <PageHeader
                    title="Land Not Found"
                    subtitle="Report Export"
                    actions={
                        <Button
                            variant="secondary"
                            onClick={() => router.back()}
                        >
                            Back
                        </Button>
                    }
                />
                <div className="p-6">
                    <Card>
                        <p className="text-gray-600">
                            The land record could not be found. Please try
                            again.
                        </p>
                    </Card>
                </div>
            </div>
        );
    }

    const handleEmailShare = () => {
        // Toast-like notification (mock)
        alert("Email feature coming soon");
    };

    const handlePrint = () => {
        window.print();
    };

    const submittedDate = new Date(land.submitted_at).toLocaleDateString(
        "en-GB",
        {
            year: "numeric",
            month: "short",
            day: "2-digit",
        },
    );

    const statusLabel = land.land_status
        ? land.land_status.replace(/_/g, " ")
        : "Unknown";
    const riskLabel = land.risk_tier
        ? land.risk_tier.replace(/_/g, " ")
        : "Unknown";
    const trendLabel = land.trend_2y
        ? land.trend_2y.replace(/_/g, " ")
        : "Unknown";
    const confidenceLabel = land.confidence?.status ?? "Unknown";
    const coverageLabel =
        land.satellite_evidence_coverage?.status?.replace(/_/g, " ") ??
        "Unknown";
    const flags =
        land.flags && land.flags.length > 0
            ? land.flags.map((flag) => flag.replace(/_/g, " "))
            : ["No land risk flags identified"];

    return (
        <div>
            <style jsx global>{`
                @media print {
                    @page {
                        size: A4;
                        margin: 14mm;
                    }

                    body {
                        background: white !important;
                    }

                    aside,
                    [role="complementary"],
                    .no-print,
                    button {
                        display: none !important;
                    }

                    main {
                        margin: 0 !important;
                    }

                    .print-shell {
                        padding: 0 !important;
                        display: block !important;
                        background: white !important;
                    }

                    .print-report {
                        width: 100% !important;
                        min-height: auto !important;
                        box-shadow: none !important;
                        border: 0 !important;
                        padding: 0 !important;
                    }
                }
            `}</style>

            <div className="no-print">
                <PageHeader
                    title={land.name}
                    subtitle="Report Export"
                    actions={
                        <Button
                            variant="secondary"
                            onClick={() => router.push(`/lands/${id}/summary`)}
                        >
                            Back to Summary
                        </Button>
                    }
                />
            </div>

            <div className="print-shell grid gap-6 p-6 xl:grid-cols-[minmax(760px,1fr)_420px]">
                {/* Left Panel: Report Preview */}
                <div className="min-w-0">
                    <Card padding="md">
                        <CardHeader className="no-print">
                            <CardTitle>Report Preview</CardTitle>
                        </CardHeader>

                        <article className="print-report mx-auto mt-4 min-h-[1050px] max-w-[820px] bg-white p-12 text-gray-900 shadow-sm ring-1 ring-gray-200">
                            <header className="border-b border-gray-200 pb-6">
                                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">
                                    FarmTrust Satellite Land Assessment
                                </p>
                                <div className="mt-5 flex items-start justify-between gap-6">
                                    <div>
                                        <h2 className="text-3xl font-semibold tracking-normal text-gray-950">
                                            {land.name}
                                        </h2>
                                        <p className="mt-2 text-sm text-gray-500">
                                            {land.governorate}
                                            {land.district
                                                ? ` · ${land.district}`
                                                : ""}{" "}
                                            · {land.area_feddan.toFixed(2)} fd
                                        </p>
                                    </div>
                                    <div className="text-right text-xs text-gray-500">
                                        <p>Report date</p>
                                        <p className="mt-1 font-semibold text-gray-900">
                                            {formValues.reportDate}
                                        </p>
                                    </div>
                                </div>
                            </header>

                            <section className="mt-7 grid grid-cols-4 gap-3">
                                {[
                                    ["Status", statusLabel],
                                    ["Risk tier", riskLabel],
                                    ["Trend", trendLabel],
                                    ["Confidence", confidenceLabel],
                                ].map(([label, value]) => (
                                    <div
                                        key={label}
                                        className="rounded-md border border-gray-200 p-3"
                                    >
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                            {label}
                                        </p>
                                        <p className="mt-2 text-sm font-semibold capitalize text-gray-900">
                                            {value}
                                        </p>
                                    </div>
                                ))}
                            </section>

                            <section className="mt-7">
                                <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900">
                                    Assessment Summary
                                </h3>
                                <p className="mt-3 rounded-md bg-gray-50 p-4 text-sm leading-7 text-gray-700">
                                    {land.report_summary ||
                                        "No report summary is available for this land."}
                                </p>
                            </section>

                            <section className="mt-7 grid grid-cols-2 gap-6">
                                <div>
                                    <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900">
                                        Evidence Basis
                                    </h3>
                                    <dl className="mt-3 space-y-3 text-sm">
                                        <div className="flex justify-between gap-4 border-b border-gray-100 pb-2">
                                            <dt className="text-gray-500">
                                                Satellite coverage
                                            </dt>
                                            <dd className="font-semibold capitalize">
                                                {coverageLabel}
                                            </dd>
                                        </div>
                                        <div className="flex justify-between gap-4 border-b border-gray-100 pb-2">
                                            <dt className="text-gray-500">
                                                Cloud-free scenes
                                            </dt>
                                            <dd className="font-semibold">
                                                {land.indicators
                                                    ?.cloud_free_scenes ??
                                                    "N/A"}
                                            </dd>
                                        </div>
                                        <div className="flex justify-between gap-4 border-b border-gray-100 pb-2">
                                            <dt className="text-gray-500">
                                                Submitted
                                            </dt>
                                            <dd className="font-semibold">
                                                {submittedDate}
                                            </dd>
                                        </div>
                                    </dl>
                                </div>

                                <div>
                                    <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900">
                                        Vegetation Indicators
                                    </h3>
                                    <dl className="mt-3 grid grid-cols-2 gap-3">
                                        <div className="rounded-md border border-gray-200 p-3">
                                            <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                                NDVI peak
                                            </dt>
                                            <dd className="mt-1 text-xl font-semibold">
                                                {land.indicators?.ndvi_peak?.toFixed(
                                                    2,
                                                ) ?? "N/A"}
                                            </dd>
                                        </div>
                                        <div className="rounded-md border border-gray-200 p-3">
                                            <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                                EVI peak
                                            </dt>
                                            <dd className="mt-1 text-xl font-semibold">
                                                {land.indicators?.evi_peak?.toFixed(
                                                    2,
                                                ) ?? "N/A"}
                                            </dd>
                                        </div>
                                        <div className="rounded-md border border-gray-200 p-3">
                                            <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                                Field spread
                                            </dt>
                                            <dd className="mt-1 text-xl font-semibold">
                                                {land.indicators?.ndvi_spread_median?.toFixed(
                                                    2,
                                                ) ?? "N/A"}
                                            </dd>
                                        </div>
                                        <div className="rounded-md border border-gray-200 p-3">
                                            <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                                Moisture
                                            </dt>
                                            <dd className="mt-1 text-xl font-semibold">
                                                {land.indicators?.ndmi_median?.toFixed(
                                                    2,
                                                ) ?? "N/A"}
                                            </dd>
                                        </div>
                                    </dl>
                                </div>
                            </section>

                            <section className="mt-7">
                                <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900">
                                    Risk and Limits
                                </h3>
                                <div className="mt-3 grid grid-cols-2 gap-4 text-sm leading-6">
                                    <div className="rounded-md border border-gray-200 p-4">
                                        <p className="font-semibold text-gray-900">
                                            Risk flags
                                        </p>
                                        <ul className="mt-2 list-disc space-y-1 pl-5 text-gray-700">
                                            {flags.map((flag) => (
                                                <li
                                                    key={flag}
                                                    className="capitalize"
                                                >
                                                    {flag}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="rounded-md border border-gray-200 p-4">
                                        <p className="font-semibold text-gray-900">
                                            Not covered
                                        </p>
                                        <p className="mt-2 text-gray-700">
                                            Crop identity, yield, income, loan
                                            approval, ownership, and legal status
                                            are outside this satellite report.
                                        </p>
                                    </div>
                                </div>
                            </section>

                            <footer className="mt-10 border-t border-gray-200 pt-4 text-xs text-gray-500">
                                <div className="flex justify-between gap-6">
                                    <p>
                                        Prepared by{" "}
                                        {formValues.analystName || "Analyst"} ·{" "}
                                        {formValues.institution ||
                                            "Institution"}
                                    </p>
                                    <p>Generated locally by FarmTrust</p>
                                </div>
                            </footer>
                        </article>
                    </Card>
                </div>

                {/* Right Panel: Export Form */}
                <div className="no-print min-w-0">
                    <Card padding="md">
                        <CardHeader>
                            <CardTitle>Export Settings</CardTitle>
                        </CardHeader>

                        <div className="mt-6 space-y-4">
                            {/* Analyst Name */}
                            <FormField label="Analyst Name" required>
                                <Input
                                    placeholder="Your name"
                                    value={formValues.analystName}
                                    onChange={(e) =>
                                        setFormValues({
                                            ...formValues,
                                            analystName: e.target.value,
                                        })
                                    }
                                />
                            </FormField>

                            {/* Institution */}
                            <FormField label="Institution" required>
                                <Input
                                    placeholder="Bank or organization name"
                                    value={formValues.institution}
                                    onChange={(e) =>
                                        setFormValues({
                                            ...formValues,
                                            institution: e.target.value,
                                        })
                                    }
                                />
                            </FormField>

                            {/* Report Date */}
                            <FormField label="Report Date" required>
                                <Input
                                    type="date"
                                    value={formValues.reportDate}
                                    onChange={(e) =>
                                        setFormValues({
                                            ...formValues,
                                            reportDate: e.target.value,
                                        })
                                    }
                                />
                            </FormField>

                            {/* Report Type */}
                            <FormField label="Report Type">
                                <Select
                                    value={formValues.reportType}
                                    onChange={(e) =>
                                        setFormValues({
                                            ...formValues,
                                            reportType: e.target.value as
                                                | "full"
                                                | "executive"
                                                | "risk",
                                        })
                                    }
                                >
                                    <option value="full">
                                        Full Assessment
                                    </option>
                                    <option value="executive">
                                        Executive Summary
                                    </option>
                                    <option value="risk">Risk Review</option>
                                </Select>
                            </FormField>

                            {/* Include Sections */}
                            <div>
                                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
                                    Include Sections
                                </p>
                                <div className="space-y-2">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={
                                                formValues.includeVegetation
                                            }
                                            onChange={(e) =>
                                                setFormValues({
                                                    ...formValues,
                                                    includeVegetation:
                                                        e.target.checked,
                                                })
                                            }
                                            className="w-4 h-4 rounded border-gray-300 text-teal-600"
                                        />
                                        <span className="text-sm text-gray-700">
                                            Vegetation Indicators
                                        </span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={
                                                formValues.includeRiskFlags
                                            }
                                            onChange={(e) =>
                                                setFormValues({
                                                    ...formValues,
                                                    includeRiskFlags:
                                                        e.target.checked,
                                                })
                                            }
                                            className="w-4 h-4 rounded border-gray-300 text-teal-600"
                                        />
                                        <span className="text-sm text-gray-700">
                                            Risk Flags
                                        </span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formValues.includeSummary}
                                            onChange={(e) =>
                                                setFormValues({
                                                    ...formValues,
                                                    includeSummary:
                                                        e.target.checked,
                                                })
                                            }
                                            className="w-4 h-4 rounded border-gray-300 text-teal-600"
                                        />
                                        <span className="text-sm text-gray-700">
                                            Summary Text
                                        </span>
                                    </label>
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="pt-4 space-y-2">
                                <Button
                                    className="w-full"
                                    onClick={handlePrint}
                                >
                                    Print / Save PDF
                                </Button>
                                <Button
                                    variant="secondary"
                                    className="w-full"
                                    onClick={handleEmailShare}
                                >
                                    Share via Email
                                </Button>
                            </div>

                            {/* Disclaimer */}
                            <div className="pt-4 border-t border-gray-200">
                                <p className="text-xs text-gray-400">
                                    Reports are generated locally. No data is
                                    transmitted.
                                </p>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}

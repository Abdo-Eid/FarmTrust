"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useLand } from "@/hooks/useLand";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Skeleton } from "@/components/ui/Skeleton";

// Dynamic imports for react-pdf (no SSR)
const PDFViewer = dynamic(
    () => import("@/components/pdf/pdf-renderer").then((mod) => mod.PDFViewer),
    { ssr: false, loading: () => <div className="h-96 bg-gray-100 rounded" /> },
);

// Wrapper for dynamic PDF download button
const PDFDownloadWrapper = dynamic(
    () =>
        import("@/components/pdf/LandReportPDF").then(
            (mod) => mod.ReportDownloadButton,
        ),
    { ssr: false },
);

const LandReportPDFDynamic = dynamic(
    () =>
        import("@/components/pdf/LandReportPDF").then(
            (mod) => mod.LandReportPDF,
        ),
    { ssr: false },
);

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

    return (
        <div>
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

            <div className="p-6 flex gap-6">
                {/* Left Panel: PDF Preview (60%) */}
                <div className="w-3/5">
                    <Card padding="md">
                        <CardHeader>
                            <CardTitle>Report Preview</CardTitle>
                        </CardHeader>

                        <div className="mt-4">
                            {typeof window !== "undefined" ? (
                                <div style={{ width: "100%", height: 600 }}>
                                    <PDFViewer
                                        style={{
                                            width: "100%",
                                            height: "100%",
                                        }}
                                    >
                                        <LandReportPDFDynamic
                                            land={land}
                                            analystName={
                                                formValues.analystName ||
                                                "Analyst"
                                            }
                                            institution={
                                                formValues.institution ||
                                                "Institution"
                                            }
                                            reportDate={formValues.reportDate}
                                        />
                                    </PDFViewer>
                                </div>
                            ) : (
                                <div className="h-96 bg-gray-100 rounded flex items-center justify-center">
                                    <p className="text-gray-500">
                                        PDF preview requires a modern browser
                                    </p>
                                </div>
                            )}
                        </div>
                    </Card>
                </div>

                {/* Right Panel: Export Form (40%) */}
                <div className="w-2/5">
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
                                <div className="w-full">
                                    <PDFDownloadWrapper
                                        land={land}
                                        analystName={
                                            formValues.analystName || "Analyst"
                                        }
                                        institution={
                                            formValues.institution ||
                                            "Institution"
                                        }
                                        reportDate={formValues.reportDate}
                                    />
                                </div>
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

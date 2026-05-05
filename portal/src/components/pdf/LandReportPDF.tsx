"use client";

import { lazy, Suspense } from "react";
import dynamic from "next/dynamic";
import type { LandResult } from "@/lib/types";

const PDFDownloadLink = dynamic(
    () =>
        import("@/components/pdf/pdf-renderer").then((mod) => ({
            default: mod.PDFDownloadLink,
        })),
    { ssr: false },
);

const ReportDocumentLazy = lazy(() =>
    import("./ReportDocument").then((mod) => ({ default: mod.ReportDocument })),
);

export function LandReportPDF(props: {
    land: LandResult;
    analystName: string;
    institution: string;
    reportDate: string;
}) {
    return (
        <Suspense fallback={null}>
            <ReportDocumentLazy {...props} />
        </Suspense>
    );
}

interface ReportDownloadButtonProps {
    land: LandResult;
    analystName: string;
    institution: string;
    reportDate: string;
}

export function ReportDownloadButton({
    land,
    analystName,
    institution,
    reportDate,
}: ReportDownloadButtonProps) {
    return (
        <PDFDownloadLink
            document={
                <LandReportPDF
                    land={land}
                    analystName={analystName}
                    institution={institution}
                    reportDate={reportDate}
                />
            }
            fileName={`farmtrust-${land.id}.pdf`}
            className="inline-flex items-center justify-center gap-2 font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-1 w-full px-4 py-2 text-sm bg-teal-700 text-white hover:bg-teal-800 disabled:opacity-50"
        >
            Download PDF Report
        </PDFDownloadLink>
    );
}

"use client";

import React from "react";
import {
    Document,
    Page,
    Text,
    View,
    StyleSheet,
} from "@/components/pdf/pdf-renderer";
import type { LandResult } from "@/lib/types";

// Color constants
const TEAL = "#1abc9c";
const TEAL_DARK = "#16a085";
const TEAL_900 = "#0d2b27";
const GOLD = "#D4A373";
const GRAY = "#6b7280";

// Label maps
const STATUS_LABELS: Record<string, string> = {
    active: "Active — Cultivated",
    intermittent: "Intermittent",
    inactive: "Inactive",
    encroachment: "Encroachment Detected",
};

const RISK_LABELS: Record<string, string> = {
    low: "Low Risk",
    medium: "Medium Risk",
    high: "High Risk",
};

const TREND_LABELS: Record<string, string> = {
    improving: "Improving",
    stable: "Stable",
    declining: "Declining",
};

const SATELLITE_EVIDENCE_LABELS: Record<string, string> = {
    good: "Good Coverage",
    fair: "Fair Coverage",
    limited: "Limited Coverage",
    insufficient: "Insufficient Evidence",
};

const NEIGHBOR_LABELS: Record<string, string> = {
    above_avg: "Above Average",
    avg: "Average",
    below_avg: "Below Average",
};

// Stylesheet
const styles = StyleSheet.create({
    page: {
        padding: 40,
        fontFamily: "Helvetica",
        fontSize: 10,
        color: "#111827",
    },
    coverHeader: {
        backgroundColor: TEAL_900,
        height: 120,
        marginLeft: -40,
        marginRight: -40,
        marginTop: -40,
        paddingLeft: 40,
        paddingRight: 40,
        paddingTop: 20,
        paddingBottom: 20,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: "bold",
        color: "white",
        marginBottom: 4,
    },
    headerSubtitle: {
        fontSize: 11,
        color: TEAL,
    },
    landName: {
        fontSize: 22,
        fontWeight: "bold",
        color: "#111827",
        marginTop: 24,
        marginBottom: 16,
    },
    h1: {
        fontSize: 18,
        fontWeight: "bold",
        marginBottom: 4,
    },
    h2: {
        fontSize: 13,
        fontWeight: "bold",
        marginBottom: 8,
        marginTop: 16,
    },
    sectionHeading: {
        borderLeftWidth: 3,
        borderLeftColor: TEAL,
        paddingLeft: 8,
        marginBottom: 8,
        marginTop: 16,
        fontSize: 13,
        fontWeight: "bold",
    },
    metaTable: {
        display: "flex",
        flexDirection: "column",
        gap: 4,
        marginBottom: 16,
    },
    metaRow: {
        flexDirection: "row",
        marginBottom: 4,
    },
    metaLabel: {
        width: 120,
        color: GRAY,
        fontSize: 9,
        fontWeight: "bold",
    },
    metaValue: {
        flex: 1,
        fontSize: 9,
    },
    hr: {
        borderBottomWidth: 1,
        borderBottomColor: "#e5e7eb",
        marginVertical: 12,
    },
    footer: {
        position: "absolute" as const,
        bottom: 30,
        left: 40,
        right: 40,
        fontSize: 8,
        color: "#9ca3af",
        textAlign: "center" as const,
    },
    preparedSection: {
        marginTop: 16,
    },
    preparedLabel: {
        fontSize: 9,
        fontWeight: "bold",
        color: GRAY,
        marginBottom: 4,
    },
    preparedValue: {
        fontSize: 9,
        marginBottom: 2,
    },
    decisionRow: {
        flexDirection: "row",
        gap: 16,
        marginBottom: 12,
    },
    decisionCol: {
        flex: 1,
    },
    decisionLabel: {
        fontSize: 8,
        color: GRAY,
        fontWeight: "bold",
        marginBottom: 2,
    },
    decisionValue: {
        fontSize: 11,
        fontWeight: "bold",
    },
    confidenceBlock: {
        marginTop: 12,
        marginBottom: 12,
    },
    confidenceStatus: {
        fontSize: 10,
        fontWeight: "bold",
        marginBottom: 4,
    },
    confidenceRationale: {
        fontSize: 9,
        color: GRAY,
        fontStyle: "italic",
    },
    bulletList: {
        marginBottom: 8,
    },
    bulletItem: {
        fontSize: 9,
        marginBottom: 4,
    },
    indicatorsTable: {
        display: "flex",
        flexDirection: "column",
        gap: 0,
        marginBottom: 12,
    },
    indicatorRow: {
        flexDirection: "row",
        gap: 12,
        paddingBottom: 4,
        borderBottomWidth: 1,
        borderBottomColor: "#f0f0f0",
    },
    indicatorCol: {
        flex: 1,
    },
    indicatorLabel: {
        fontSize: 8,
        color: GRAY,
        fontWeight: "bold",
        marginBottom: 2,
    },
    indicatorValue: {
        fontSize: 9,
    },
    summaryText: {
        fontSize: 10,
        color: GRAY,
        lineHeight: 1.4,
    },
});

interface ReportDocumentProps {
    land: LandResult;
    analystName: string;
    institution: string;
    reportDate: string;
}

export function ReportDocument({
    land,
    analystName,
    institution,
    reportDate,
}: ReportDocumentProps) {
    const statusLabel =
        land.land_status && STATUS_LABELS[land.land_status]
            ? STATUS_LABELS[land.land_status]
            : land.land_status || "Unknown";

    const riskLabel =
        land.risk_tier && RISK_LABELS[land.risk_tier]
            ? RISK_LABELS[land.risk_tier]
            : land.risk_tier || "Unknown";

    const trendLabel =
        land.trend_2y && TREND_LABELS[land.trend_2y]
            ? TREND_LABELS[land.trend_2y]
            : land.trend_2y || "Unknown";

    const neighborLabel =
        land.indicators?.neighbor_comparison &&
        NEIGHBOR_LABELS[land.indicators.neighbor_comparison]
            ? NEIGHBOR_LABELS[land.indicators.neighbor_comparison]
            : land.indicators?.neighbor_comparison || "N/A";

    const formattedDate = new Date(land.submitted_at).toLocaleDateString(
        "en-US",
        {
            year: "numeric",
            month: "long",
            day: "numeric",
        },
    );

    return (
        <Document title={`FarmTrust Report - ${land.name}`}>
            {/* Cover Page */}
            <Page size="A4" style={styles.page}>
                <View style={styles.coverHeader}>
                    <Text style={styles.headerTitle}>FARMTRUST</Text>
                    <Text style={styles.headerSubtitle}>
                        Satellite Land Assessment Report
                    </Text>
                </View>

                <Text style={styles.landName}>{land.name}</Text>

                <View style={styles.metaTable}>
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Land ID</Text>
                        <Text style={styles.metaValue}>{land.id}</Text>
                    </View>
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Governorate</Text>
                        <Text style={styles.metaValue}>{land.governorate}</Text>
                    </View>
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Area</Text>
                        <Text style={styles.metaValue}>
                            {land.area_feddan.toFixed(2)} feddan
                        </Text>
                    </View>
                    <View style={styles.metaRow}>
                        <Text style={styles.metaLabel}>Submitted</Text>
                        <Text style={styles.metaValue}>{formattedDate}</Text>
                    </View>
                </View>

                <View style={styles.hr} />

                <View style={styles.preparedSection}>
                    <Text style={styles.preparedLabel}>PREPARED BY</Text>
                    <Text style={styles.preparedValue}>{analystName}</Text>
                    <Text style={styles.preparedValue}>{institution}</Text>
                    <Text style={styles.preparedValue}>{reportDate}</Text>
                </View>

                <Text
                    style={styles.footer}
                    render={({ pageNumber, totalPages }) =>
                        `CONFIDENTIAL — For internal bank use only | Page ${pageNumber} of ${totalPages}`
                    }
                />
            </Page>

            {/* Assessment Page */}
            <Page size="A4" style={styles.page}>
                {/* Assessment Decision Section */}
                <Text style={styles.sectionHeading}>ASSESSMENT DECISION</Text>

                <View style={styles.decisionRow}>
                    <View style={styles.decisionCol}>
                        <Text style={styles.decisionLabel}>Status</Text>
                        <Text style={styles.decisionValue}>{statusLabel}</Text>
                    </View>
                    <View style={styles.decisionCol}>
                        <Text style={styles.decisionLabel}>Risk Tier</Text>
                        <Text style={styles.decisionValue}>{riskLabel}</Text>
                    </View>
                    <View style={styles.decisionCol}>
                        <Text style={styles.decisionLabel}>2-Year Trend</Text>
                        <Text style={styles.decisionValue}>{trendLabel}</Text>
                    </View>
                </View>

                {/* Satellite Evidence Coverage */}
                {land.satellite_evidence_coverage && (
                    <View style={styles.confidenceBlock}>
                        <Text style={styles.confidenceStatus}>
                            Satellite Evidence Coverage: {SATELLITE_EVIDENCE_LABELS[land.satellite_evidence_coverage.status]}
                        </Text>
                        <Text style={styles.confidenceRationale}>
                            {land.satellite_evidence_coverage.rationale}
                        </Text>
                    </View>
                )}

                {/* Assessment Confidence Block */}
                {land.confidence && (
                    <View style={styles.confidenceBlock}>
                        <Text
                            style={{
                                ...styles.confidenceStatus,
                                color:
                                    land.confidence.status === "high"
                                        ? "#059669"
                                        : land.confidence.status === "medium"
                                          ? "#d97706"
                                          : "#dc2626",
                            }}
                        >
                            Assessment Confidence: {land.confidence.status.toUpperCase()}
                        </Text>
                        <Text style={styles.confidenceRationale}>
                            {land.confidence.rationale}
                        </Text>
                    </View>
                )}

                {/* Risk Flags Section */}
                <Text style={styles.sectionHeading}>RISK FLAGS</Text>
                {land.flags && land.flags.length > 0 ? (
                    <View style={styles.bulletList}>
                        {land.flags.map((flag, idx) => (
                            <Text key={idx} style={styles.bulletItem}>
                                • {flag}
                            </Text>
                        ))}
                    </View>
                ) : (
                    <Text style={styles.bulletItem}>
                        No risk flags identified
                    </Text>
                )}

                {/* Vegetation Indicators Section */}
                <Text style={styles.sectionHeading}>VEGETATION INDICATORS</Text>
                <View style={styles.indicatorsTable}>
                    <View style={styles.indicatorRow}>
                        <View style={styles.indicatorCol}>
                            <Text style={styles.indicatorLabel}>NDVI Peak</Text>
                            <Text style={styles.indicatorValue}>
                                {land.indicators?.ndvi_peak
                                    ? land.indicators.ndvi_peak.toFixed(3)
                                    : "N/A"}
                            </Text>
                        </View>
                        <View style={styles.indicatorCol}>
                            <Text style={styles.indicatorLabel}>NDVI AUC</Text>
                            <Text style={styles.indicatorValue}>
                                {land.indicators?.ndvi_auc
                                    ? land.indicators.ndvi_auc.toFixed(3)
                                    : "N/A"}
                            </Text>
                        </View>
                        <View style={styles.indicatorCol}>
                            <Text style={styles.indicatorLabel}>
                                Cloud-Free Scenes
                            </Text>
                            <Text style={styles.indicatorValue}>
                                {land.indicators?.cloud_free_scenes ?? "N/A"}
                            </Text>
                        </View>
                        <View style={styles.indicatorCol}>
                            <Text style={styles.indicatorLabel}>
                                Neighbor Comparison
                            </Text>
                            <Text style={styles.indicatorValue}>
                                {neighborLabel}
                            </Text>
                        </View>
                    </View>
                </View>

                {/* Summary Section */}
                <Text style={styles.sectionHeading}>SUMMARY</Text>
                <Text style={styles.summaryText}>
                    {land.report_summary || "No summary available"}
                </Text>

                <Text style={styles.footer}>
                    CONFIDENTIAL — For internal bank use only
                </Text>
            </Page>
        </Document>
    );
}

import { clsx } from "clsx";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { EvidencePacket, ClaimLayer, PacketClaim } from "@/lib/types";
import { ActivityTimeline } from "./ActivityTimeline";
import { TrackRecordGauge } from "./TrackRecordGauge";
import {
    LAYER_META,
    LAYER_ORDER,
    CONFIDENCE_PILL,
    SEVERITY_PILL,
    OVERALL_CONFIDENCE_PILL,
    humanizeKey,
} from "./packet-style";

function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{children}</p>
    );
}

function ClaimRow({ claim }: { claim: PacketClaim }) {
    return (
        <div className="py-2.5 first:pt-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-gray-800 leading-relaxed">{claim.claim}</p>
                <Badge className={clsx("flex-shrink-0 capitalize", CONFIDENCE_PILL[claim.confidence])}>
                    {claim.confidence}
                </Badge>
            </div>
            {claim.rests_on && (
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{claim.rests_on}</p>
            )}
        </div>
    );
}

function LayerCard({ layer, claims }: { layer: ClaimLayer; claims: PacketClaim[] }) {
    const meta = LAYER_META[layer];
    return (
        <Card padding="none" className={clsx("border-l-4 overflow-hidden", meta.border)}>
            <div className={clsx("px-4 py-3", meta.bg)}>
                <div className="flex items-center gap-2">
                    <span className={clsx("material-symbols-outlined text-base", meta.text)}>{meta.icon}</span>
                    <span className={clsx("text-sm font-semibold uppercase tracking-wide", meta.text)}>
                        {meta.label}
                    </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{meta.blurb}</p>
            </div>
            <div className="px-4 py-2 divide-y divide-gray-100">
                {claims.length === 0 ? (
                    <p className="text-sm text-gray-400 py-2">No items.</p>
                ) : (
                    claims.map((c, i) => <ClaimRow key={`${c.id}-${i}`} claim={c} />)
                )}
            </div>
        </Card>
    );
}

export function EvidencePacketReport({ packet }: { packet: EvidencePacket }) {
    const { headline, track_record, activity_record, risk_register, indicators } = packet;
    const landRisks = risk_register.filter((r) => r.kind === "land_risk");
    const limitations = risk_register.filter((r) => r.kind === "evidence_limitation");
    const isManualReview = packet.assessment_status === "manual_review_required";

    return (
        <div className="space-y-5">
            {/* Verdict */}
            <Card>
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div>
                        <SectionLabel>Assessment</SectionLabel>
                        <h2 className="text-2xl font-bold text-gray-900">{headline.state_label}</h2>
                        {headline.cropping_intensity && (
                            <p className="text-sm text-gray-500 mt-1">{headline.cropping_intensity}</p>
                        )}
                    </div>
                    <Badge
                        className={clsx(
                            "self-start text-sm px-3 py-1",
                            OVERALL_CONFIDENCE_PILL[headline.overall_confidence],
                        )}
                    >
                        <span className="material-symbols-outlined text-sm">target</span>
                        {headline.overall_confidence} confidence
                    </Badge>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed mt-3">{headline.summary}</p>
            </Card>

            {isManualReview && (
                <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 text-amber-800 rounded-md px-4 py-3 text-sm">
                    <span className="material-symbols-outlined text-base">flag</span>
                    <span>
                        Satellite evidence did not meet the automated-assessment threshold; this read is
                        provided for manual review, not as a final determination.
                    </span>
                </div>
            )}

            {/* Four-layer read */}
            <div>
                <SectionLabel>The read, in four layers</SectionLabel>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {LAYER_ORDER.map((layer) => (
                        <LayerCard
                            key={layer}
                            layer={layer}
                            claims={packet.claims.filter((c) => c.layer === layer)}
                        />
                    ))}
                </div>
            </div>

            {/* Activity record */}
            <Card>
                <CardHeader>
                    <CardTitle>Activity record</CardTitle>
                </CardHeader>
                <ActivityTimeline activity={activity_record} />
            </Card>

            {/* Track record */}
            <Card>
                <CardHeader>
                    <CardTitle>Track record</CardTitle>
                </CardHeader>
                <TrackRecordGauge track={track_record} />
            </Card>

            {/* Risk register */}
            <Card>
                <CardHeader>
                    <CardTitle>Risk register</CardTitle>
                </CardHeader>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <RiskColumn
                        title="Land risks"
                        icon="warning"
                        items={landRisks}
                        emptyText="No land risks flagged."
                    />
                    <RiskColumn
                        title="Evidence limitations"
                        icon="info"
                        items={limitations}
                        emptyText="No evidence limitations recorded."
                    />
                </div>
            </Card>

            {/* Limitations (method/data) */}
            {packet.limitations.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Limitations</CardTitle>
                    </CardHeader>
                    <ul className="space-y-2">
                        {packet.limitations.map((l, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                                <span className="material-symbols-outlined text-gray-400 text-base mt-0.5">
                                    chevron_right
                                </span>
                                <span className="leading-relaxed">{l}</span>
                            </li>
                        ))}
                    </ul>
                </Card>
            )}

            {/* Indicators */}
            <Card>
                <CardHeader>
                    <CardTitle>Indicators</CardTitle>
                </CardHeader>
                {Object.keys(indicators.values).length === 0 ? (
                    <p className="text-sm text-gray-400">No indicator values available.</p>
                ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {Object.entries(indicators.values).map(([key, value]) => (
                        <div
                            key={key}
                            className="bg-gray-50 border border-gray-200 rounded-md p-3"
                            title={indicators.interpretation_notes[key] ?? undefined}
                        >
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                {humanizeKey(key)}
                            </p>
                            <p className="text-lg font-bold text-gray-900 mt-0.5">
                                {value == null ? "—" : value.toFixed(3)}
                            </p>
                            {indicators.interpretation_notes[key] && (
                                <p className="text-[11px] text-gray-400 mt-1 leading-snug">
                                    {indicators.interpretation_notes[key]}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
                )}
            </Card>

            {/* Boundaries — what this does NOT tell you */}
            <div className="bg-gray-900 text-white rounded-md p-5 shadow-panel">
                <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-base text-gray-300">block</span>
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-100">
                        What this does not tell you
                    </h3>
                </div>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
                    {packet.boundaries.map((b, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                            <span className="material-symbols-outlined text-base text-gray-500 mt-0.5">close</span>
                            <span className="leading-relaxed">{b}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Provenance footer */}
            <p className="text-xs text-gray-400 leading-relaxed">
                Generated from satellite greenness only — not crop identity, yield, or financial outcome.
                Built deterministically from {packet.source_artifacts.join(", ")} (packet v{packet.packet_version}).
            </p>
        </div>
    );
}

function RiskColumn({
    title,
    icon,
    items,
    emptyText,
}: {
    title: string;
    icon: string;
    items: EvidencePacket["risk_register"];
    emptyText: string;
}) {
    return (
        <div>
            <div className="flex items-center gap-1.5 mb-2">
                <span className="material-symbols-outlined text-gray-400 text-base">{icon}</span>
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{title}</span>
            </div>
            {items.length === 0 ? (
                <p className="text-sm text-gray-400">{emptyText}</p>
            ) : (
                <ul className="space-y-2.5">
                    {items.map((r, i) => (
                        <li key={`${r.code ?? "lim"}-${i}`} className="border border-gray-100 rounded-md p-3 bg-gray-50">
                            <div className="flex items-center justify-between gap-2 mb-1">
                                <span className="text-sm font-medium text-gray-900">{r.item}</span>
                                <Badge className={clsx("capitalize", SEVERITY_PILL[r.severity])}>{r.severity}</Badge>
                            </div>
                            <p className="text-xs text-gray-600 leading-relaxed">{r.reason}</p>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

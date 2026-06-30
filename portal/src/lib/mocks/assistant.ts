import type { AssistantLine, AssistantResponse, EvidencePacket, LandResult } from "../types";
import { mockEvidencePacket } from "./packet";

// TS port of farmtrust_core.report.brief.build_deterministic_brief, so mock
// lands narrate offline with the same shape the backend's no-LLM path returns.

const LAYER_ORDER = ["observed", "interpreted", "confidence", "watch"] as const;

function line(
    text: string,
    claim_type: string,
    source: string,
    confidence?: string,
    section?: string,
): AssistantLine {
    return { text, claim_type, source, confidence, section };
}

export function mockBrief(packet: EvidencePacket): AssistantLine[] {
    const lines: AssistantLine[] = [];
    const h = packet.headline;
    if (h?.summary) {
        lines.push(line(h.summary, "deterministic_pipeline_result", "headline.summary", h.overall_confidence, "verdict"));
    }
    if (h?.cropping_intensity) {
        lines.push(line(h.cropping_intensity, "model_derived_analysis", "headline.cropping_intensity", undefined, "verdict"));
    }
    for (const layer of LAYER_ORDER) {
        for (const c of packet.claims.filter((c) => c.layer === layer)) {
            lines.push(line(c.claim, c.claim_type ?? "unknown", c.id, c.confidence, layer));
        }
    }
    const t = packet.track_record;
    if (t?.note) {
        const flag = t.provisional ? " (provisional)" : "";
        const prefix = t.status_so_far ? `Track record so far: ${t.status_so_far}${flag}. ` : "";
        lines.push(line(`${prefix}${t.note}`, "model_derived_analysis", "track_record",
            t.provisional ? "provisional" : "moderate", "track_record"));
    }
    for (const item of packet.risk_register) {
        const claimType = item.kind === "land_risk" ? "deterministic_pipeline_result" : "measured_observation";
        const label = item.kind === "land_risk" ? "Land risk" : "Evidence limitation";
        lines.push(line(`${label}: ${item.item} — ${item.reason}`.replace(/ —\s*$/, ""),
            claimType, `risk_register:${item.code ?? item.item}`, undefined, "risk"));
    }
    if (packet.boundaries.length) {
        lines.push(line(`What this does NOT tell you: ${packet.boundaries.join("; ")}.`,
            "boundary_exclusion", "boundaries", undefined, "boundaries"));
    }
    return lines;
}

export function mockNarrate(land: LandResult): AssistantResponse {
    return {
        lines: mockBrief(mockEvidencePacket(land)),
        source_mode: "deterministic",
        fallback_used: true,
        model: undefined,
    };
}

export function mockChat(land: LandResult): AssistantResponse {
    const preface = line(
        "The assistant model is not enabled for this demo land, so here is the grounded brief for this report.",
        "deterministic_pipeline_result",
        "assistant",
        undefined,
        "chat",
    );
    return {
        lines: [preface, ...mockBrief(mockEvidencePacket(land))],
        source_mode: "deterministic",
        fallback_used: true,
        model: undefined,
    };
}

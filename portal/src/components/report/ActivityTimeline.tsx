import { clsx } from "clsx";
import type { PacketActivityRecord } from "@/lib/types";
import { calendarStyle, CALENDAR_STYLE } from "./packet-style";

function ms(date?: string): number | null {
    if (!date) return null;
    const t = Date.parse(date);
    return Number.isNaN(t) ? null : t;
}

function fmt(t: number): string {
    return new Date(t).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

/**
 * A deterministic, data-driven SVG strip of the detected vegetation activity
 * cycles. Each cycle is one segment; colour is the broad summer/winter calendar
 * descriptor (never a crop). Open cycles are drawn hatched/translucent.
 */
export function ActivityTimeline({ activity }: { activity: PacketActivityRecord }) {
    const cycles = activity.cycles.filter(
        (c) => ms(c.start_date) !== null && ms(c.end_date) !== null,
    );

    if (cycles.length === 0) {
        return <p className="text-sm text-gray-500">No detected cycles to display.</p>;
    }

    const t0 = Math.min(...cycles.map((c) => ms(c.start_date)!));
    const tEnd = Math.max(...cycles.map((c) => ms(c.end_date)!));
    // If every cycle collapses to (about) one instant, fall back to even index spacing.
    const degenerate = tEnd - t0 < 1;
    const t1 = degenerate ? t0 + 1 : tEnd;
    const span = t1 - t0;

    const W = 720;
    const H = 104;
    const padX = 10;
    const trackY = 44;
    const trackH = 28;
    const innerW = W - 2 * padX;
    const x = (t: number) => padX + ((t - t0) / span) * innerW;

    function geom(start: number, end: number, peak: number | null, i: number) {
        if (degenerate) {
            const cw = innerW / cycles.length;
            return { xs: padX + i * cw + 2, xe: padX + (i + 1) * cw - 2, xp: padX + (i + 0.5) * cw };
        }
        const xs = x(start);
        const xe = Math.max(xs + 5, x(end));
        const raw = peak != null ? x(peak) : (xs + xe) / 2;
        return { xs, xe, xp: Math.min(xe, Math.max(xs, raw)) }; // clamp peak into its own cycle
    }

    const usedLabels = Array.from(
        new Set(cycles.map((c) => (c.season_calendar_label && CALENDAR_STYLE[c.season_calendar_label] ? c.season_calendar_label : "transition"))),
    );

    return (
        <div>
            <div className="w-full overflow-x-auto">
                <svg
                    viewBox={`0 0 ${W} ${H}`}
                    className="w-full"
                    style={{ minWidth: 480 }}
                    role="img"
                    aria-label="Detected vegetation activity cycles over time"
                >
                    <line
                        x1={padX}
                        y1={trackY + trackH + 10}
                        x2={W - padX}
                        y2={trackY + trackH + 10}
                        stroke="#e5e7eb"
                        strokeWidth={1}
                    />
                    {cycles.map((c, i) => {
                        const { xs, xe, xp } = geom(
                            ms(c.start_date)!,
                            ms(c.end_date)!,
                            c.peak_date != null ? ms(c.peak_date) : null,
                            i,
                        );
                        const cal = calendarStyle(c.season_calendar_label);
                        const w = Math.max(5, xe - xs);
                        const dates = [c.start_date, c.peak_date, c.end_date].filter(Boolean).join(" → ");
                        return (
                            <g key={`${c.season_id ?? "cycle"}-${i}`}>
                                <title>{`${cal.label} cycle${c.is_open ? " (open)" : ""}${dates ? ` · ${dates}` : ""}`}</title>
                                <rect
                                    x={xs}
                                    y={trackY}
                                    width={w}
                                    height={trackH}
                                    rx={3}
                                    fill={cal.fill}
                                    fillOpacity={c.is_open ? 0.4 : 0.85}
                                    stroke={cal.fill}
                                    strokeWidth={c.is_open ? 1.5 : 0}
                                    strokeDasharray={c.is_open ? "4 3" : undefined}
                                />
                                <circle cx={xp} cy={trackY + trackH / 2} r={3.5} fill="#ffffff" stroke={cal.fill} strokeWidth={2} />
                                {w > 36 && (
                                    <text x={(xs + xe) / 2} y={trackY - 7} textAnchor="middle" fontSize={10} fill="#475569">
                                        {cal.label}
                                    </text>
                                )}
                            </g>
                        );
                    })}
                    <text x={padX} y={H - 8} fontSize={10} fill="#94a3b8">
                        {fmt(t0)}
                    </text>
                    <text x={W - padX} y={H - 8} fontSize={10} fill="#94a3b8" textAnchor="end">
                        {fmt(t1)}
                    </text>
                </svg>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-3">
                {usedLabels.map((label) => {
                    const cal = calendarStyle(label);
                    return (
                        <span key={label} className="inline-flex items-center gap-1.5 text-xs text-gray-500">
                            <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: cal.fill }} />
                            {cal.label} cycle
                        </span>
                    );
                })}
                <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
                    <span className="inline-block w-3 h-3 rounded-sm border border-gray-400 border-dashed" />
                    Open (still in progress)
                </span>
            </div>
            <div className={clsx("mt-3 flex flex-wrap gap-4 text-xs text-gray-500")}>
                <span>
                    <span className="font-semibold text-gray-700">{activity.complete_window_count}</span> complete
                </span>
                <span>
                    <span className="font-semibold text-gray-700">{activity.open_window_count}</span> open
                </span>
                <span>
                    <span className="font-semibold text-gray-700">{activity.borderline_window_count}</span> borderline
                </span>
            </div>
        </div>
    );
}

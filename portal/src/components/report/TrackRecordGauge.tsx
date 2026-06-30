import { ProgressRing } from "@/components/ui/ProgressRing";
import { Badge } from "@/components/ui/Badge";
import type { PacketTrackRecord } from "@/lib/types";
import { TRACK_STATUS_LABEL } from "./packet-style";

export function TrackRecordGauge({ track }: { track: PacketTrackRecord }) {
    const pct = Math.round(Math.min(1, Math.max(0, track.fraction)) * 100);

    return (
        <div className="flex flex-col sm:flex-row items-center gap-5">
            <ProgressRing
                percent={pct}
                size={120}
                strokeWidth={10}
                label={`${track.seasons_observed}/${track.seasons_for_certifiable_trend}`}
                sublabel="record length"
                color="#1abc9c"
            />
            <div className="flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-sm font-semibold text-gray-900">
                        Status so far: {TRACK_STATUS_LABEL[track.status_so_far]}
                    </span>
                    {track.provisional && (
                        <Badge className="bg-slate-100 text-slate-700 border-slate-200">Provisional</Badge>
                    )}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">{track.note}</p>
            </div>
        </div>
    );
}

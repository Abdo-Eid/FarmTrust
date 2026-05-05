"use client";
import { useState, use, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useLand } from "@/hooks/useLand";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    ResponsiveContainer,
    Tooltip,
} from "recharts";
import { RiskFlag } from "@/lib/types";

const GeoMap = dynamic(
    () =>
        import("@/components/map/Map").then((mod) => ({
            default: mod.Map,
        })),
    {
        ssr: false,
    },
);

const iconMap: Record<RiskFlag, string> = {
    waterlogging: "water_drop",
    salinity: "science",
    abandonment: "grass",
    encroachment: "report",
};

export default function WorkbenchPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const [notes, setNotes] = useState("");
    const { data: land, isLoading } = useLand(id);

    const handleMapReady = useCallback(
        (map: any) => {
            if (land?.geometry) {
                try {
                    // Dynamically import L only when needed (client-side)
                    import("leaflet").then((Leaflet) => {
                        const geoJsonLayer = Leaflet.geoJSON(
                            land.geometry as any,
                        );
                        const bounds = geoJsonLayer.getBounds();
                        if (bounds && bounds.isValid()) {
                            map.fitBounds(bounds, {
                                padding: [80, 80],
                                maxZoom: 14,
                            });
                        }
                    });
                } catch (err) {
                    console.error("Error fitting bounds:", err);
                }
            }
        },
        [land?.geometry],
    );

    if (isLoading) {
        return (
            <div className="w-screen h-screen flex items-center justify-center bg-gray-50">
                <p className="text-gray-600">Loading land data...</p>
            </div>
        );
    }

    if (!land) {
        return (
            <div className="w-screen h-screen flex items-center justify-center bg-gray-50">
                <p className="text-gray-600">Land not found</p>
            </div>
        );
    }

    return (
        <div className="flex h-screen overflow-hidden bg-gray-50">
            {/* Left 70%: Map */}
            <div className="flex-1" style={{ width: "70%" }}>
                <GeoMap
                    geometry={land.geometry || null}
                    showLayerControls={true}
                    defaultLayerMode="satellite"
                    onMapReady={handleMapReady}
                />
            </div>

            {/* Right 30%: Sidebar */}
            <div
                className="overflow-y-auto bg-white border-l border-gray-200"
                style={{ width: "30%" }}
            >
                <div className="p-4 space-y-6">
                    {/* Header */}
                    <div className="border-b border-gray-200 pb-4">
                        <h1 className="text-lg font-semibold text-teal-700">
                            {land.name}
                        </h1>
                        <p className="text-xs text-gray-600 mt-1">
                            Evidence Workbench
                        </p>
                    </div>

                    {/* NDVI Trend */}
                    <div>
                        <p className="text-xs font-semibold text-gray-700 uppercase mb-2">
                            NDVI Trend
                        </p>
                        {land.ndvi_series && land.ndvi_series.length > 0 ? (
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={land.ndvi_series}>
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(date: string) => {
                                            const d = new Date(date);
                                            return d.toLocaleDateString(
                                                "en-US",
                                                { month: "short" },
                                            );
                                        }}
                                    />
                                    <YAxis
                                        domain={[0, 1]}
                                        tick={{ fontSize: 10 }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "#fff",
                                            border: "1px solid #ccc",
                                            borderRadius: "4px",
                                            fontSize: "12px",
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="ndvi"
                                        stroke="#1abc9c"
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <p className="text-xs text-gray-500 text-center py-8">
                                No data
                            </p>
                        )}
                    </div>

                    {/* Anomaly Flags */}
                    <div>
                        <p className="text-xs font-semibold text-gray-700 uppercase mb-2">
                            Detected Anomalies
                        </p>
                        {land.flags && land.flags.length > 0 ? (
                            <div className="space-y-2">
                                {land.flags.map((flag, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-2 text-amber-700 text-xs"
                                    >
                                        <span className="material-symbols-outlined text-sm">
                                            {iconMap[flag]}
                                        </span>
                                        <span className="capitalize">
                                            {flag.replace("_", " ")}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-green-700 text-xs">
                                <span className="material-symbols-outlined text-sm">
                                    check_circle
                                </span>
                                <span>No anomalies detected</span>
                            </div>
                        )}
                    </div>

                    {/* Analyst Notes */}
                    <div>
                        <label
                            htmlFor="notes"
                            className="text-xs font-semibold text-gray-700 uppercase block mb-2"
                        >
                            Field Notes
                        </label>
                        <textarea
                            id="notes"
                            rows={4}
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="w-full border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 resize-none"
                            placeholder="Enter observations..."
                        />
                        <div className="flex justify-end mt-2">
                            <button className="text-xs text-teal-700 hover:text-teal-800 font-medium">
                                Save Note
                            </button>
                        </div>
                    </div>

                    {/* Evidence Links */}
                    <div className="border-t border-gray-200 pt-4 space-y-2">
                        <Link
                            href={`/lands/${id}/evidence`}
                            className="flex items-center gap-2 text-teal-700 hover:text-teal-800 text-xs font-medium"
                        >
                            <span className="material-symbols-outlined text-sm">
                                arrow_back
                            </span>
                            View Data Tables
                        </Link>
                        <Link
                            href={`/lands/${id}/summary`}
                            className="flex items-center gap-2 text-teal-700 hover:text-teal-800 text-xs font-medium"
                        >
                            <span className="material-symbols-outlined text-sm">
                                arrow_back
                            </span>
                            Back to Summary
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}

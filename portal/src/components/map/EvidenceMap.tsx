"use client";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Geometry } from "geojson";

const EGYPT_BOUNDS: [[number, number], [number, number]] = [
    [22.0, 24.5],
    [31.8, 36.9],
];

const TILES = {
    satellite:
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    labels: "https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
    osm: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
};

interface EvidenceMapProps {
    geometry?: Geometry | null;
    layerMode: "ndvi" | "evi" | "rgb";
}

export function EvidenceMap({ geometry, layerMode }: EvidenceMapProps) {
    const useSatellite = layerMode !== "rgb";
    const feature = geometry
        ? { type: "Feature" as const, geometry, properties: {} }
        : null;

    return (
        <div className="relative w-full h-full">
            <MapContainer
                center={[26.8206, 30.8025]}
                zoom={6}
                minZoom={6}
                maxBounds={EGYPT_BOUNDS}
                maxBoundsViscosity={1}
                className="w-full h-full"
                scrollWheelZoom
            >
                {useSatellite ? (
                    <>
                        <TileLayer
                            url={TILES.satellite}
                            attribution="Esri World Imagery"
                        />
                        <TileLayer
                            url={TILES.labels}
                            attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
                        />
                    </>
                ) : (
                    <TileLayer
                        url={TILES.osm}
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    />
                )}
                {feature && (
                    <GeoJSON
                        key={JSON.stringify(feature)}
                        data={feature}
                        style={{
                            color: "#1abc9c",
                            weight: 2,
                            fillColor: "#1abc9c",
                            fillOpacity: 0.15,
                        }}
                    />
                )}
            </MapContainer>

            {/* NDVI legend */}
            <div className="absolute bottom-4 left-4 z-[1000] bg-white rounded-md shadow-lg p-3 pointer-events-none">
                <p className="text-xs font-semibold text-gray-700 mb-2">NDVI</p>
                <div className="flex items-center gap-2 text-xs text-gray-600">
                    <div
                        className="w-20 h-3 rounded-sm"
                        style={{
                            background:
                                "linear-gradient(90deg, #d73027 0%, #fee08b 50%, #1a9850 100%)",
                        }}
                    />
                    <span>-1 → 1</span>
                </div>
            </div>
        </div>
    );
}

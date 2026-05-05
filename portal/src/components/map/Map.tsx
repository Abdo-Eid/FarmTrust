"use client";
import { useState, useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import type { Geometry } from "geojson";

// Fix broken default marker icons in webpack/Next.js builds
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)
    ._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const EGYPT_BOUNDS: L.LatLngBoundsExpression = [
    [21.9, 24.7],
    [31.7, 37.0],
];

const TILES = {
    satellite:
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    labels: "https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
    osm: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
};

type LayerMode = "satellite" | "rgb";

interface MapProps {
    center?: [number, number];
    zoom?: number;
    geometry?: Geometry | null;
    geojson?: GeoJSON.FeatureCollection | null;
    showLayerControls?: boolean;
    defaultLayerMode?: LayerMode;
    onMapReady?: (map: L.Map) => void;
}

function MapReadyHandler({
    onMapReady,
}: {
    onMapReady?: (map: L.Map) => void;
}) {
    const map = useMap();
    useEffect(() => {
        onMapReady?.(map);
    }, [map, onMapReady]);
    return null;
}

export function Map({
    center = [26.8206, 30.8025],
    zoom = 6,
    geometry,
    geojson,
    showLayerControls = false,
    defaultLayerMode = "satellite",
    onMapReady,
}: MapProps) {
    const [layerMode, setLayerMode] = useState<LayerMode>(defaultLayerMode);

    // Use geometry or first feature of geojson
    const geoData = geometry
        ? { type: "Feature" as const, geometry, properties: {} }
        : geojson?.features[0];

    const useSatellite = layerMode !== "rgb";

    return (
        <div className="relative w-full h-full">
            <MapContainer
                center={center}
                zoom={zoom}
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

                {geoData && (
                    <GeoJSON
                        key={JSON.stringify(geoData)}
                        data={geoData}
                        style={{
                            color: "#ff6b35",
                            weight: 3,
                            fillColor: "#ff6b35",
                            fillOpacity: 0.25,
                            dashArray: "5, 5",
                        }}
                    />
                )}

                <MapReadyHandler onMapReady={onMapReady} />
            </MapContainer>

            {/* Layer Controls - only show if enabled */}
            {showLayerControls && (
                <div className="absolute top-4 right-4 z-[1000] bg-white rounded-md shadow-lg p-3">
                    <div className="flex gap-2">
                        {(["satellite", "rgb"] as const).map((mode) => (
                            <button
                                key={mode}
                                onClick={() => setLayerMode(mode)}
                                className={`py-2 px-3 rounded-md text-xs font-medium transition ${
                                    layerMode === mode
                                        ? "bg-teal-600 text-white"
                                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                }`}
                            >
                                {mode.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* NDVI Legend - show when NDVI layer is active */}
            {showLayerControls &&
                layerMode !== "rgb" &&
                layerMode !== "satellite" && (
                    <div className="absolute bottom-4 left-4 z-[1000] bg-white rounded-md shadow-lg p-3 pointer-events-none">
                        <p className="text-xs font-semibold text-gray-700 mb-2">
                            NDVI
                        </p>
                        <div className="flex items-center gap-200">
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
                )}
        </div>
    );
}

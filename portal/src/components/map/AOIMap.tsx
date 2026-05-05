"use client";
import { useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

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
    [22.0, 24.5],
    [31.8, 36.9],
];

interface AOIMapProps {
    center?: [number, number];
    geojson?: GeoJSON.FeatureCollection | null;
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

export function AOIMap({
    center = [26.8, 30.8],
    geojson,
    onMapReady,
}: AOIMapProps) {
    return (
        <MapContainer
            center={center}
            zoom={6}
            minZoom={6}
            maxBounds={EGYPT_BOUNDS}
            maxBoundsViscosity={1}
            className="w-full h-full"
            scrollWheelZoom
        >
            <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Esri World Imagery"
            />
            <TileLayer
                url="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
            />
            {geojson && (
                <GeoJSON
                    key={JSON.stringify(geojson)}
                    data={geojson}
                    style={{
                        color: "#16a085",
                        weight: 2,
                        fillColor: "#1abc9c",
                        fillOpacity: 0.15,
                    }}
                />
            )}
            <MapReadyHandler onMapReady={onMapReady} />
        </MapContainer>
    );
}

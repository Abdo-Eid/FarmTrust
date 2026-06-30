"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import type { Feature, GeoJSON as GeoJSONData, Geometry } from "geojson";

// Fix broken default marker icons in webpack/Next.js builds
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)
    ._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
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

export interface MapProps {
    center?: [number, number];
    zoom?: number;
    geometry?: Geometry | null;
    geojson?: GeoJSONData | null;
    fitBoundsOnData?: boolean;
    showLayerControls?: boolean;
    defaultLayerMode?: LayerMode;
    onMapReady?: (map: L.Map) => void;
    /** "draw" enables polygon drawing by clicking corners */
    mode?: "display" | "draw";
    /** Increment this to reset the drawn polygon */
    drawKey?: number;
    /** Called whenever drawn polygon changes; null when incomplete or cleared */
    onPolygonChange?: (polygon: GeoJSON.Polygon | null) => void;
}

// ─── Vertex icon ────────────────────────────────────────────────────────────

function makeVertexIcon(isFirst: boolean): L.DivIcon {
    const size = isFirst ? 14 : 10;
    const color = isFirst ? "#ff6b35" : "#16a085";
    return L.divIcon({
        className: "",
        html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.45);cursor:move;box-sizing:border-box;"></div>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
    });
}

// ─── DrawLayer ───────────────────────────────────────────────────────────────

interface DrawLayerProps {
    drawKey: number;
    onPolygonChange: (polygon: GeoJSON.Polygon | null) => void;
}

function DrawLayer({ drawKey, onPolygonChange }: DrawLayerProps) {
    const map = useMap();
    const cbRef = useRef(onPolygonChange);
    cbRef.current = onPolygonChange;

    // All mutable draw state lives in a single ref to avoid stale-closure issues
    const st = useRef<{
        vertices: L.LatLng[];
        markers: L.Marker[];
        polyline: L.Polyline | null;
        polygon: L.Polygon | null;
        closed: boolean;
    }>({
        vertices: [],
        markers: [],
        polyline: null,
        polygon: null,
        closed: false,
    });

    const clearAll = useCallback(() => {
        const s = st.current;
        s.markers.forEach((m) => map.removeLayer(m));
        if (s.polyline) map.removeLayer(s.polyline);
        if (s.polygon) map.removeLayer(s.polygon);
        s.vertices = [];
        s.markers = [];
        s.polyline = null;
        s.polygon = null;
        s.closed = false;
    }, [map]);

    // Reset whenever drawKey changes
    useEffect(() => {
        clearAll();
    }, [drawKey, clearAll]);

    // Cleanup on unmount
    useEffect(() => () => clearAll(), [clearAll]);

    // Crosshair cursor while in draw mode
    useEffect(() => {
        const c = map.getContainer();
        c.style.cursor = "crosshair";
        return () => {
            c.style.cursor = "";
        };
    }, [map]);

    // Redraw all Leaflet layers from current vertex state
    const redraw = useCallback(() => {
        const s = st.current;
        if (s.polyline) {
            map.removeLayer(s.polyline);
            s.polyline = null;
        }
        if (s.polygon) {
            map.removeLayer(s.polygon);
            s.polygon = null;
        }

        if (s.vertices.length < 1) {
            cbRef.current(null);
            return;
        }

        if (s.closed && s.vertices.length >= 3) {
            s.polygon = L.polygon(s.vertices, {
                color: "#16a085",
                weight: 2,
                fillColor: "#1abc9c",
                fillOpacity: 0.2,
            }).addTo(map);
            const ring = s.vertices.map(
                (v) => [v.lng, v.lat] as [number, number],
            );
            ring.push(ring[0]); // close GeoJSON ring
            cbRef.current({ type: "Polygon", coordinates: [ring] });
        } else if (s.vertices.length >= 2) {
            s.polyline = L.polyline(s.vertices, {
                color: "#16a085",
                weight: 2,
                dashArray: "6,4",
            }).addTo(map);
            cbRef.current(null);
        } else {
            cbRef.current(null);
        }
    }, [map]);

    const addMarker = useCallback(
        (latlng: L.LatLng, idx: number) => {
            const m = L.marker(latlng, {
                icon: makeVertexIcon(idx === 0),
                draggable: true,
                zIndexOffset: idx === 0 ? 100 : 0,
            }).addTo(map);
            m.on("drag", () => {
                st.current.vertices[idx] = m.getLatLng();
                redraw();
            });
            m.on("dragend", () => {
                st.current.vertices[idx] = m.getLatLng();
                redraw();
            });
            return m;
        },
        [map, redraw],
    );

    useMapEvents({
        click(e) {
            const s = st.current;
            if (s.closed) return;

            const { latlng } = e;

            // Close polygon when clicking within 15px of the first vertex
            if (s.vertices.length >= 3) {
                const fp = map.latLngToContainerPoint(s.vertices[0]);
                const cp = map.latLngToContainerPoint(latlng);
                if (fp.distanceTo(cp) < 15) {
                    s.closed = true;
                    redraw();
                    return;
                }
            }

            const idx = s.vertices.length;
            s.vertices.push(latlng);
            s.markers.push(addMarker(latlng, idx));
            redraw();
        },
    });

    return null;
}

// ─── MapReadyHandler ─────────────────────────────────────────────────────────

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

function FitGeoJSONBounds({ data }: { data: GeoJSONData }) {
    const map = useMap();

    useEffect(() => {
        const layer = L.geoJSON(data);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [24, 24], maxZoom: 17 });
        }
    }, [data, map]);

    return null;
}

// ─── Map ─────────────────────────────────────────────────────────────────────

export function Map({
    center = [26.8206, 30.8025],
    zoom = 6,
    geometry,
    geojson,
    fitBoundsOnData = false,
    showLayerControls = false,
    defaultLayerMode = "satellite",
    onMapReady,
    mode = "display",
    drawKey = 0,
    onPolygonChange,
}: MapProps) {
    const [layerMode, setLayerMode] = useState<LayerMode>(defaultLayerMode);
    const [drawPolygon, setDrawPolygon] = useState<GeoJSON.Polygon | null>(
        null,
    );

    // Keep internal draw polygon state in sync with drawKey resets
    useEffect(() => {
        setDrawPolygon(null);
    }, [drawKey]);

    const handlePolygonChange = useCallback(
        (p: GeoJSON.Polygon | null) => {
            setDrawPolygon(p);
            onPolygonChange?.(p);
        },
        [onPolygonChange],
    );

    // Display-mode data
    const geoData: GeoJSONData | null = geojson
        ? geojson
        : geometry
          ? ({ type: "Feature", geometry, properties: {} } satisfies Feature<Geometry>)
          : null;

    const useSatellite = layerMode !== "rgb";

    const drawHint = drawPolygon
        ? "Polygon complete — drag corners to adjust"
        : "Click to place corners · click near the first corner ◉ to close";

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

                {/* Render existing or uploaded geometry */}
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

                {fitBoundsOnData && geoData && <FitGeoJSONBounds data={geoData} />}

                {/* Draw mode */}
                {mode === "draw" && (
                    <DrawLayer
                        drawKey={drawKey}
                        onPolygonChange={handlePolygonChange}
                    />
                )}

                <MapReadyHandler onMapReady={onMapReady} />
            </MapContainer>

            {/* Layer controls */}
            {showLayerControls && (
                <div className="absolute top-4 right-4 z-[1000] bg-white rounded-md shadow-lg p-3">
                    <div className="flex gap-2">
                        {(["satellite", "rgb"] as const).map((m) => (
                            <button
                                key={m}
                                onClick={() => setLayerMode(m)}
                                className={`py-2 px-3 rounded-md text-xs font-medium transition ${
                                    layerMode === m
                                        ? "bg-teal-600 text-white"
                                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                }`}
                            >
                                {m.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* NDVI Legend — only in display mode when a non-standard layer would show it */}
            {showLayerControls &&
                layerMode !== "rgb" &&
                layerMode !== "satellite" && (
                    <div className="absolute bottom-4 left-4 z-[1000] bg-white rounded-md shadow-lg p-3 pointer-events-none">
                        <p className="text-xs font-semibold text-gray-700 mb-2">
                            NDVI
                        </p>
                        <div className="flex items-center gap-2">
                            <div
                                className="w-20 h-3 rounded-sm"
                                style={{
                                    background:
                                        "linear-gradient(90deg, #d73027 0%, #fee08b 50%, #1a9850 100%)",
                                }}
                            />
                            <span className="text-xs text-gray-500">
                                -1 → 1
                            </span>
                        </div>
                    </div>
                )}

            {/* Draw mode hint bar */}
            {mode === "draw" && (
                <div className="absolute bottom-4 left-4 z-[1000] bg-white/90 backdrop-blur-sm rounded-md shadow-panel px-3 py-2 text-xs text-gray-700 flex items-center gap-2 pointer-events-none max-w-xs">
                    <span
                        className={`material-symbols-outlined text-sm flex-shrink-0 ${drawPolygon ? "text-teal-600" : "text-gray-400"}`}
                    >
                        {drawPolygon ? "check_circle" : "draw"}
                    </span>
                    {drawHint}
                </div>
            )}
        </div>
    );
}

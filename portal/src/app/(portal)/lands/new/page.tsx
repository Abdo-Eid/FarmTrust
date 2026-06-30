"use client";
import { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select, Textarea } from "@/components/ui/FormField";
import { GOVERNORATES } from "@/lib/constants";
import { api } from "@/lib/api";
import {
    calcGeoJSONAreaFeddan,
    countGeoJSONAOIs,
    formatFeddan,
    normalizeLandGeoJSON,
} from "@/lib/geo";
import type { LandGeoJSON } from "@/lib/geo";

const GeoMap = dynamic(
    () => import("@/components/map/Map").then((m) => m.Map),
    {
        ssr: false,
        loading: () => (
            <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                <div className="text-center text-gray-400">
                    <span className="material-symbols-outlined text-4xl">
                        map
                    </span>
                    <p className="text-sm mt-2">Loading map...</p>
                </div>
            </div>
        ),
    },
);

const LOOKBACK_OPTIONS = [
    { label: "6 months", days: 180 },
    { label: "1 year", days: 365 },
    { label: "2 years (recommended)", days: 730 },
    { label: "3 years", days: 1095 },
] as const;

const MIN_AREA_FEDDAN = 1 / 24;
const MAX_AREA_FEDDAN = 200;

interface FormData {
    name: string;
    governorate: string;
    district?: string;
    notes?: string;
    lookback_days: number;
}

export default function AddLandPage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
    const [drawKey, setDrawKey] = useState(0);
    const [uploadInputKey, setUploadInputKey] = useState(0);
    const [landGeometry, setLandGeometry] = useState<LandGeoJSON | null>(null);
    const [boundarySource, setBoundarySource] = useState<"draw" | "upload" | null>(null);
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
    const [formData, setFormData] = useState<Partial<FormData>>({ lookback_days: 730 });
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);

    const calculatedArea = useMemo(() => {
        if (!landGeometry) return null;
        return calcGeoJSONAreaFeddan(landGeometry);
    }, [landGeometry]);

    const aoiCount = useMemo(() => {
        if (!landGeometry) return 0;
        return countGeoJSONAOIs(landGeometry);
    }, [landGeometry]);

    const isSingleAoi = aoiCount === 1;

    const areaError =
        isSingleAoi &&
        calculatedArea !== null &&
        (calculatedArea < MIN_AREA_FEDDAN || calculatedArea > MAX_AREA_FEDDAN)
            ? calculatedArea < MIN_AREA_FEDDAN
                ? "Minimum 1/24 feddan"
                : "Maximum 200 feddan"
            : null;

    const positiveAreaError =
        calculatedArea !== null && calculatedArea <= 0
            ? "Area must be greater than 0"
            : null;

    const canSubmit =
        !!landGeometry &&
        calculatedArea !== null &&
        calculatedArea > 0 &&
        !areaError &&
        !!formData.name?.trim() &&
        !!formData.governorate;

    const handlePolygonChange = useCallback((p: GeoJSON.Polygon | null) => {
        setLandGeometry(p);
        setBoundarySource(p ? "draw" : null);
        setUploadedFileName(null);
        setUploadError(null);
    }, []);

    const handleGeoJSONUpload = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (!file) return;

            setUploadError(null);
            setSubmitError(null);

            try {
                const parsed = JSON.parse(await file.text()) as unknown;
                const geojson = normalizeLandGeoJSON(parsed);
                setLandGeometry(geojson);
                setBoundarySource("upload");
                setUploadedFileName(file.name);
                setDrawKey((k) => k + 1);
            } catch (error) {
                setLandGeometry(null);
                setBoundarySource(null);
                setUploadedFileName(null);
                setDrawKey((k) => k + 1);
                setUploadError(
                    error instanceof Error
                        ? error.message
                        : "Could not read this GeoJSON file.",
                );
            }
        },
        [],
    );

    const handleClear = useCallback(() => {
        setLandGeometry(null);
        setBoundarySource(null);
        setUploadedFileName(null);
        setUploadError(null);
        setSubmitError(null);
        setUploadInputKey((k) => k + 1);
        setDrawKey((k) => k + 1);
    }, []);

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;
        setSubmitting(true);
        setSubmitError(null);
        try {
            const district = formData.district?.trim();
            const notes = formData.notes?.trim();
            const land = await api.lands.create({
                name: formData.name!.trim(),
                governorate: formData.governorate!,
                ...(district ? { district } : {}),
                ...(notes ? { notes } : {}),
                method: "polygon",
                geometry: landGeometry!,
                area_feddan: calculatedArea!,
                lookback_days: formData.lookback_days ?? 730,
            });
            router.push(`/lands/${land.id}`);
        } catch {
            setSubmitError("Submission failed. Please try again.");
            setSubmitting(false);
        }
    };

    // AOI status strip appearance
    const aoiStatus = landGeometry
        ? areaError || positiveAreaError
            ? {
                  bg: "bg-red-50 border-red-100",
                  text: "text-red-700",
                  icon: "error",
                  label: `${formatFeddan(calculatedArea!)} — ${areaError || positiveAreaError}`,
              }
            : {
                  bg: "bg-teal-50 border-teal-100",
                  text: "text-teal-700",
                  icon: "check_circle",
                  label:
                      aoiCount > 1
                          ? `${formatFeddan(calculatedArea!)} across ${aoiCount} AOIs uploaded`
                          : `${formatFeddan(calculatedArea!)} ${boundarySource === "upload" ? "uploaded" : "drawn"}`,
              }
        : {
              bg: "bg-gray-50 border-gray-100",
              text: "text-gray-500",
              icon: "draw",
              label: "No boundary selected — draw on the map or upload GeoJSON",
          };

    return (
        <div className="min-h-full bg-sand flex flex-col">
            <TopBar
                breadcrumbs={[
                    { label: "Lands", href: "/lands" },
                    { label: "Add Land" },
                ]}
                actions={
                    <Button
                        variant="ghost"
                        size="sm"
                        icon="arrow_back"
                        onClick={() => router.push("/lands")}
                    >
                        Cancel
                    </Button>
                }
            />

            {/* Two-column layout: map top/right, form bottom/left */}
            <div className="flex flex-col md:flex-row md:flex-1 md:h-[calc(100vh-49px)] md:overflow-hidden">
                {/* Map — top on mobile, right on desktop */}
                <div className="order-1 md:order-2 h-64 md:h-auto md:flex-1 relative bg-gray-100 flex-shrink-0">
                    <div className="absolute inset-0">
                        <GeoMap
                            mode="draw"
                            drawKey={drawKey}
                            geojson={boundarySource === "upload" ? landGeometry : null}
                            fitBoundsOnData={boundarySource === "upload"}
                            onPolygonChange={handlePolygonChange}
                            showLayerControls
                            defaultLayerMode="satellite"
                        />
                    </div>
                    {/* Clear button */}
                    <button
                        type="button"
                        onClick={handleClear}
                        className="absolute top-3 left-3 z-[1000] bg-white border border-gray-200 rounded-md px-3 py-1.5 shadow-panel text-xs text-gray-600 flex items-center gap-1.5 hover:bg-gray-50 transition-colors"
                    >
                        <span className="material-symbols-outlined text-sm text-gray-400">
                            restart_alt
                        </span>
                        Clear
                    </button>
                </div>

                {/* Form — bottom on mobile, left on desktop */}
                <div className="order-2 md:order-1 w-full md:w-[440px] flex-shrink-0 bg-white border-t md:border-t-0 md:border-r border-gray-200 flex flex-col md:overflow-y-auto">
                    {/* Header */}
                    <div className="px-6 py-5 border-b border-gray-100">
                        <h2 className="text-base font-semibold text-gray-900">
                            New Land Submission
                        </h2>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Draw the land boundary or upload GeoJSON, then fill
                            in the details below.
                        </p>
                    </div>

                    {/* AOI status strip */}
                    <div
                        className={`px-6 py-3 border-b text-xs flex items-center gap-2 ${aoiStatus.bg} ${aoiStatus.text}`}
                    >
                        <span className="material-symbols-outlined text-sm flex-shrink-0">
                            {aoiStatus.icon}
                        </span>
                        {aoiStatus.label}
                    </div>

                    {/* Form fields */}
                    <form
                        onSubmit={onSubmit}
                        className="flex-1 px-6 py-5 space-y-5"
                    >
                        <FormField
                            label="Boundary GeoJSON"
                            hint={
                                uploadedFileName
                                    ? `Loaded ${uploadedFileName}`
                                    : "Optional: upload .geojson or .json with Polygon, MultiPolygon, Feature, or FeatureCollection."
                            }
                            error={uploadError || undefined}
                        >
                            <Input
                                key={uploadInputKey}
                                type="file"
                                accept=".geojson,.json,application/geo+json,application/json"
                                onChange={handleGeoJSONUpload}
                                error={!!uploadError}
                            />
                        </FormField>

                        {landGeometry && calculatedArea !== null && (
                            <div className="rounded-md border border-teal-100 bg-teal-50 px-4 py-3 text-xs text-teal-800">
                                <div className="flex items-center gap-2 font-semibold">
                                    <span className="material-symbols-outlined text-sm">
                                        inventory_2
                                    </span>
                                    Submission review
                                </div>
                                <div className="mt-2 grid grid-cols-2 gap-2">
                                    <div>
                                        <p className="text-teal-600">AOIs</p>
                                        <p className="font-semibold text-teal-900">
                                            {aoiCount} land{aoiCount === 1 ? "" : "s"}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-teal-600">Total area</p>
                                        <p className="font-semibold text-teal-900">
                                            {formatFeddan(calculatedArea)}
                                        </p>
                                    </div>
                                </div>
                                {aoiCount > 1 && (
                                    <p className="mt-2 leading-relaxed text-teal-700">
                                        This will appear as one parent submission in the lands list. FarmTrust will download one shared satellite cube for the combined bbox, then analyze each AOI separately.
                                    </p>
                                )}
                            </div>
                        )}

                        <FormField label="Land Name" required>
                            <Input
                                placeholder="e.g. North Sharqia Plot A"
                                value={formData.name || ""}
                                onChange={(e) =>
                                    setFormData({
                                        ...formData,
                                        name: e.target.value,
                                    })
                                }
                            />
                        </FormField>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField label="Governorate" required>
                                <Select
                                    value={formData.governorate || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            governorate: e.target.value,
                                        })
                                    }
                                >
                                    <option value="">Select...</option>
                                    {GOVERNORATES.map((g) => (
                                        <option key={g} value={g}>
                                            {g}
                                        </option>
                                    ))}
                                </Select>
                            </FormField>

                            <FormField label="District">
                                <Input
                                    placeholder="Optional"
                                    value={formData.district || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            district: e.target.value,
                                        })
                                    }
                                />
                            </FormField>
                        </div>

                        <FormField label="Notes">
                            <Textarea
                                placeholder="Any additional context for the analyst..."
                                rows={3}
                                value={formData.notes || ""}
                                onChange={(e) =>
                                    setFormData({
                                        ...formData,
                                        notes: e.target.value,
                                    })
                                }
                            />
                        </FormField>

                        <FormField
                            label="Satellite Lookback Period"
                            hint="How far back to search for Sentinel-2 imagery"
                        >
                            <Select
                                value={String(formData.lookback_days ?? 730)}
                                onChange={(e) =>
                                    setFormData({
                                        ...formData,
                                        lookback_days: Number(e.target.value),
                                    })
                                }
                            >
                                {LOOKBACK_OPTIONS.map((opt) => (
                                    <option key={opt.days} value={opt.days}>
                                        {opt.label}
                                    </option>
                                ))}
                            </Select>
                        </FormField>

                        {submitError && (
                            <p className="text-xs text-red-600 flex items-center gap-1.5">
                                <span className="material-symbols-outlined text-sm">
                                    error
                                </span>
                                {submitError}
                            </p>
                        )}

                        <div className="pt-2 border-t border-gray-100">
                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                loading={submitting}
                                icon="send"
                                className="w-full"
                                disabled={!canSubmit}
                            >
                                Submit for Analysis
                            </Button>
                            <p className="text-xs text-gray-400 text-center mt-2">
                                {!landGeometry
                                    ? "Draw or upload the land boundary to continue."
                                    : areaError || positiveAreaError
                                      ? areaError || positiveAreaError
                                      : "Analysis typically completes in 5–15 minutes."}
                            </p>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

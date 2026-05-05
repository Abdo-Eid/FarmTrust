"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import dynamic from "next/dynamic";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select, Textarea } from "@/components/ui/FormField";
import { GOVERNORATES } from "@/lib/constants";
import { api } from "@/lib/api";

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

const schema = z.object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    governorate: z.string().min(1, "Select a governorate"),
    district: z.string().optional(),
    method: z.enum(["point_area", "geojson"]),
    area_feddan: z.coerce
        .number()
        .min(1, "Minimum 1 feddan")
        .max(200, "Maximum 200 feddan"),
    notes: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function AddLandPage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
    const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(
        null,
    );
    const [fileError, setFileError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<FormData>({
        resolver: zodResolver(schema),
        defaultValues: { method: "point_area", area_feddan: 10 },
    });

    const method = watch("method");

    const handleFileUpload = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setFileError(null);

            const reader = new FileReader();
            reader.onload = (ev) => {
                try {
                    const parsed = JSON.parse(ev.target?.result as string);
                    if (parsed.type !== "FeatureCollection") {
                        setFileError(
                            "File must be a GeoJSON FeatureCollection",
                        );
                        return;
                    }
                    setGeojson(parsed);
                } catch {
                    setFileError("Invalid JSON file");
                }
            };
            reader.readAsText(file);
        },
        [],
    );

    const onSubmit = async (data: FormData) => {
        setSubmitting(true);
        try {
            const land = await api.lands.create({
                name: data.name,
                governorate: data.governorate,
                district: data.district,
                area_feddan: data.area_feddan,
                method: data.method,
                geometry: geojson?.features[0]?.geometry ?? null,
                notes: data.notes,
            });
            router.push(`/lands/${land.id}`);
        } catch {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-full bg-sand">
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

            <div className="flex h-[calc(100vh-49px)]">
                {/* Left: Form */}
                <div className="w-1/2 flex flex-col border-r border-gray-200 bg-white overflow-y-auto">
                    <div className="px-6 py-5 border-b border-gray-100">
                        <h2 className="text-base font-semibold text-gray-900">
                            New Land Submission
                        </h2>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Submit an Area of Interest (AOI) for satellite land
                            assessment. Area must be 1–200 feddan.
                        </p>
                    </div>

                    <form
                        onSubmit={handleSubmit(onSubmit)}
                        className="flex-1 px-6 py-5 space-y-5"
                    >
                        <FormField
                            label="Land Name"
                            error={errors.name?.message}
                            required
                        >
                            <Input
                                placeholder="e.g. North Sharqia Plot A"
                                {...register("name")}
                                error={!!errors.name}
                            />
                        </FormField>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                label="Governorate"
                                error={errors.governorate?.message}
                                required
                            >
                                <Select
                                    {...register("governorate")}
                                    error={!!errors.governorate}
                                >
                                    <option value="">Select...</option>
                                    {GOVERNORATES.map((g) => (
                                        <option key={g} value={g}>
                                            {g}
                                        </option>
                                    ))}
                                </Select>
                            </FormField>

                            <FormField
                                label="District"
                                error={errors.district?.message}
                            >
                                <Input
                                    placeholder="Optional"
                                    {...register("district")}
                                />
                            </FormField>
                        </div>

                        <FormField label="AOI Method" required>
                            <div className="flex gap-3">
                                {(["point_area", "geojson"] as const).map(
                                    (m) => (
                                        <label
                                            key={m}
                                            className="flex items-center gap-2 cursor-pointer"
                                        >
                                            <input
                                                type="radio"
                                                value={m}
                                                {...register("method")}
                                                className="accent-teal-700"
                                            />
                                            <span className="text-sm text-gray-700">
                                                {m === "point_area"
                                                    ? "Point + Area"
                                                    : "Upload GeoJSON"}
                                            </span>
                                        </label>
                                    ),
                                )}
                            </div>
                        </FormField>

                        {method === "point_area" && (
                            <FormField
                                label="Area (Feddan)"
                                error={errors.area_feddan?.message}
                                hint="1 feddan = 4,200 m². Valid range: 1–200 feddan."
                                required
                            >
                                <Input
                                    type="number"
                                    min={1}
                                    max={200}
                                    step={0.5}
                                    placeholder="e.g. 45"
                                    {...register("area_feddan")}
                                    error={!!errors.area_feddan}
                                />
                            </FormField>
                        )}

                        {method === "geojson" && (
                            <FormField
                                label="GeoJSON File"
                                hint="Upload a FeatureCollection with a single Polygon or MultiPolygon."
                            >
                                <div className="border-2 border-dashed border-gray-200 rounded-md p-4 text-center hover:border-teal-400 transition-colors">
                                    <input
                                        type="file"
                                        accept=".json,.geojson"
                                        onChange={handleFileUpload}
                                        className="hidden"
                                        id="geojson-upload"
                                    />
                                    <label
                                        htmlFor="geojson-upload"
                                        className="cursor-pointer"
                                    >
                                        <span className="material-symbols-outlined text-gray-300 text-3xl block mb-1">
                                            upload_file
                                        </span>
                                        <span className="text-sm text-teal-700 font-medium">
                                            Click to upload
                                        </span>
                                        <span className="text-xs text-gray-400 block">
                                            .json or .geojson
                                        </span>
                                    </label>
                                    {geojson && (
                                        <p className="text-xs text-green-600 mt-2 flex items-center justify-center gap-1">
                                            <span className="material-symbols-outlined text-sm">
                                                check_circle
                                            </span>
                                            GeoJSON loaded (
                                            {geojson.features.length} feature
                                            {geojson.features.length !== 1
                                                ? "s"
                                                : ""}
                                            )
                                        </p>
                                    )}
                                    {fileError && (
                                        <p className="text-xs text-red-600 mt-1">
                                            {fileError}
                                        </p>
                                    )}
                                </div>
                            </FormField>
                        )}

                        <FormField label="Notes">
                            <Textarea
                                placeholder="Any additional context for the analyst..."
                                rows={3}
                                {...register("notes")}
                            />
                        </FormField>

                        <div className="pt-2 border-t border-gray-100">
                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                loading={submitting}
                                icon="send"
                                className="w-full"
                            >
                                Submit for Analysis
                            </Button>
                            <p className="text-xs text-gray-400 text-center mt-2">
                                Analysis typically completes in 5–15 minutes.
                            </p>
                        </div>
                    </form>
                </div>

                {/* Right: Map */}
                <div className="w-1/2 relative bg-gray-100">
                    <div className="absolute inset-0">
                        <GeoMap geojson={geojson} showLayerControls={true} />
                    </div>
                    <div className="absolute top-3 left-3 bg-white border border-gray-200 rounded-md px-3 py-1.5 shadow-panel text-xs text-gray-600 flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-teal-600 text-sm">
                            location_on
                        </span>
                        Egypt — Restricted to registered AOIs
                    </div>
                </div>
            </div>
        </div>
    );
}

"""Fetch compact AOI soil features from public SoilGrids layers.

This script reads ``data/<aoi_id>/run_metadata.json``, queries SoilGrids at the
AOI centroid, aggregates representative topsoil/root-zone features, and writes
a compact one-row artifact next to the AOI.

The centroid-query approach is intentional here: the current AOIs are much
smaller than SoilGrids' native ~250 m resolution, so recreating a wide raster
summary schema would add complexity without adding much real information.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import shape

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.io.paths import aoi_dir


SOILGRIDS_QUERY_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOILGRIDS_RESOLUTION_M = 250


@dataclass(frozen=True)
class DepthSlice:
    label: str
    thickness_cm: float


TOPSOIL_SLICES = (
    DepthSlice("0-5cm", 5.0),
    DepthSlice("5-15cm", 10.0),
    DepthSlice("15-30cm", 15.0),
)

ROOTZONE_SLICES = (
    DepthSlice("0-5cm", 5.0),
    DepthSlice("5-15cm", 10.0),
    DepthSlice("15-30cm", 15.0),
    DepthSlice("30-60cm", 30.0),
    DepthSlice("60-100cm", 40.0),
)

TOPSOIL_PROPERTIES = ("sand", "clay", "soc", "phh2o", "cec", "nitrogen")
ROOTZONE_PROPERTIES = ("wv0033", "wv1500")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch compact AOI soil features from SoilGrids / ISRIC."
    )
    parser.add_argument("--aoi-id", default="aoi_demo_01", help="AOI identifier under data/")
    parser.add_argument(
        "--data-root",
        default="data",
        help="Root folder containing AOI directories (default: data)",
    )
    return parser.parse_args()


def weighted_nanmean(values: Iterable[float], weights: Iterable[float]) -> float:
    values_arr = np.asarray(list(values), dtype="float64")
    weights_arr = np.asarray(list(weights), dtype="float64")
    mask = np.isfinite(values_arr) & np.isfinite(weights_arr) & (weights_arr > 0)
    if not mask.any():
        return float("nan")
    return float(np.average(values_arr[mask], weights=weights_arr[mask]))


def load_run_metadata(aoi_path: Path) -> dict:
    meta_path = aoi_path / "run_metadata.json"
    with meta_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def aoi_centroid_and_area(meta: dict) -> tuple[float, float, float]:
    geom = shape(meta["geometry"])
    centroid = geom.centroid
    target_crs = meta.get("crs") or "EPSG:32636"
    transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    projected_coords = [transformer.transform(x, y) for x, y in geom.exterior.coords]
    area_m2 = shape({"type": "Polygon", "coordinates": [projected_coords]}).area
    return float(centroid.x), float(centroid.y), float(area_m2)


def fetch_soilgrids_payload(*, lon: float, lat: float) -> dict:
    params: list[tuple[str, str | float]] = [("lon", lon), ("lat", lat), ("value", "mean")]
    for property_name in (*TOPSOIL_PROPERTIES, *ROOTZONE_PROPERTIES):
        params.append(("property", property_name))
    for depth_slice in ROOTZONE_SLICES:
        params.append(("depth", depth_slice.label))

    response = requests.get(SOILGRIDS_QUERY_URL, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def extract_layer_values(payload: dict) -> dict[str, dict[str, float]]:
    layers = payload.get("properties", {}).get("layers", [])
    output: dict[str, dict[str, float]] = {}
    for layer in layers:
        property_name = layer["name"]
        divisor = float(layer.get("unit_measure", {}).get("d_factor") or 1.0)
        depth_map: dict[str, float] = {}
        for depth_info in layer.get("depths", []):
            label = depth_info["label"]
            raw_value = depth_info.get("values", {}).get("mean")
            if raw_value is None:
                depth_map[label] = float("nan")
            else:
                depth_map[label] = float(raw_value) / divisor
        output[property_name] = depth_map
    return output


def build_soil_features(meta: dict) -> dict[str, object]:
    query_lon, query_lat, area_m2 = aoi_centroid_and_area(meta)
    payload = fetch_soilgrids_payload(lon=query_lon, lat=query_lat)
    layers = extract_layer_values(payload)

    topsoil_feature_map = {
        "sand": "soil_sand_pct_0_30cm",
        "clay": "soil_clay_pct_0_30cm",
        "soc": "soil_soc_gkg_0_30cm",
        "phh2o": "soil_phh2o_0_30cm",
        "cec": "soil_cec_cmolkg_0_30cm",
        "nitrogen": "soil_nitrogen_gkg_0_30cm",
    }

    output: dict[str, object] = {
        "aoi_id": meta.get("aoi_id"),
        "soil_source": "SoilGrids ISRIC REST mean",
        "soil_source_url": "https://docs.isric.org/globaldata/soilgrids/",
        "soil_source_resolution_m": SOILGRIDS_RESOLUTION_M,
        "soil_query_method": "centroid_point_query",
        "soil_query_lon": query_lon,
        "soil_query_lat": query_lat,
        "soil_aoi_area_m2": area_m2,
        "soil_feature_units_json": json.dumps(
            {
                "soil_sand_pct_0_30cm": "%",
                "soil_clay_pct_0_30cm": "%",
                "soil_soc_gkg_0_30cm": "g/kg",
                "soil_phh2o_0_30cm": "pH",
                "soil_cec_cmolkg_0_30cm": "cmol(c)/kg",
                "soil_nitrogen_gkg_0_30cm": "g/kg",
                "soil_available_water_0_100cm": "%",
            },
            sort_keys=True,
        ),
    }

    for property_name, output_name in topsoil_feature_map.items():
        converted = [layers[property_name].get(depth_slice.label, float("nan")) for depth_slice in TOPSOIL_SLICES]
        weights = [depth_slice.thickness_cm for depth_slice in TOPSOIL_SLICES]
        output[output_name] = weighted_nanmean(converted, weights)

    fc_converted = [layers["wv0033"].get(depth_slice.label, float("nan")) for depth_slice in ROOTZONE_SLICES]
    wp_converted = [layers["wv1500"].get(depth_slice.label, float("nan")) for depth_slice in ROOTZONE_SLICES]
    available_water_by_depth = [fc - wp for fc, wp in zip(fc_converted, wp_converted, strict=True)]
    rootzone_weights = [depth_slice.thickness_cm for depth_slice in ROOTZONE_SLICES]
    output["soil_available_water_0_100cm"] = weighted_nanmean(available_water_by_depth, rootzone_weights)

    output["soil_estimated_source_cells"] = max(1, int(np.ceil(area_m2 / float(SOILGRIDS_RESOLUTION_M**2))))
    output["soil_low_resolution_warning"] = bool(area_m2 <= float(SOILGRIDS_RESOLUTION_M**2))

    return output


def write_outputs(aoi_path: Path, features: dict[str, object]) -> tuple[Path, Path]:
    json_path = aoi_path / "soil_features.json"
    parquet_path = aoi_path / "soil_features.parquet"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(features, fh, indent=2)

    pd.DataFrame([features]).to_parquet(parquet_path, index=False)
    return json_path, parquet_path


def main() -> int:
    args = parse_args()
    root = Path(args.data_root)
    aoi_path = aoi_dir(args.aoi_id, root=root)
    if not aoi_path.exists():
        raise FileNotFoundError(f"AOI directory does not exist: {aoi_path}")

    meta = load_run_metadata(aoi_path)
    features = build_soil_features(meta)
    json_path, parquet_path = write_outputs(aoi_path, features)

    print(f"Saved compact soil features to {json_path}")
    print(f"Saved compact soil features to {parquet_path}")
    print(pd.DataFrame([features]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

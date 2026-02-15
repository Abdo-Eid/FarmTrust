import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from pyproj import Transformer
import pystac_client
import planetary_computer as pc
from datetime import date
from dateutil.relativedelta import relativedelta

# --------- CONFIGURATION ---------
CONFIG = {
    "sentinel": {
        "collection": "sentinel-2-l2a",
        "bands": {"red": "B04", "nir": "B08", "qa": "SCL"},
        "res": 10.0,
        "name": "Sentinel-2 (10m)"
    },
    "landsat": {
        "collection": "landsat-c2-l2",
        "bands": {"red": "red", "nir": "nir08", "qa": "qa_pixel"},
        "res": 30.0,
        "name": "Landsat 8 (30m)"
    }
}

BBOX = [30.9903, 30.594356, 31.013848, 30.616635]
AOI_ID = "aoi_farmtrust_demo_01"

# --------- UTILITIES ---------

def get_aoi_stats(bbox):
    """Calculates physical dimensions of the BBOX in meters."""
    lon_dist = bbox[2] - bbox[0]
    lat_dist = bbox[3] - bbox[1]
    center_lat = (bbox[1] + bbox[3]) / 2
    
    # 1 deg lat approx 111.32km; 1 deg lon varies by latitude
    width_m = lon_dist * 111320 * np.cos(np.radians(center_lat))
    height_m = lat_dist * 111320
    return width_m, height_m

def bbox_to_scene_crs(bbox_lonlat, dst_crs):
    """Transforms WGS84 bbox to the projection of the satellite image."""
    transformer = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True)
    minx, miny = transformer.transform(bbox_lonlat[0], bbox_lonlat[1])
    maxx, maxy = transformer.transform(bbox_lonlat[2], bbox_lonlat[3])
    return [min(minx, maxx), min(miny, maxy), max(minx, maxx), max(miny, maxy)]

def run_diagnostic(asset_href, band_label, bbox, expected_res):
    """Deep-dives into a specific band asset."""
    print(f"\n--- DIAGNOSING: {band_label} ---")
    
    with rasterio.open(asset_href) as src:
        # 1. Transform Bbox
        bbox_scene = bbox_to_scene_crs(bbox, src.crs)
        
        # 2. Define Window
        window = from_bounds(*bbox_scene, transform=src.transform)
        window = window.round_offsets().round_lengths()
        
        # Clamp to avoid reading outside image bounds
        img_win = rasterio.windows.Window(0, 0, src.width, src.height)
        window = window.intersection(img_win)
        
        # 3. Read
        arr = src.read(1, window=window, resampling=Resampling.bilinear)
        
        # 4. Reporting
        actual_res_x = abs(src.transform[0])
        actual_res_y = abs(src.transform[4])
        
        print(f"  Native CRS:  {src.crs}")
        print(f"  Native Res: {actual_res_x:.1f}m x {actual_res_y:.1f}m")
        print(f"  Array Shape: {arr.shape[1]} (W) x {arr.shape[0]} (H)")
        
        # Validate Resolution
        if not np.isclose(actual_res_x, expected_res, atol=1.0):
            print(f"  ⚠️ ALERT: Resolution ({actual_res_x}m) differs from target ({expected_res}m)")
        else:
            print(f"  ✅ Resolution is correct.")

        # Data Range Check
        print(f"  Value Range: {np.nanmin(arr)} to {np.nanmax(arr)}")
        return arr

# --------- MAIN EXECUTION ---------

print("="*60)
print(f"DUAL-SENSOR DIAGNOSTIC: {AOI_ID}")
print("="*60)

w_m, h_m = get_aoi_stats(BBOX)
print(f"AOI Physical Size: {w_m:.0f}m Wide x {h_m:.0f}m High (Area: {(w_m*h_m)/1e6:.2f} km²)")

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=pc.sign_inplace
)

# Test both Sentinel and Landsat
for key, cfg in CONFIG.items():
    print(f"\n\n{'#'*60}")
    print(f" TESTING {cfg['name']}")
    print(f"{'#'*60}")
    
    # 1. Search
    search = catalog.search(
        collections=[cfg["collection"]],
        bbox=BBOX,
        datetime=f"{(date.today() - relativedelta(months=6)).isoformat()}/{date.today().isoformat()}",
        query={"eo:cloud_cover": {"lt": 20.0}},
        limit=5
    )
    
    items = list(search.items())
    if not items:
        print(f"❌ No {key} items found. Check search parameters.")
        continue
        
    # Pick newest
    item = sorted(items, key=lambda x: x.datetime, reverse=True)[0]
    print(f"Found Item: {item.id} ({item.datetime.date()})")
    
    # 2. Geometric Expectation
    exp_w = int(w_m / cfg["res"])
    exp_h = int(h_m / cfg["res"])
    print(f"Expected array size at {cfg['res']}m: ~{exp_w}x{exp_h} pixels")
    
    # 3. Diagnose Primary Bands
    red_arr = run_diagnostic(
        item.assets[cfg["bands"]["red"]].href, 
        "RED BAND", 
        BBOX, 
        cfg["res"]
    )
    
    qa_arr = run_diagnostic(
        item.assets[cfg["bands"]["qa"]].href, 
        "QUALITY/QA BAND", 
        BBOX, 
        cfg["res"] if key == "landsat" else 20.0 # Sentinel SCL is native 20m
    )

    # 4. QA specific check
    if key == "sentinel":
        valid = np.isin(qa_arr, [4, 5, 6]).sum() # Vegetation, Bare Soils, Water
        print(f"  SCL Valid Pixels (4,5,6): {valid}/{qa_arr.size} ({(valid/qa_arr.size):.1%})")
    else:
        # Landsat Bit 0 is Fill
        fill = (qa_arr.astype(int) & 1).sum()
        print(f"  QA_PIXEL Fill Pixels (Bit 0): {fill}/{qa_arr.size} ({(fill/qa_arr.size):.1%})")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)

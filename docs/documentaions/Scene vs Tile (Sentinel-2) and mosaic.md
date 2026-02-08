### Sentinel-2A vs Sentinel-2B (the “A” and “B”)

At the top level, the **Copernicus Sentinel-2 mission** is about **repeated, consistent optical measurements of Earth’s surface** for land monitoring.

They’re **two separate, almost-identical satellites** in the same Sentinel-2 mission:

- **Sentinel-2A** = spacecraft A
    
- **Sentinel-2B** = spacecraft B
    

They fly in the same orbit but **offset in time**, so together they revisit the same place more often.

Why this matters:

- With only one satellite, you get fewer looks (and clouds ruin many looks).
    
- With **2A + 2B**, you roughly **double the observation opportunities**, which is huge for agriculture monitoring.

Think of A and B as **two cameras taking turns on the same racetrack**.
    

When you see an item ID starting with `S2A_...` or `S2B_...`, that tells you which spacecraft captured it.

---

### What “processing level” means (L1C vs L2A)

A “level” is basically: **what the pixel physically means**, not just “quality.”

#### L1C (Level-1C) — “Top of Atmosphere” reflectance

- Data is **geometrically corrected** (so it lines up on maps).
    
- Pixel values represent reflectance **at the top of the atmosphere** (TOA).
    
- Still includes atmospheric effects: haze, aerosols, water vapor influence.

Atmosphere adds noise like aerosols (haze), water vapor (absorption), and Rayleigh scattering (bluish bias).
    

Use it when:

- You want your own atmospheric correction pipeline
    
- You’re doing certain physics-heavy workflows
    

#### L2A (Level-2A) — “Surface Reflectance”

- L1C **plus atmospheric correction**.
    
- Pixel values approximate reflectance **at the ground surface** (surface reflectance), much better for vegetation indices and ML.
    
- Typically includes helpful QA layers, like:
    
    - **SCL (Scene Classification Layer)**: cloud / cloud shadow / water / vegetation / etc.
        
    - Sometimes masks like “valid data” or cloud probability (dataset-dependent)
        

Use it when:

- You’re doing NDVI / crop monitoring
    
- You want consistency over time
    
- You’re feeding ML models (most prefer L2A)

L2A is generally the **analysis-ready** version.
    

---

### Quick intuition

- **2A/2B** = _which satellite took the picture_
    
- **L1C/L2A** = _what kind of cleaned, physical signal the pixels represent_
    

### Scene vs Tile (Sentinel-2)

**Tile (MGRS tile, e.g., `36RUU`)**

- A **fixed grid cell** on Earth (Military Grid Reference System).
    
- Always the **same geographic footprint**, ~**100 km × 100 km**.
    
- It’s like an addressable square in a global chessboard.
    
- You can ask: “Give me all acquisitions for tile 36RUU.”
    

**Scene (acquisition / product / STAC Item)**

- One **capture at a specific time** by a satellite (Sentinel-2A or 2B), processed to a level (L1C/L2A).
    
- A scene usually **contains one tile’s worth of data** (or sometimes multiple related assets), but it’s time-specific: **tile + datetime + processing**.
    
- In STAC terms: you typically get back **Items** that correspond to a specific acquisition for a tile on a date.

Mental compression:

- **Satellite (2A/2B)** = who measured
- **Level (L1C/L2A)** = what physical signal
- **Tile** = where on Earth grid
- **Scene** = that place at that time
- **Mosaic** = engineered “best view”
    

**Rule of thumb**

- **Tile = “where” (fixed area)**
    
- **Scene = “when” (that area on a particular date/time, plus processing version)**
    

So you can have:

- Tile `36RUU` (same area forever)
    
- Many scenes for it: `36RUU @ 2026-02-04`, `36RUU @ 2026-02-09`, etc.
    

---

### What is a “mosaic” 

A **mosaic** is when you **combine multiple scenes** into one seamless image for an area/time.

Why mosaics happen:

- Your AOI crosses **tile boundaries**
    
- One scene is **cloudy** in part of the AOI, so you blend in another scene
    
- You want a **cloud-free composite** for a date range (weekly/monthly)
    

Common mosaic flavors:

- **Spatial mosaic:** stitch neighboring tiles together (bigger map)
    
- **Temporal mosaic / composite:** merge multiple dates (pick best pixels, e.g., lowest cloud, median reflectance)
    

In agriculture, mosaics are used to produce a **clean “best available” surface** for an area and period.

---

### Full tile vs AOI-only pulls (operational reality)

Pulling full Sentinel-2 tiles for a small farm is like downloading an entire season to watch a 10-second clip. Bandwidth and cloud bills hurt.

**What a full tile means**

- A tile is ~**100 km x 100 km** at **10 m** for key bands (B02, B03, B04, B08).
- That is **10,000 km2 -> 100 million pixels per band**.
- One band GeoTIFF can be **hundreds of MB**. Multiply by bands, dates, and farms.

**Decision rule**

Use **full tiles** when the tile is your unit:

- Regional analytics (national crop maps)
- Training large ML models
- Long-term archives / data lakes

Use **AOI-only data** when your unit is a farm or parcel:

- Farm monitoring dashboards
- Field-level NDVI
- Per-loan land assessment
- Most agri product workflows

**Modern trick: do not download full files**

Archives are stored as **Cloud Optimized GeoTIFFs (COGs)**, so you can use **HTTP range requests** to read only the AOI window.

Instead of:

```
download B04.tif -> clip locally
```

Do:

```
read remote COG
window read using AOI bounds
```

Data transfer drops from **hundreds of MB** to **a few MB**.

**Tools / concepts**

- **STAC + COG**
- Windowed reads / lazy loading
- On-the-fly reprojection and clipping
- rasterio windows, stackstac, rio-tiler, xarray + dask
- Sentinel Hub, Planetary Computer, Earth Engine

**Mental model shift**

- Old: satellite image = file
- New: satellite image = queryable data service

**Bottom line**

- AOI-first for applications
- Full tiles for infrastructure

---

### AOI windows vs full tiles (practical rule)

Short answer: you almost never want full tiles for farm analytics. You want your **farm AOI** and read only the pixels you need.

**Full tile**

- ~**100 km x 100 km**
- Hundreds of MB per band
- Massive I/O, slow, expensive
- 99% of pixels irrelevant to your farm

**Farm AOI window**

- 2–5 km around the field
- Tiny fraction of the file
- Fast HTTP range reads from COGs
- Ideal for cloud pipelines and ML

Mental model:

**Satellite files are warehouses. Your model needs a lunchbox.**

---

### Why full TIFF downloads hurt

COGs are designed so you do not download the whole file. A full read (e.g., `src.read(1)` with no window) defeats the cloud-native design.

Correct approach:

- Convert AOI polygon to the scene CRS
- Compute a tight window (or chips)
- Read only that window

Windowed reads are why the fast pipelines feel fast.

---

### When a full tile is actually justified

Rare cases:

1. Building a regional mosaic
2. Precomputing a tile-level dataset
3. Training foundation models
4. Generating national products

Those are data engineering jobs, not farm inference.

---

### Industry pattern for farm ML

- AOI-based windowing
- Pick lowest-cloud scene
- Mask clouds using SCL
- Stack aligned bands
- Normalize
- Run model

Rule professionals use:

- If AOI < 10% of a tile: never load the full tile
- Farms are usually < 1%

One more gotcha: **reprojection can explode I/O**. Reproject the AOI to the scene CRS first, then compute the window to keep reads tight.

# Difference between **EPSG:4326** and **CRS**

## CRS (Coordinate Reference System)

CRS is the generic definition of how spatial coordinates are referenced. It specifies:

* Datum (e.g., WGS84)
* Coordinate system type (geographic or projected)
* Units (degrees or meters)
* Axis order
* Projection parameters (if projected)

Examples:

* EPSG:4326 → Geographic CRS (degrees)
* EPSG:32636 → UTM Zone 36N (meters)
* Custom Albers defined via WKT


## EPSG:4326

A specific geographic CRS:
* Name: WGS84
* Type: Geographic (not projected)
* Units: degrees
* Coordinate order: (longitude, latitude)

Example:
```
(31.2357, 30.0444)  # Cairo
```
Values are angular degrees, not linear distances.

## Conceptual Difference

| EPSG:4326         | Projected CRS (e.g., EPSG:32636) |
| ----------------- | -------------------------------- |
| Degrees           | Meters                           |
| Lat/Lon           | Easting/Northing                 |
| Global            | Zone-based                       |
| Non-uniform scale | Uniform linear scale             |

A 0.1° width in EPSG:4326 is an angular difference, while in UTM it directly represents meters. That is why most satellite rasters (Sentinel, Landsat) are distributed in projected CRSs.

[Coordinate System Jargon: geoid, datum, projection ](https://www.youtube.com/watch?v=Z41Dt7_R180)
[What is a Coordinate Reference Systems (CRS)?](https://www.youtube.com/watch?v=xJyJlKbZFlc)
[Overview: Cloud-Optimized GeoTIFF](https://www.youtube.com/watch?v=wjHtJicaRsI)

# remote sensing, data types

1. Based on Data Structure
• Raster data

* Pixel-based grid structure
* Each pixel stores a value (DN, reflectance, temperature, etc.)
* Examples: GeoTIFF, IMG, NetCDF
GeoTIFF is not a data type — it is a raster file format that stores georeferenced raster data.

• Vector data (used with remote sensing products)

* Points, lines, polygons
* Used for classification results, boundaries, training samples

2. Based on Sensor Type
   • Passive remote sensing

* Measures natural radiation (sunlight or emitted energy)
* Examples: Landsat, Sentinel-2

• Active remote sensing

* Emits its own energy and measures return signal
* Examples: RADAR, LiDAR

3. Based on Spectral Characteristics
   • Panchromatic

* Single broad spectral band
* High spatial resolution

• Multispectral

* Few discrete spectral bands (3–15 bands)
* Example: RGB, NIR

• Hyperspectral

* Hundreds of narrow spectral bands
* Detailed spectral signature analysis

4. Based on Resolution Type
   • Spatial resolution (pixel size: 10m, 30m, etc.)
   • Spectral resolution (number and width of bands)
   • Temporal resolution (revisit time)
   • Radiometric resolution (bit depth: 8-bit, 16-bit, 12-bit)

5. Based on Physical Measurement
   • Optical imagery (reflectance)
   • Thermal imagery (temperature)
   • SAR data (backscatter coefficient)
   • LiDAR point clouds (3D elevation data)

6. Based on Processing Level
   • Raw data (Level-0)
   • Radiometrically corrected (Level-1)
   • Georeferenced / orthorectified
   • Surface reflectance products
   • Classified maps
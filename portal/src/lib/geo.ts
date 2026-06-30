const FEDDAN_TO_SQM = 4200.833

export type LandGeoJSON =
  | GeoJSON.Polygon
  | GeoJSON.MultiPolygon
  | GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon>
  | GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>

export const feddanToSqM = (feddan: number): number => feddan * FEDDAN_TO_SQM

export const sqMToFeddan = (sqm: number): number => sqm / FEDDAN_TO_SQM

export const formatFeddan = (n: number): string =>
  `${n.toLocaleString('en-EG', { maximumFractionDigits: 2 })} fd`

export const EGYPT_BOUNDS: [[number, number], [number, number]] = [
  [24.7, 21.9],
  [37.0, 31.7],
]

export const EGYPT_CENTER: [number, number] = [30.8, 26.8]

/**
 * Calculate the area of a GeoJSON polygon ring in feddans.
 * coords: GeoJSON-order [lng, lat] pairs.
 * Closed rings (first === last) are handled automatically.
 * Uses the spherical excess formula; accurate for Egypt-scale polygons.
 */
export function calcPolygonAreaFeddan(coords: [number, number][]): number {
  // Strip closing duplicate if present
  const pts =
    coords.length > 1 &&
    coords[0][0] === coords[coords.length - 1][0] &&
    coords[0][1] === coords[coords.length - 1][1]
      ? coords.slice(0, -1)
      : coords

  const n = pts.length
  if (n < 3) return 0

  const R = 6_371_000 // Earth mean radius in metres
  let area = 0

  for (let i = 0; i < n; i++) {
    const [lng1, lat1] = pts[i]
    const [lng2, lat2] = pts[(i + 1) % n]
    const phi1 = (lat1 * Math.PI) / 180
    const phi2 = (lat2 * Math.PI) / 180
    const dLng = ((lng2 - lng1) * Math.PI) / 180
    area += dLng * (2 + Math.sin(phi1) + Math.sin(phi2))
  }

  const sqM = Math.abs((area * R * R) / 2)
  return sqM / FEDDAN_TO_SQM
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function validatePolygonCoordinates(coordinates: unknown): string | null {
  if (!Array.isArray(coordinates) || coordinates.length === 0) {
    return 'Polygon geometry must include coordinates.'
  }

  const exterior = coordinates[0]
  if (!Array.isArray(exterior) || exterior.length < 4) {
    return 'Polygon exterior ring must contain at least four points.'
  }

  for (const point of exterior) {
    if (
      !Array.isArray(point) ||
      point.length < 2 ||
      !Number.isFinite(Number(point[0])) ||
      !Number.isFinite(Number(point[1]))
    ) {
      return 'Polygon points must be numeric [longitude, latitude] pairs.'
    }
  }

  return null
}

function validateLandGeoJSON(value: unknown): string | null {
  if (!isObject(value)) return 'GeoJSON must be a JSON object.'

  switch (value.type) {
    case 'Polygon':
      return validatePolygonCoordinates(value.coordinates)
    case 'MultiPolygon': {
      const coordinates = value.coordinates
      if (!Array.isArray(coordinates) || coordinates.length === 0) {
        return 'MultiPolygon geometry must include at least one polygon.'
      }
      for (const polygon of coordinates) {
        const error = validatePolygonCoordinates(polygon)
        if (error) return error
      }
      return null
    }
    case 'Feature':
      if (!isObject(value.geometry)) {
        return 'Feature must include a Polygon or MultiPolygon geometry.'
      }
      return validateLandGeoJSON(value.geometry)
    case 'FeatureCollection': {
      const features = value.features
      if (!Array.isArray(features) || features.length === 0) {
        return 'FeatureCollection must include at least one feature.'
      }
      for (let index = 0; index < features.length; index += 1) {
        const feature = features[index]
        if (!isObject(feature) || feature.type !== 'Feature') {
          return `FeatureCollection item ${index + 1} must be a GeoJSON Feature.`
        }
        const error = validateLandGeoJSON(feature)
        if (error) return `Feature ${index + 1}: ${error}`
      }
      return null
    }
    default:
      return 'Unsupported GeoJSON. Upload a Polygon, MultiPolygon, Feature, or FeatureCollection containing polygon features.'
  }
}

export function normalizeLandGeoJSON(value: unknown): LandGeoJSON {
  const error = validateLandGeoJSON(value)
  if (error) throw new Error(error)
  return value as LandGeoJSON
}

export function calcGeoJSONAreaFeddan(geojson: LandGeoJSON): number {
  switch (geojson.type) {
    case 'Polygon':
      return calcPolygonAreaFeddan(geojson.coordinates[0] as [number, number][])
    case 'MultiPolygon':
      return geojson.coordinates.reduce(
        (total, polygon) => total + calcPolygonAreaFeddan(polygon[0] as [number, number][]),
        0,
      )
    case 'Feature':
      return calcGeoJSONAreaFeddan(geojson.geometry)
    case 'FeatureCollection':
      return geojson.features.reduce(
        (total, feature) => total + calcGeoJSONAreaFeddan(feature.geometry),
        0,
      )
  }
}

export function countGeoJSONAOIs(geojson: LandGeoJSON): number {
  switch (geojson.type) {
    case 'Polygon':
      return 1
    case 'MultiPolygon':
      return geojson.coordinates.length
    case 'Feature':
      return countGeoJSONAOIs(geojson.geometry)
    case 'FeatureCollection':
      return geojson.features.reduce(
        (total, feature) => total + countGeoJSONAOIs(feature.geometry),
        0,
      )
  }
}

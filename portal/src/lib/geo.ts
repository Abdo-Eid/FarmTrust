const FEDDAN_TO_SQM = 4200.833

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

const FEDDAN_TO_SQM = 4200.833

export const feddanToSqM = (feddan: number): number => feddan * FEDDAN_TO_SQM

export const sqMToFeddan = (sqm: number): number => sqm / FEDDAN_TO_SQM

export const formatFeddan = (n: number): string =>
  `${n.toLocaleString('en-EG', { maximumFractionDigits: 1 })} fd`

export const EGYPT_BOUNDS: [[number, number], [number, number]] = [
  [24.7, 21.9],
  [37.0, 31.7],
]

export const EGYPT_CENTER: [number, number] = [30.8, 26.8]

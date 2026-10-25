// Radar geometry (Bible 52.2): pure and map-free. No tiles, no geocoding, no third-party service.

export interface Point {
  x: number
  y: number
}

/**
 * Place a shop on a circle of `size` px radius around the centre.
 * Bearing is a compass bearing (0 = north, clockwise). A shop beyond the radius is pinned to the
 * edge rather than drawn outside the picture.
 */
export function radarPoint(
  distanceKm: number,
  bearingDeg: number,
  radiusKm: number,
  size: number,
  centre: Point,
): Point {
  const fraction = radiusKm > 0 ? Math.min(Math.max(distanceKm / radiusKm, 0), 1) : 0
  const r = fraction * size
  const rad = (bearingDeg * Math.PI) / 180
  return { x: centre.x + r * Math.sin(rad), y: centre.y - r * Math.cos(rad) }
}

export function ringLabels(radiusKm: number): number[] {
  const round = (n: number) => Math.round(n * 10) / 10
  return [round(radiusKm / 3), round((2 * radiusKm) / 3), round(radiusKm)]
}

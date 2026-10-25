// Small geography helpers. Pure, no network.

export interface LatLng {
  lat: number
  lng: number
}

const EARTH_RADIUS_KM = 6371.0088
const rad = (d: number) => (d * Math.PI) / 180
const deg = (r: number) => (r * 180) / Math.PI

/** The point `distanceKm` away from `from` along a compass bearing (0 = north, clockwise). */
export function destinationPoint(from: LatLng, bearingDeg: number, distanceKm: number): LatLng {
  const delta = distanceKm / EARTH_RADIUS_KM
  const theta = rad(bearingDeg)
  const phi1 = rad(from.lat)
  const lambda1 = rad(from.lng)
  const phi2 = Math.asin(
    Math.sin(phi1) * Math.cos(delta) + Math.cos(phi1) * Math.sin(delta) * Math.cos(theta),
  )
  const lambda2 =
    lambda1 +
    Math.atan2(
      Math.sin(theta) * Math.sin(delta) * Math.cos(phi1),
      Math.cos(delta) - Math.sin(phi1) * Math.sin(phi2),
    )
  return { lat: deg(phi2), lng: ((deg(lambda2) + 540) % 360) - 180 }
}

/** Great-circle distance in km (used to check the helper above against the backend's maths). */
export function distanceKm(a: LatLng, b: LatLng): number {
  const dPhi = rad(b.lat - a.lat)
  const dLambda = rad(b.lng - a.lng)
  const h =
    Math.sin(dPhi / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLambda / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)))
}

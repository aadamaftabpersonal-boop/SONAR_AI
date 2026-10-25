// OpenStreetMap's public tiles are for light use and need visible attribution (their tile usage
// policy). The URL is configurable so a heavier deployment can switch provider without a code
// change (set VITE_TILE_URL; it is public by construction and must hold no secret). We never
// prefetch tiles or offer offline download.
export const TILE_URL: string =
  import.meta.env.VITE_TILE_URL ?? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

export const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'

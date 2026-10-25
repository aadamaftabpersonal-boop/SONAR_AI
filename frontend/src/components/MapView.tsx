import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef, useState } from 'react'
import type { LatLng } from '../geo'
import { ATTRIBUTION, TILE_URL } from '../tiles'

export interface MapPin {
  id: string
  name: string
  position: LatLng
  /** the text shown beside the pin: status is never colour alone */
  label: string
  color: string
}

interface Props {
  center: LatLng
  radiusKm: number
  pins?: MapPin[]
  /** a point the user picked (shown as a marker) */
  picked?: LatLng | null
  /** when set, clicking the map reports the clicked point */
  onPick?: (point: LatLng) => void
  height?: number
  ariaLabel: string
}

/** A map with the search radius, the shops and (optionally) a clickable spot. */
export function MapView({ center, radiusKm, pins = [], picked, onPick, height = 300, ariaLabel }: Props) {
  const element = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layer = useRef<L.LayerGroup | null>(null)
  const pickHandler = useRef(onPick)
  const [tilesFailed, setTilesFailed] = useState(false)
  pickHandler.current = onPick

  useEffect(() => {
    if (!element.current) return
    const instance = L.map(element.current, { scrollWheelZoom: false }).setView(
      [center.lat, center.lng],
      13,
    )
    const tiles = L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION })
    tiles.on('tileerror', () => setTilesFailed(true))
    tiles.on('tileload', () => setTilesFailed(false))
    tiles.addTo(instance)
    layer.current = L.layerGroup().addTo(instance)
    instance.on('click', (e: L.LeafletMouseEvent) =>
      pickHandler.current?.({ lat: e.latlng.lat, lng: e.latlng.lng }),
    )
    map.current = instance
    return () => {
      instance.remove()
      map.current = null
    }
    // the map is created once; the effect below redraws what is on it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const instance = map.current
    const group = layer.current
    if (!instance || !group) return
    group.clearLayers()
    const circle = L.circle([center.lat, center.lng], {
      radius: radiusKm * 1000,
      color: '#0f766e',
      weight: 1.5,
      dashArray: '4 6',
      fillOpacity: 0.05,
    }).addTo(group)
    L.circleMarker([center.lat, center.lng], {
      radius: 7,
      color: '#fff',
      weight: 2,
      fillColor: '#0f766e',
      fillOpacity: 1,
    })
      .bindTooltip('You', { permanent: true, direction: 'bottom', offset: [0, 6] })
      .addTo(group)
    for (const pin of pins) {
      L.circleMarker([pin.position.lat, pin.position.lng], {
        radius: 8,
        color: '#fff',
        weight: 2,
        fillColor: pin.color,
        fillOpacity: 1,
      })
        .bindTooltip(`${pin.name} · ${pin.label}`, { permanent: pins.length <= 8, direction: 'right' })
        .addTo(group)
    }
    if (picked) {
      L.circleMarker([picked.lat, picked.lng], {
        radius: 9,
        color: '#fff',
        weight: 3,
        fillColor: '#e11d48',
        fillOpacity: 1,
      })
        .bindTooltip('Search here', { permanent: true, direction: 'top', offset: [0, -8] })
        .addTo(group)
    }
    // fitting needs a laid-out container; skip it when there is no size (tests, hidden tabs)
    const { clientWidth, clientHeight } = instance.getContainer()
    if (clientWidth > 0 && clientHeight > 0) {
      instance.fitBounds(circle.getBounds(), { padding: [16, 16], maxZoom: 16 })
    } else {
      instance.setView([center.lat, center.lng], 13)
    }
  }, [center.lat, center.lng, radiusKm, pins, picked])

  return (
    <div>
      <div
        ref={element}
        role="application"
        aria-label={ariaLabel}
        style={{ height, borderRadius: 12, overflow: 'hidden', zIndex: 0 }}
        className="border border-[var(--border)]"
      />
      {tilesFailed && (
        <p role="status" className="mt-2 text-xs text-[var(--warn)]">
          Map tiles could not be loaded (offline or blocked). Shops are still shown, and the Radar tab
          works without any network.
        </p>
      )}
    </div>
  )
}

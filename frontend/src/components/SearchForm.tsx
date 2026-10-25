import { useState } from 'react'
import type { FormEvent } from 'react'
import type { ClarificationQuestion, PublicConfig, SearchRequest } from '../api'

const PRESETS = [
  { label: 'Demo locality, Bengaluru', lat: 12.9716, lng: 77.5946 },
]

const labelOf = (key: string) => key.replaceAll('_', ' ')

interface Props {
  config: PublicConfig
  busy: boolean
  fieldError: { field: string | null; message: string } | null
  clarification: ClarificationQuestion[] | null
  onSubmit: (request: SearchRequest, accessKey: string) => void
}

export function SearchForm({ config, busy, fieldError, clarification, onSubmit }: Props) {
  const categoryNames = Object.keys(config.categories)
  const [accessKey, setAccessKey] = useState('') // memory only: never stored, never in the bundle
  const [category, setCategory] = useState(categoryNames[0] ?? 'pharmacy')
  const [itemName, setItemName] = useState('')
  const [attributes, setAttributes] = useState<Record<string, string>>({})
  const [preset, setPreset] = useState(0)
  const [coords, setCoords] = useState<{ lat: number; lng: number; label: string } | null>(null)
  const [geoNote, setGeoNote] = useState<string | null>(null)
  const [radius, setRadius] = useState(3)
  const [demo, setDemo] = useState(true)
  const [askEveryone, setAskEveryone] = useState(false)

  const cat = config.categories[category]
  const location = coords ?? { ...PRESETS[preset], label: PRESETS[preset].label }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeoNote('Location is not available in this browser. Using the demo locality.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: 'My location' })
        setGeoNote(null)
      },
      () => {
        setCoords(null)
        setGeoNote('Location permission was denied. Using the demo locality.')
      },
    )
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    const attrText = Object.values(attributes).filter(Boolean).join(' ')
    onSubmit(
      {
        query_text: `Does anyone nearby have ${itemName} ${attrText} in stock right now?`.replace(
          /\s+/g,
          ' ',
        ),
        category,
        item: {
          name: itemName.trim(),
          attributes: Object.fromEntries(
            Object.entries(attributes).filter(([, v]) => v.trim() !== ''),
          ),
        },
        location: { lat: location.lat, lng: location.lng, label: location.label },
        radius_km: radius,
        demo_mode: demo,
        mode: askEveryone ? 'THOROUGH' : 'FAST',
      },
      accessKey,
    )
  }

  const errorFor = (field: string) => (fieldError?.field === field ? fieldError.message : null)

  return (
    <form onSubmit={submit} className="card grid gap-5 p-5 sm:p-6" aria-label="New search">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="font-semibold">What are you looking for?</span>
          <input
            className="field"
            required
            maxLength={80}
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            placeholder={category === 'pharmacy' ? 'e.g. Paracetamol' : 'e.g. Screen replacement'}
            aria-invalid={!!errorFor('item.name')}
          />
          {errorFor('item.name') && <span className="text-sm text-[var(--bad)]">{errorFor('item.name')}</span>}
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-semibold">Category</span>
          <select
            className="field"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setAttributes({})
            }}
          >
            {categoryNames.map((name) => (
              <option key={name} value={name}>
                {config.categories[name].display_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {cat.essential_attributes.map((attr) => (
          <label key={attr} className="grid gap-1 text-sm">
            <span className="font-semibold capitalize">{labelOf(attr)}</span>
            <input
              className="field"
              required
              maxLength={80}
              value={attributes[attr] ?? ''}
              onChange={(e) => setAttributes({ ...attributes, [attr]: e.target.value })}
              placeholder={attr === 'strength' ? 'e.g. 500 mg' : ''}
              aria-invalid={!!errorFor(`item.attributes.${attr}`)}
            />
            {errorFor(`item.attributes.${attr}`) && (
              <span className="text-sm text-[var(--bad)]">{errorFor(`item.attributes.${attr}`)}</span>
            )}
          </label>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-1 text-sm">
          <label htmlFor="locality" className="font-semibold">
            Where
          </label>
          <div className="flex gap-2">
            <select
              id="locality"
              className="field"
              value={preset}
              disabled={!!coords}
              onChange={(e) => {
                setPreset(Number(e.target.value))
                setCoords(null)
              }}
            >
              {PRESETS.map((p, i) => (
                <option key={p.label} value={i}>
                  {p.label}
                </option>
              ))}
            </select>
            <button type="button" className="btn" onClick={useMyLocation}>
              Use mine
            </button>
          </div>
          {coords && (
            <span className="text-[var(--muted)]">
              Searching around your current location, not the locality above.{' '}
              <button type="button" className="font-semibold underline" onClick={() => setCoords(null)}>
                Use the demo locality instead
              </button>
            </span>
          )}
          {geoNote && <span className="text-[var(--warn)]">{geoNote}</span>}
        </div>
        <label className="grid gap-1 text-sm">
          <span className="font-semibold">
            Radius: <output>{radius}</output> km
          </span>
          <input
            type="range"
            min={config.min_radius_km}
            max={Math.min(config.max_radius_km, 10)}
            step={0.5}
            value={radius}
            onChange={(e) => setRadius(Number(e.target.value))}
            aria-label="Search radius in kilometres"
          />
          {errorFor('radius_km') && <span className="text-[var(--bad)]">{errorFor('radius_km')}</span>}
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="font-semibold">Access key</span>
          <input
            className="field"
            type="password"
            autoComplete="off"
            required
            value={accessKey}
            onChange={(e) => setAccessKey(e.target.value)}
            placeholder="Demo key (kept in memory only)"
          />
        </label>
        <label className="flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            className="mt-1 size-4"
            checked={demo}
            onChange={(e) => setDemo(e.target.checked)}
          />
          <span>
            <span className="font-semibold">Demo mode (simulated calls)</span>
            <br />
            <span className="text-[var(--muted)]">
              Nobody is phoned. Every result is clearly marked as simulated.
            </span>
          </span>
        </label>
      </div>

      <label className="flex items-start gap-3 text-sm">
        <input
          type="checkbox"
          className="mt-1 size-4"
          checked={askEveryone}
          onChange={(e) => setAskEveryone(e.target.checked)}
        />
        <span>
          <span className="font-semibold">Ask every shop</span>
          <br />
          <span className="text-[var(--muted)]">
            By default Sonar stops calling once two shops have confirmed. Turn this on to call all of
            them.
          </span>
        </span>
      </label>

      {clarification && (
        <div role="alert" className="rounded-xl bg-[var(--warn-bg)] p-3 text-sm text-[var(--warn)]">
          <p className="font-semibold">Sonar needs a little more detail before it calls anyone:</p>
          <ul className="ml-5 list-disc">
            {clarification.map((q) => (
              <li key={q.field}>{q.question}</li>
            ))}
          </ul>
        </div>
      )}
      {fieldError && !fieldError.field?.startsWith('item.') && fieldError.field !== 'radius_km' && (
        <div role="alert" className="rounded-xl bg-[var(--bad-bg)] p-3 text-sm text-[var(--bad)]">
          {fieldError.message}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Starting…' : 'Search by phone'}
        </button>
        <p className="text-sm text-[var(--muted)]">{config.disclaimer}</p>
      </div>
    </form>
  )
}

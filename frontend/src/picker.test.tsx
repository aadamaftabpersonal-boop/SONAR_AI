import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { PublicConfig } from './api'
import { SearchForm } from './components/SearchForm'
// --- picking a location on the map --------------------------------------------------------------

vi.mock('./components/MapView', async (original) => {
  const real = await original<typeof import('./components/MapView')>()
  return {
    ...real,
    // a stand-in map with a button that "clicks" a known point, because jsdom cannot lay out tiles
    MapView: (props: { onPick?: (p: { lat: number; lng: number }) => void; picked?: { lat: number } | null }) => (
      <div>
        <button type="button" onClick={() => props.onPick?.({ lat: 28.6139, lng: 77.209 })}>
          click the map
        </button>
        <span>{props.picked ? 'marker shown' : 'no marker'}</span>
      </div>
    ),
  }
})

const config: PublicConfig = {
  categories: {
    pharmacy: { display_name: 'Pharmacy', essential_attributes: ['strength'], required_fields_default: ['availability'] },
  },
  min_radius_km: 0.5,
  max_radius_km: 25,
  max_targets_per_search: 5,
  simulated_banner: 'SIMULATED',
  disclaimer: 'x',
}

describe('SearchForm map picker', () => {
  const setup = () => {
    const onSubmit = vi.fn()
    render(<SearchForm config={config} busy={false} fieldError={null} clarification={null} onSubmit={onSubmit} />)
    return { onSubmit, user: userEvent.setup() }
  }

  it('is closed until asked for, and opens and closes from one button', async () => {
    const { user } = setup()
    expect(screen.queryByText('click the map')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Pick on map' }))
    expect(screen.getByText('click the map')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Hide map' }))
    expect(screen.queryByText('click the map')).not.toBeInTheDocument()
  })

  it('searches around the clicked spot, and says so', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText('What are you looking for?'), 'X')
    await user.type(screen.getByLabelText(/strength/i), '5')
    await user.type(screen.getByLabelText('Access key'), 'k')
    await user.click(screen.getByRole('button', { name: 'Pick on map' }))
    await user.click(screen.getByText('click the map'))
    expect(screen.getByText(/the spot you picked/)).toBeInTheDocument()
    expect(screen.getByText('marker shown')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit.mock.calls[0][0].location).toMatchObject({ lat: 28.6139, lng: 77.209, label: 'Picked on map' })
  })

  it('goes back to the demo locality from a picked spot', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText('What are you looking for?'), 'X')
    await user.type(screen.getByLabelText(/strength/i), '5')
    await user.type(screen.getByLabelText('Access key'), 'k')
    await user.click(screen.getByRole('button', { name: 'Pick on map' }))
    await user.click(screen.getByText('click the map'))
    await user.click(screen.getByRole('button', { name: /use the demo locality instead/i }))
    expect(screen.getByLabelText('Where')).toBeEnabled()
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit.mock.calls[0][0].location).toMatchObject({ lat: 12.9716, lng: 77.5946 })
  })

  it('fills in a worked example in one click', async () => {
    const { user } = setup()
    await user.click(screen.getByRole('button', { name: /Try: Paracetamol 500 mg/ }))
    expect(screen.getByLabelText('What are you looking for?')).toHaveValue('Paracetamol')
    expect(screen.getByLabelText(/strength/i)).toHaveValue('500 mg')
  })
})



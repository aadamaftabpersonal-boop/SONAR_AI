import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { PublicConfig } from '../api'
import { SearchForm } from './SearchForm'

const config: PublicConfig = {
  categories: {
    pharmacy: { display_name: 'Pharmacy', essential_attributes: ['strength'], required_fields_default: ['availability', 'price'] },
    computer_repair: { display_name: 'Repair', essential_attributes: ['device_model', 'problem'], required_fields_default: ['availability_today'] },
  },
  min_radius_km: 0.5,
  max_radius_km: 25,
  max_targets_per_search: 5,
  simulated_banner: 'SIMULATED',
  disclaimer: 'Sonar reports what the business said. It does not give medical advice.',
}

const setup = (props: Partial<React.ComponentProps<typeof SearchForm>> = {}) => {
  const onSubmit = vi.fn()
  render(<SearchForm config={config} busy={false} fieldError={null} clarification={null} onSubmit={onSubmit} {...props} />)
  return { onSubmit, user: userEvent.setup() }
}

describe('SearchForm', () => {
  it('asks for the essential attributes of the chosen category', async () => {
    const { user } = setup()
    expect(screen.getByLabelText(/strength/i)).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Category'), 'computer_repair')
    expect(screen.getByLabelText(/device model/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/problem/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/strength/i)).not.toBeInTheDocument()
  })

  it('submits a structured request with demo mode on by default', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText('What are you looking for?'), 'Paracetamol')
    await user.type(screen.getByLabelText(/strength/i), '500 mg')
    await user.type(screen.getByLabelText('Access key'), 'k')
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
    const [request, key] = onSubmit.mock.calls[0]
    expect(key).toBe('k')
    expect(request).toMatchObject({
      category: 'pharmacy',
      item: { name: 'Paracetamol', attributes: { strength: '500 mg' } },
      radius_km: 3,
      demo_mode: true,
    })
    expect(request.location).toMatchObject({ lat: 12.9716, lng: 77.5946 })
  })

  it('lets the user turn demo mode off, which is a visible, deliberate choice', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText('What are you looking for?'), 'X')
    await user.type(screen.getByLabelText(/strength/i), '5')
    await user.type(screen.getByLabelText('Access key'), 'k')
    await user.click(screen.getByRole('checkbox', { name: /demo mode/i }))
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit.mock.calls[0][0].demo_mode).toBe(false)
  })

  it('stops early by default and calls every shop only when asked', async () => {
    const { onSubmit, user } = setup()
    const fill = async () => {
      await user.type(screen.getByLabelText('What are you looking for?'), 'X')
      await user.type(screen.getByLabelText(/strength/i), '5')
      await user.type(screen.getByLabelText('Access key'), 'k')
    }
    await fill()
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit.mock.calls[0][0].mode).toBe('FAST')

    await user.click(screen.getByRole('checkbox', { name: /ask every shop/i }))
    await user.click(screen.getByRole('button', { name: /search by phone/i }))
    expect(onSubmit.mock.calls[1][0].mode).toBe('THOROUGH')
  })

  it('keeps the access key in a password field', () => {
    setup()
    expect(screen.getByLabelText('Access key')).toHaveAttribute('type', 'password')
  })

  it('shows the clarification questions inline', () => {
    setup({ clarification: [{ field: 'item.attributes.strength', question: 'What strength should we ask about?' }] })
    expect(screen.getByRole('alert')).toHaveTextContent('What strength should we ask about?')
  })

  it('shows a field error next to the field and a general error as an alert', () => {
    const { unmount } = render(
      <SearchForm config={config} busy={false} fieldError={{ field: 'item.name', message: 'item name is not an acceptable product name' }} clarification={null} onSubmit={vi.fn()} />,
    )
    expect(screen.getByText('item name is not an acceptable product name')).toBeInTheDocument()
    unmount()
    render(<SearchForm config={config} busy={false} fieldError={{ field: null, message: 'Missing or invalid access key' }} clarification={null} onSubmit={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Missing or invalid access key')
  })

  it('disables the button while a search is starting', () => {
    setup({ busy: true })
    expect(screen.getByRole('button', { name: /starting/i })).toBeDisabled()
  })

  it('falls back to the demo locality when location permission is denied', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition: (_ok: unknown, fail: () => void) => fail() },
    })
    const { user } = setup()
    await user.click(screen.getByRole('button', { name: /use mine/i }))
    expect(screen.getByText(/permission was denied/i)).toBeInTheDocument()
  })

  it('shows the medical-advice disclaimer', () => {
    setup()
    expect(screen.getByText(/does not give medical advice/i)).toBeInTheDocument()
  })
})

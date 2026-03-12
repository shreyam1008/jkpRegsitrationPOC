import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import SearchPage from '../../client/src/pages/SearchPage'

const mockSearchSatsangis = vi.fn()
vi.mock('../../client/src/api', () => ({
  searchSatsangis: (...args: unknown[]) => mockSearchSatsangis(...args),
}))

beforeEach(() => {
  mockSearchSatsangis.mockReset()
  mockSearchSatsangis.mockResolvedValue([])
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/search']}>
      <SearchPage />
    </MemoryRouter>,
  )
}

const SAMPLE = {
  satsangi_id: 'A1',
  first_name: 'Ram',
  last_name: 'Kumar',
  phone_number: '9876543210',
  nationality: 'Indian',
  country: 'India',
  created_at: '2025-01-01',
}

describe('SearchPage', () => {
  it('renders search input and page header', async () => {
    renderPage()
    expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument()
    expect(screen.getByText('Search Devotees')).toBeInTheDocument()
  })

  it('shows result cards with initials and full name', async () => {
    mockSearchSatsangis.mockResolvedValueOnce([SAMPLE])
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Ram Kumar')).toBeInTheDocument()
      expect(screen.getByText('RK')).toBeInTheDocument()
      expect(screen.getByText('A1')).toBeInTheDocument()
    })
  })

  it('shows no results message when empty', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No satsangis found.')).toBeInTheDocument()
    })
  })

  it('searches with debounce when typing', async () => {
    mockSearchSatsangis.mockResolvedValue([])
    renderPage()

    const input = screen.getByPlaceholderText(/search by name/i)
    fireEvent.change(input, { target: { value: 'Ram' } })

    await waitFor(
      () => {
        expect(mockSearchSatsangis).toHaveBeenCalledWith('Ram')
      },
      { timeout: 500 },
    )
  })

  it('displays tags for govt ID, first timer, banned', async () => {
    mockSearchSatsangis.mockResolvedValueOnce([
      {
        ...SAMPLE,
        govt_id_type: 'Aadhar Card',
        govt_id_number: '1234-5678-9012',
        first_timer: true,
        banned: true,
        city: 'Delhi',
        state: 'Delhi',
      },
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/aadhar card/i)).toBeInTheDocument()
      expect(screen.getByText('First Timer')).toBeInTheDocument()
      expect(screen.getByText('Banned')).toBeInTheDocument()
    })
  })

  it('shows result count', async () => {
    mockSearchSatsangis.mockResolvedValueOnce([SAMPLE])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('1 result found')).toBeInTheDocument()
    })
  })
})

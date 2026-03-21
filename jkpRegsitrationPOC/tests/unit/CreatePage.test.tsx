import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import CreatePage from '../../client/src/pages/CreatePage'

const mockCreateSatsangi = vi.fn()
vi.mock('../../client/src/api', () => ({
  createSatsangi: (...args: unknown[]) => mockCreateSatsangi(...args),
}))

beforeEach(() => {
  mockCreateSatsangi.mockReset()
})

function LocationDisplay() {
  const loc = useLocation()
  return <div data-testid="location">{loc.pathname}</div>
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/create']}>
      <CreatePage />
      <LocationDisplay />
    </MemoryRouter>,
  )
}

describe('CreatePage', () => {
  it('renders page header and all three form sections', () => {
    renderPage()
    expect(screen.getByText('Add New Devotee')).toBeInTheDocument()
    expect(screen.getByText('Personal Details')).toBeInTheDocument()
    expect(screen.getByText('Address Details')).toBeInTheDocument()
    expect(screen.getByText('Other Details')).toBeInTheDocument()
  })

  it('renders required fields', () => {
    renderPage()
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument()
  })

  it('renders dropdowns for gender, nationality, state', () => {
    renderPage()
    expect(screen.getByRole('combobox', { name: /gender/i })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: /nationality/i })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: /^state$/i })).toBeInTheDocument()
    expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(5)
  })

  it('has a Register Satsangi submit button', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /register satsangi/i })).toBeInTheDocument()
  })

  it('shows validation error when required fields are empty', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /register satsangi/i }))
    await waitFor(() => {
      expect(screen.getByText(/first name, last name and phone number are required/i)).toBeInTheDocument()
    })
  })

  it('calls createSatsangi and shows success on submit', async () => {
    mockCreateSatsangi.mockResolvedValueOnce({ satsangi_id: 'X1' })
    renderPage()

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Sita' } })
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'Devi' } })
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '9876543210' } })
    fireEvent.click(screen.getByRole('button', { name: /register satsangi/i }))

    await waitFor(() => {
      expect(mockCreateSatsangi).toHaveBeenCalledTimes(1)
      const call = mockCreateSatsangi.mock.calls[0][0]
      expect(call.first_name).toBe('Sita')
      expect(call.last_name).toBe('Devi')
      expect(call.phone_number).toBe('9876543210')
    })
    await waitFor(() => {
      expect(screen.getByText(/registered! satsangi id: x1/i)).toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    mockCreateSatsangi.mockRejectedValueOnce(new Error('fail'))
    renderPage()

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Test' } })
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'User' } })
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '111' } })
    fireEvent.click(screen.getByRole('button', { name: /register satsangi/i }))

    await waitFor(() => {
      expect(screen.getByText(/failed to register/i)).toBeInTheDocument()
    })
  })

  it('renders all three collapsible section titles', () => {
    renderPage()
    expect(screen.getByText('Personal Details')).toBeInTheDocument()
    expect(screen.getByText('Address Details')).toBeInTheDocument()
    expect(screen.getByText('Other Details')).toBeInTheDocument()
  })

  it('renders checkboxes for boolean fields', () => {
    renderPage()
    expect(screen.getByText('Has Room in Ashram')).toBeInTheDocument()
    expect(screen.getByText('First Timer')).toBeInTheDocument()
    expect(screen.getByText('Banned')).toBeInTheDocument()
  })
})

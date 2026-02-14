import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../test/helpers'

// Mocks — must be before component import
const mockRegister = vi.fn()
const mockNavigate = vi.fn()
const mockSearchParams = new URLSearchParams()
const mockSetSearchParams = vi.fn()

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    register: mockRegister,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams, mockSetSearchParams],
  }
})

import { Register } from './Register'

describe('Register', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParams.delete('google_email')
    mockSearchParams.delete('google_name')
    mockSearchParams.delete('google_id')
  })

  it('renders all form fields', () => {
    renderWithProviders(<Register />)

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/i am a/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('renders link to login page', () => {
    renderWithProviders(<Register />)

    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })

  it('does not show teacher_type field by default (parent role)', () => {
    renderWithProviders(<Register />)

    expect(screen.queryByLabelText(/teacher type/i)).not.toBeInTheDocument()
  })

  it('shows teacher_type dropdown when role is teacher', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Register />)

    await user.selectOptions(screen.getByLabelText(/i am a/i), 'teacher')

    expect(screen.getByLabelText(/teacher type/i)).toBeInTheDocument()
    expect(screen.getByText(/school teacher/i)).toBeInTheDocument()
    expect(screen.getByText(/private tutor/i)).toBeInTheDocument()
  })

  it('hides teacher_type when switching away from teacher role', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Register />)

    await user.selectOptions(screen.getByLabelText(/i am a/i), 'teacher')
    expect(screen.getByLabelText(/teacher type/i)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText(/i am a/i), 'student')
    expect(screen.queryByLabelText(/teacher type/i)).not.toBeInTheDocument()
  })

  it('validates password match', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'Test User')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'different456')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('submits form and calls register() on success', async () => {
    mockRegister.mockResolvedValue(undefined)
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'New User')
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockRegister).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'password123',
      full_name: 'New User',
      role: 'parent',
    })
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('submits with teacher_type when role is teacher', async () => {
    mockRegister.mockResolvedValue(undefined)
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'Teacher User')
    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    await user.selectOptions(screen.getByLabelText(/i am a/i), 'teacher')
    await user.selectOptions(screen.getByLabelText(/teacher type/i), 'school_teacher')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockRegister).toHaveBeenCalledWith({
      email: 'teacher@example.com',
      password: 'password123',
      full_name: 'Teacher User',
      role: 'teacher',
      teacher_type: 'school_teacher',
    })
  })

  it('shows error message on registration failure', async () => {
    mockRegister.mockRejectedValue({
      response: { data: { detail: 'Email already registered' } },
    })
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'Test')
    await user.type(screen.getByLabelText(/email/i), 'dup@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/email already registered/i)).toBeInTheDocument()
    })
  })

  it('shows generic error when no detail in response', async () => {
    mockRegister.mockRejectedValue(new Error('Network'))
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'Test')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/registration failed/i)).toBeInTheDocument()
    })
  })

  it('disables submit button while loading', async () => {
    mockRegister.mockReturnValue(new Promise(() => {}))
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/full name/i), 'Test')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
  })

  it('pre-fills from Google OAuth params', () => {
    mockSearchParams.set('google_email', 'google@example.com')
    mockSearchParams.set('google_name', 'Google User')
    mockSearchParams.set('google_id', 'google-123')

    renderWithProviders(<Register />)

    expect(screen.getByLabelText(/email/i)).toHaveValue('google@example.com')
    expect(screen.getByLabelText(/email/i)).toBeDisabled()
    expect(screen.getByLabelText(/full name/i)).toHaveValue('Google User')
    expect(screen.getByText(/complete your google account setup/i)).toBeInTheDocument()
  })

  it('includes google_id in register call for Google signup', async () => {
    mockSearchParams.set('google_email', 'google@example.com')
    mockSearchParams.set('google_name', 'Google User')
    mockSearchParams.set('google_id', 'google-123')
    mockRegister.mockResolvedValue(undefined)
    const user = userEvent.setup()

    renderWithProviders(<Register />)

    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockRegister).toHaveBeenCalledWith(
      expect.objectContaining({ google_id: 'google-123' }),
    )
  })
})

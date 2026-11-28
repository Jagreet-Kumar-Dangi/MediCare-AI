import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DoctorRegisterPage } from './DoctorRegisterPage'
import { RegisterPage } from './RegisterPage'

const authMocks = vi.hoisted(() => ({
  registerPatient: vi.fn(),
  registerDoctor: vi.fn(),
}))

vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    registerPatient: authMocks.registerPatient,
    registerDoctor: authMocks.registerDoctor,
    status: 'unauthenticated',
    user: null,
  }),
}))

function VerificationDestination() {
  const location = useLocation()
  const state = location.state as { email?: string; role?: string } | null
  return <p>{`Verify ${state?.role} ${state?.email}`}</p>
}

function renderRegistration(page: ReactNode, path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={page} path={path} />
        <Route
          element={<VerificationDestination />}
          path="/verify-email"
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('registration verification routing', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    authMocks.registerPatient.mockResolvedValue({})
    authMocks.registerDoctor.mockResolvedValue({})
  })

  it('routes patient registration to email verification', async () => {
    const user = userEvent.setup()
    renderRegistration(<RegisterPage />, '/register')

    await user.type(screen.getByLabelText('First name'), 'Avery')
    await user.type(screen.getByLabelText('Last name'), 'Patient')
    await user.type(screen.getByLabelText('Email address'), 'patient@example.com')
    await user.type(screen.getByLabelText('Password'), 'a-strong-password-123')
    await user.type(screen.getByLabelText('Confirm password'), 'a-strong-password-123')
    await user.click(screen.getByRole('button', { name: 'Create patient account' }))

    expect(await screen.findByText('Verify PATIENT patient@example.com')).toBeTruthy()
    expect(authMocks.registerPatient).toHaveBeenCalledWith({
      first_name: 'Avery',
      last_name: 'Patient',
      email: 'patient@example.com',
      password: 'a-strong-password-123',
    })
  })

  it('routes doctor registration to email verification without signing in', async () => {
    const user = userEvent.setup()
    renderRegistration(<DoctorRegisterPage />, '/register/doctor')

    await user.type(screen.getByLabelText('Full name'), 'Dr. Devon North')
    await user.type(screen.getByLabelText('Email address'), 'doctor@example.com')
    await user.type(screen.getByLabelText('Specialization'), 'Family Medicine')
    await user.type(screen.getByLabelText('Qualification'), 'MD')
    await user.type(
      screen.getByLabelText('Medical registration number'),
      'DOC-0001',
    )
    await user.clear(screen.getByLabelText('Years of experience'))
    await user.type(screen.getByLabelText('Years of experience'), '5')
    await user.type(screen.getByLabelText('Password'), 'another-strong-password')
    await user.type(screen.getByLabelText('Confirm password'), 'another-strong-password')
    await user.click(screen.getByRole('button', { name: 'Submit for verification' }))

    expect(await screen.findByText('Verify DOCTOR doctor@example.com')).toBeTruthy()
    await waitFor(() => {
      expect(authMocks.registerDoctor).toHaveBeenCalledWith(
        expect.objectContaining({
          email: 'doctor@example.com',
          years_of_experience: 5,
        }),
      )
    })
  })
})

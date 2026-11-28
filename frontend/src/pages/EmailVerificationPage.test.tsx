import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  confirmEmailVerification,
  resendVerificationEmail,
  sendVerificationEmail,
} from '../api/auth'
import { EmailVerificationPage } from './EmailVerificationPage'

vi.mock('../api/auth', () => ({
  confirmEmailVerification: vi.fn(),
  resendVerificationEmail: vi.fn(),
  sendVerificationEmail: vi.fn(),
}))

function renderVerification(state: Record<string, unknown> = {}) {
  return render(
    <MemoryRouter
      initialEntries={[{ pathname: '/verify-email', state }]}
    >
      <Routes>
        <Route element={<EmailVerificationPage />} path="/verify-email" />
        <Route element={<p>Sign-in destination</p>} path="/login" />
      </Routes>
    </MemoryRouter>,
  )
}

describe('email verification', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('validates OTP input and displays an incorrect-code response', async () => {
    vi.mocked(confirmEmailVerification).mockRejectedValue(
      new Error('Invalid or expired verification code.'),
    )
    const user = userEvent.setup()
    renderVerification({ email: 'patient@example.com' })

    expect(screen.getByText('pa*****@example.com')).toBeTruthy()
    const code = screen.getByLabelText('Six-digit code')
    await user.type(code, '12a3456')
    expect((code as HTMLInputElement).value).toBe('123456')
    await user.click(screen.getByRole('button', { name: 'Verify email' }))
    expect(
      await screen.findByText('Invalid or expired verification code.'),
    ).toBeTruthy()
  })

  it('resends after the cooldown and navigates to sign-in after verification', async () => {
    vi.useFakeTimers()
    vi.mocked(resendVerificationEmail).mockResolvedValue()
    vi.mocked(confirmEmailVerification).mockResolvedValue()
    renderVerification({ email: 'patient@example.com' })

    const resend = screen.getByRole('button', { name: 'Resend code in 60s' })
    expect((resend as HTMLButtonElement).disabled).toBe(true)
    for (let second = 0; second < 60; second++) {
      act(() => vi.advanceTimersByTime(1000))
    }
    fireEvent.click(screen.getByRole('button', { name: 'Resend verification code' }))
    await act(async () => Promise.resolve())
    expect(resendVerificationEmail).toHaveBeenCalledWith({
      email: 'patient@example.com',
    })
    expect(
      screen.getByText(
        'If this address can be verified, a code has been sent.',
      ),
    ).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Six-digit code'), {
      target: { value: '123456' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verify email' }))
    await act(async () => Promise.resolve())
    expect(
      screen.getByText('Your email address is verified. You can now sign in.'),
    ).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Continue to sign in' }))
    expect(screen.getByText('Sign-in destination')).toBeTruthy()
  })

  it('requests a code for an existing unverified account', async () => {
    vi.mocked(sendVerificationEmail).mockResolvedValue()
    renderVerification({ email: 'legacy@example.com', autoSend: true })

    await waitFor(() => {
      expect(sendVerificationEmail).toHaveBeenCalledWith({
        email: 'legacy@example.com',
      })
    })
    expect(screen.getByText('le****@example.com')).toBeTruthy()
  })
})

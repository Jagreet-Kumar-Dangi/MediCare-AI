import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  registerPatient as registerPatientRequest,
} from '../api/auth'
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
  setUnauthorizedHandler,
} from '../api/client'
import type {
  LoginPayload,
  PatientRegistrationPayload,
  PublicUser,
} from '../types/api'
import { AuthContext, type AuthContextValue, type AuthStatus } from './context'

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<PublicUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>(() =>
    getAccessToken() ? 'loading' : 'unauthenticated',
  )
  const [restoreError, setRestoreError] = useState<string | null>(null)

  const handleUnauthorized = useCallback(() => {
    setUser(null)
    setStatus('unauthenticated')
    setRestoreError('Your session has ended. Please sign in again.')
  }, [])

  const retrySessionRestore = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null)
      setStatus('unauthenticated')
      return
    }
    setRestoreError(null)
    setStatus('loading')
    try {
      const currentUser = await getCurrentUser()
      if (currentUser.role !== 'PATIENT') {
        clearAccessToken()
        setUser(null)
        setStatus('unauthenticated')
        setRestoreError('This portal is currently available to patients.')
        return
      }
      setUser(currentUser)
      setStatus('authenticated')
    } catch (error) {
      if (getAccessToken()) {
        setRestoreError(getApiErrorMessage(error))
        setStatus('error')
      } else {
        setUser(null)
        setStatus('unauthenticated')
      }
    }
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(handleUnauthorized)
    let active = true
    if (getAccessToken()) {
      void getCurrentUser()
        .then((currentUser) => {
          if (!active) return
          if (currentUser.role !== 'PATIENT') {
            clearAccessToken()
            setUser(null)
            setStatus('unauthenticated')
            setRestoreError('This portal is currently available to patients.')
            return
          }
          setUser(currentUser)
          setStatus('authenticated')
        })
        .catch((error: unknown) => {
          if (!active) return
          if (getAccessToken()) {
            setRestoreError(getApiErrorMessage(error))
            setStatus('error')
          } else {
            setUser(null)
            setStatus('unauthenticated')
          }
        })
    }
    return () => {
      active = false
      setUnauthorizedHandler(undefined)
    }
  }, [handleUnauthorized])

  const signIn = useCallback(async (payload: LoginPayload) => {
    const tokenResponse = await loginRequest(payload)
    setAccessToken(tokenResponse.access_token)
    try {
      const currentUser = await getCurrentUser()
      if (currentUser.role !== 'PATIENT') {
        try {
          await logoutRequest()
        } finally {
          clearAccessToken()
          setUser(null)
          setStatus('unauthenticated')
        }
        throw new Error('This portal is currently available to patients.')
      }
      setUser(currentUser)
      setRestoreError(null)
      setStatus('authenticated')
    } catch (error) {
      clearAccessToken()
      setUser(null)
      setStatus('unauthenticated')
      throw error
    }
  }, [])

  const registerPatient = useCallback(
    (payload: PatientRegistrationPayload) => registerPatientRequest(payload),
    [],
  )

  const signOut = useCallback(async () => {
    await logoutRequest()
    clearAccessToken()
    setUser(null)
    setRestoreError(null)
    setStatus('unauthenticated')
  }, [])

  const value: AuthContextValue = useMemo(
    () => ({
      user,
      status,
      restoreError,
      signIn,
      registerPatient,
      signOut,
      retrySessionRestore,
    }),
    [
      user,
      status,
      restoreError,
      signIn,
      registerPatient,
      signOut,
      retrySessionRestore,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

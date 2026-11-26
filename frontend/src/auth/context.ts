import { createContext } from 'react'
import type {
  LoginPayload,
  DoctorRegistrationPayload,
  PatientRegistrationPayload,
  PublicUser,
} from '../types/api'

export type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'unauthenticated'
  | 'error'

export interface AuthContextValue {
  user: PublicUser | null
  status: AuthStatus
  restoreError: string | null
  signIn: (payload: LoginPayload) => Promise<PublicUser>
  registerPatient: (payload: PatientRegistrationPayload) => Promise<PublicUser>
  registerDoctor: (payload: DoctorRegistrationPayload) => Promise<PublicUser>
  signOut: () => Promise<void>
  retrySessionRestore: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

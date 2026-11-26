import { apiClient } from './client'
import type {
  Appointment,
  AppointmentStatus,
  AvailabilityException,
  AvailabilityExceptionPayload,
  AvailableSlotsResponse,
  DoctorAvailability,
  DoctorAvailabilityPayload,
} from '../types/api'

export type AppointmentView = 'upcoming' | 'history' | 'all'

export async function getAvailableSlots(
  doctorId: number,
  date: string,
): Promise<AvailableSlotsResponse> {
  const response = await apiClient.get<AvailableSlotsResponse>(
    '/appointments/available-slots',
    { params: { doctor_id: doctorId, date } },
  )
  return response.data
}

export async function createAppointment(payload: {
  doctor_id: number
  scheduled_start: string
  reason_for_visit: string
  patient_notes?: string
}): Promise<Appointment> {
  const response = await apiClient.post<Appointment>('/appointments', payload)
  return response.data
}

export async function getMyAppointments(
  view: AppointmentView = 'upcoming',
): Promise<Appointment[]> {
  const response = await apiClient.get<Appointment[]>('/appointments/me', {
    params: { view },
  })
  return response.data
}

export async function cancelAppointment(
  appointmentId: number,
  reason: string,
): Promise<Appointment> {
  const response = await apiClient.post<Appointment>(
    `/appointments/${appointmentId}/cancel`,
    { reason },
  )
  return response.data
}

export async function rescheduleAppointment(
  appointmentId: number,
  scheduledStart: string,
  reason: string,
): Promise<Appointment> {
  const response = await apiClient.put<Appointment>(
    `/appointments/${appointmentId}/reschedule`,
    { scheduled_start: scheduledStart, reason },
  )
  return response.data
}

export async function getDoctorAvailability(): Promise<DoctorAvailability[]> {
  const response = await apiClient.get<DoctorAvailability[]>(
    '/doctor/availability',
  )
  return response.data
}

export async function createDoctorAvailability(
  payload: DoctorAvailabilityPayload,
): Promise<DoctorAvailability> {
  const response = await apiClient.post<DoctorAvailability>(
    '/doctor/availability',
    payload,
  )
  return response.data
}

export async function deleteDoctorAvailability(
  availabilityId: number,
): Promise<void> {
  await apiClient.delete(`/doctor/availability/${availabilityId}`)
}

export async function getDoctorAvailabilityExceptions(): Promise<
  AvailabilityException[]
> {
  const response = await apiClient.get<AvailabilityException[]>(
    '/doctor/availability/exceptions',
  )
  return response.data
}

export async function createDoctorAvailabilityException(
  payload: AvailabilityExceptionPayload,
): Promise<AvailabilityException> {
  const response = await apiClient.post<AvailabilityException>(
    '/doctor/availability/exceptions',
    payload,
  )
  return response.data
}

export async function deleteDoctorAvailabilityException(
  exceptionId: number,
): Promise<void> {
  await apiClient.delete(`/doctor/availability/exceptions/${exceptionId}`)
}

export async function getDoctorAppointments(
  view: AppointmentView = 'upcoming',
): Promise<Appointment[]> {
  const response = await apiClient.get<Appointment[]>(
    '/doctor/appointments',
    { params: { view } },
  )
  return response.data
}

export async function doctorAppointmentAction(
  appointmentId: number,
  action: 'confirm' | 'complete' | 'no-show',
): Promise<Appointment> {
  const response = await apiClient.post<Appointment>(
    `/doctor/appointments/${appointmentId}/${action}`,
  )
  return response.data
}

export async function rejectDoctorAppointment(
  appointmentId: number,
  reason: string,
): Promise<Appointment> {
  const response = await apiClient.post<Appointment>(
    `/doctor/appointments/${appointmentId}/reject`,
    { reason },
  )
  return response.data
}

export async function cancelDoctorAppointment(
  appointmentId: number,
  reason: string,
): Promise<Appointment> {
  const response = await apiClient.post<Appointment>(
    `/doctor/appointments/${appointmentId}/cancel`,
    { reason },
  )
  return response.data
}

export async function updateDoctorAppointmentNotes(
  appointmentId: number,
  doctorNotes: string,
): Promise<Appointment> {
  const response = await apiClient.put<Appointment>(
    `/doctor/appointments/${appointmentId}/notes`,
    { doctor_notes: doctorNotes },
  )
  return response.data
}

export async function getAdminAppointments(
  statusFilter?: AppointmentStatus,
): Promise<Appointment[]> {
  const response = await apiClient.get<Appointment[]>('/admin/appointments', {
    params: statusFilter ? { status: statusFilter } : undefined,
  })
  return response.data
}

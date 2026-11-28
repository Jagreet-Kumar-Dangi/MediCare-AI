import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_provider.dart';
import '../domain/patient_appointment.dart';

final appointmentRepositoryProvider = Provider<AppointmentRepository>((ref) {
  return AppointmentRepository(ref.watch(dioProvider));
});

class AppointmentRepository {
  const AppointmentRepository(this._dio);

  final Dio _dio;

  Future<AvailableSlots> getAvailableSlots({
    required int doctorId,
    required String date,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/appointments/available-slots',
      queryParameters: {'doctor_id': doctorId, 'date': date},
    );
    return AvailableSlots.fromJson(response.data!);
  }

  Future<PatientAppointment> createAppointment({
    required int doctorId,
    required DateTime scheduledStart,
    required String reasonForVisit,
    String? patientNotes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/appointments',
      data: {
        'doctor_id': doctorId,
        'scheduled_start': scheduledStart.toUtc().toIso8601String(),
        'reason_for_visit': reasonForVisit.trim(),
        if (patientNotes != null && patientNotes.trim().isNotEmpty)
          'patient_notes': patientNotes.trim(),
      },
    );
    return PatientAppointment.fromJson(response.data!);
  }

  Future<List<PatientAppointment>> listMyAppointments({
    required String view,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      '/appointments/me',
      queryParameters: {'view': view},
    );
    return response.data!
        .map(
          (item) => PatientAppointment.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  Future<PatientAppointment> getAppointment(int appointmentId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/appointments/$appointmentId',
    );
    return PatientAppointment.fromJson(response.data!);
  }

  Future<PatientAppointment> rescheduleAppointment({
    required int appointmentId,
    required DateTime scheduledStart,
    required String reason,
  }) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/appointments/$appointmentId/reschedule',
      data: {
        'scheduled_start': scheduledStart.toUtc().toIso8601String(),
        'reason': reason.trim(),
      },
    );
    return PatientAppointment.fromJson(response.data!);
  }

  Future<PatientAppointment> cancelAppointment({
    required int appointmentId,
    required String reason,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/appointments/$appointmentId/cancel',
      data: {'reason': reason.trim()},
    );
    return PatientAppointment.fromJson(response.data!);
  }
}

import 'package:flutter_test/flutter_test.dart';
import 'package:medicare_ai/features/appointment/domain/patient_appointment.dart';
import 'package:medicare_ai/features/doctor/domain/doctor_profile.dart';
import 'package:medicare_ai/features/patient/domain/patient_profile.dart';
import 'package:medicare_ai/core/utils/date_time_formatters.dart';
import 'package:timezone/data/latest.dart' as timezone_data;

void main() {
  setUpAll(timezone_data.initializeTimeZones);

  test('maps supported patient profile fields including nullable values', () {
    final profile = PatientProfile.fromJson({
      'first_name': 'Sample',
      'last_name': 'Patient',
      'date_of_birth': null,
      'phone_number': null,
      'created_at': '2026-01-01T00:00:00Z',
      'updated_at': '2026-01-02T00:00:00Z',
    });

    expect(profile.firstName, 'Sample');
    expect(profile.lastName, 'Patient');
    expect(profile.dateOfBirth, isNull);
    expect(profile.phoneNumber, isNull);
  });

  test('maps public doctor response without inventing verification fields', () {
    final doctor = DoctorProfile.fromJson({
      'id': 42,
      'full_name': 'Dr Sample',
      'specialization': 'Family Medicine',
      'qualification': 'MD',
      'years_of_experience': 8,
      'clinic_or_hospital': null,
      'consultation_fee': 1250.0,
      'biography': null,
    });

    expect(doctor.id, 42);
    expect(doctor.consultationFee, '1250.0');
    expect(doctor.clinicOrHospital, isNull);
  });

  test('maps appointment and slot responses and clinic timezone correctly', () {
    final appointment = PatientAppointment.fromJson({
      'id': 7,
      'doctor': {'id': 42, 'full_name': 'Dr Sample'},
      'scheduled_start': '2026-01-01T20:00:00Z',
      'scheduled_end': '2026-01-01T20:30:00Z',
      'status': 'BOOKED',
      'reason_for_visit': 'Routine consultation',
      'patient_notes': null,
      'cancellation_reason': null,
      'rejection_reason': null,
      'created_at': '2025-12-01T00:00:00Z',
      'updated_at': '2025-12-01T00:00:00Z',
      'audit_events': [
        {
          'id': 1,
          'action': 'BOOKED',
          'reason': null,
          'previous_start': null,
          'previous_end': null,
          'new_start': '2026-01-01T20:00:00Z',
          'new_end': '2026-01-01T20:30:00Z',
          'created_at': '2025-12-01T00:00:00Z',
        },
      ],
    });
    final slots = AvailableSlots.fromJson({
      'doctor_id': 42,
      'date': '2026-01-02',
      'timezone': 'Asia/Kolkata',
      'slots': [
        {
          'scheduled_start': '2026-01-01T20:00:00Z',
          'scheduled_end': '2026-01-01T20:30:00Z',
        },
      ],
    });

    expect(appointment.canChange, isTrue);
    expect(appointment.auditEvents.single.action, 'BOOKED');
    expect(slots.slots, hasLength(1));
    expect(
      formatDateTimeInZone(slots.slots.single.scheduledStart, slots.timezone),
      '2026-01-02 at 1:30 AM (Asia/Kolkata)',
    );
  });
}

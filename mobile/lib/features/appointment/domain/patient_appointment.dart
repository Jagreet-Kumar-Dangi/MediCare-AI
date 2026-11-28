class AppointmentDoctor {
  const AppointmentDoctor({required this.id, required this.fullName});

  final int id;
  final String fullName;

  factory AppointmentDoctor.fromJson(Map<String, dynamic> json) {
    return AppointmentDoctor(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
    );
  }
}

class AppointmentAuditEvent {
  const AppointmentAuditEvent({
    required this.id,
    required this.action,
    required this.reason,
    required this.previousStart,
    required this.previousEnd,
    required this.newStart,
    required this.newEnd,
    required this.createdAt,
  });

  final int id;
  final String action;
  final String? reason;
  final DateTime? previousStart;
  final DateTime? previousEnd;
  final DateTime? newStart;
  final DateTime? newEnd;
  final DateTime createdAt;

  factory AppointmentAuditEvent.fromJson(Map<String, dynamic> json) {
    return AppointmentAuditEvent(
      id: json['id'] as int,
      action: json['action'] as String,
      reason: json['reason'] as String?,
      previousStart: _dateTimeOrNull(json['previous_start']),
      previousEnd: _dateTimeOrNull(json['previous_end']),
      newStart: _dateTimeOrNull(json['new_start']),
      newEnd: _dateTimeOrNull(json['new_end']),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class PatientAppointment {
  const PatientAppointment({
    required this.id,
    required this.doctor,
    required this.scheduledStart,
    required this.scheduledEnd,
    required this.status,
    required this.reasonForVisit,
    required this.patientNotes,
    required this.cancellationReason,
    required this.rejectionReason,
    required this.createdAt,
    required this.updatedAt,
    required this.auditEvents,
  });

  final int id;
  final AppointmentDoctor doctor;
  final DateTime scheduledStart;
  final DateTime scheduledEnd;
  final String status;
  final String reasonForVisit;
  final String? patientNotes;
  final String? cancellationReason;
  final String? rejectionReason;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<AppointmentAuditEvent> auditEvents;

  bool get canChange => status == 'BOOKED' || status == 'CONFIRMED';

  factory PatientAppointment.fromJson(Map<String, dynamic> json) {
    final events = json['audit_events'] as List<dynamic>;
    return PatientAppointment(
      id: json['id'] as int,
      doctor: AppointmentDoctor.fromJson(
        json['doctor'] as Map<String, dynamic>,
      ),
      scheduledStart: DateTime.parse(json['scheduled_start'] as String),
      scheduledEnd: DateTime.parse(json['scheduled_end'] as String),
      status: json['status'] as String,
      reasonForVisit: json['reason_for_visit'] as String,
      patientNotes: json['patient_notes'] as String?,
      cancellationReason: json['cancellation_reason'] as String?,
      rejectionReason: json['rejection_reason'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      auditEvents: events
          .map(
            (event) =>
                AppointmentAuditEvent.fromJson(event as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}

class AvailableSlot {
  const AvailableSlot({
    required this.scheduledStart,
    required this.scheduledEnd,
  });

  final DateTime scheduledStart;
  final DateTime scheduledEnd;

  factory AvailableSlot.fromJson(Map<String, dynamic> json) {
    return AvailableSlot(
      scheduledStart: DateTime.parse(json['scheduled_start'] as String),
      scheduledEnd: DateTime.parse(json['scheduled_end'] as String),
    );
  }
}

class AvailableSlots {
  const AvailableSlots({
    required this.doctorId,
    required this.date,
    required this.timezone,
    required this.slots,
  });

  final int doctorId;
  final String date;
  final String timezone;
  final List<AvailableSlot> slots;

  factory AvailableSlots.fromJson(Map<String, dynamic> json) {
    final slots = json['slots'] as List<dynamic>;
    return AvailableSlots(
      doctorId: json['doctor_id'] as int,
      date: json['date'] as String,
      timezone: json['timezone'] as String,
      slots: slots
          .map((slot) => AvailableSlot.fromJson(slot as Map<String, dynamic>))
          .toList(),
    );
  }
}

DateTime? _dateTimeOrNull(dynamic value) {
  if (value == null) return null;
  return DateTime.parse(value as String);
}

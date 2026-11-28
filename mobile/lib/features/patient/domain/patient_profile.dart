class PatientProfile {
  const PatientProfile({
    required this.firstName,
    required this.lastName,
    required this.dateOfBirth,
    required this.phoneNumber,
    required this.createdAt,
    required this.updatedAt,
  });

  final String firstName;
  final String lastName;
  final DateTime? dateOfBirth;
  final String? phoneNumber;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory PatientProfile.fromJson(Map<String, dynamic> json) {
    final dateOfBirth = json['date_of_birth'] as String?;
    return PatientProfile(
      firstName: json['first_name'] as String,
      lastName: json['last_name'] as String,
      dateOfBirth: dateOfBirth == null ? null : DateTime.parse(dateOfBirth),
      phoneNumber: json['phone_number'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

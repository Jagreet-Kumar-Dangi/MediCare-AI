class DoctorProfile {
  const DoctorProfile({
    required this.id,
    required this.fullName,
    required this.specialization,
    required this.qualification,
    required this.yearsOfExperience,
    required this.clinicOrHospital,
    required this.consultationFee,
    required this.biography,
  });

  final int id;
  final String fullName;
  final String specialization;
  final String qualification;
  final int yearsOfExperience;
  final String? clinicOrHospital;
  final String? consultationFee;
  final String? biography;

  factory DoctorProfile.fromJson(Map<String, dynamic> json) {
    return DoctorProfile(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      specialization: json['specialization'] as String,
      qualification: json['qualification'] as String,
      yearsOfExperience: json['years_of_experience'] as int,
      clinicOrHospital: json['clinic_or_hospital'] as String?,
      consultationFee: json['consultation_fee']?.toString(),
      biography: json['biography'] as String?,
    );
  }
}

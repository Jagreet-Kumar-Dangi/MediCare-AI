import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_provider.dart';
import '../domain/patient_profile.dart';

final patientRepositoryProvider = Provider<PatientRepository>((ref) {
  return PatientRepository(ref.watch(dioProvider));
});

class PatientRepository {
  const PatientRepository(this._dio);

  final Dio _dio;

  Future<PatientProfile> getMyProfile() async {
    final response = await _dio.get<Map<String, dynamic>>('/patients/me');
    return PatientProfile.fromJson(response.data!);
  }

  Future<PatientProfile> updateMyProfile({
    required String firstName,
    required String lastName,
    required String? dateOfBirth,
    required String? phoneNumber,
  }) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/patients/me',
      data: {
        'first_name': firstName,
        'last_name': lastName,
        'date_of_birth': dateOfBirth,
        'phone_number': phoneNumber,
      },
    );
    return PatientProfile.fromJson(response.data!);
  }
}

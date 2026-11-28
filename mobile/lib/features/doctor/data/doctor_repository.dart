import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_provider.dart';
import '../domain/doctor_profile.dart';

final doctorRepositoryProvider = Provider<DoctorRepository>((ref) {
  return DoctorRepository(ref.watch(dioProvider));
});

class DoctorRepository {
  const DoctorRepository(this._dio);

  final Dio _dio;

  Future<List<DoctorProfile>> listDoctors({
    String? search,
    String? specialization,
    int? minExperience,
    int? maxExperience,
    String? maxConsultationFee,
  }) async {
    final trimmedSearch = search?.trim();
    final trimmedSpecialization = specialization?.trim();
    final trimmedMaxFee = maxConsultationFee?.trim();
    final query = <String, dynamic>{
      if (trimmedSearch?.isNotEmpty ?? false) 'search': trimmedSearch,
      if (trimmedSpecialization?.isNotEmpty ?? false)
        'specialization': trimmedSpecialization,
      'min_experience': ?minExperience,
      'max_experience': ?maxExperience,
      if (trimmedMaxFee?.isNotEmpty ?? false)
        'max_consultation_fee': trimmedMaxFee,
      'limit': 100,
      'offset': 0,
    };
    final response = await _dio.get<List<dynamic>>(
      '/doctors',
      queryParameters: query,
    );
    return response.data!
        .map((item) => DoctorProfile.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<DoctorProfile> getDoctor(int doctorId) async {
    final response = await _dio.get<Map<String, dynamic>>('/doctors/$doctorId');
    return DoctorProfile.fromJson(response.data!);
  }
}

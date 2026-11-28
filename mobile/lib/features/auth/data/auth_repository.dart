import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_provider.dart';
import '../domain/app_user.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(dioProvider));
});

class AuthRepository {
  const AuthRepository(this._dio);

  final Dio _dio;

  Future<String> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return response.data!['access_token'] as String;
  }

  Future<AppUser> currentUser() async {
    final response = await _dio.get<Map<String, dynamic>>('/auth/me');
    return AppUser.fromJson(response.data!);
  }

  Future<AppUser> registerPatient({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/register/patient',
      data: {
        'email': email,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
      },
    );
    return AppUser.fromJson(response.data!);
  }

  Future<AppUser> registerDoctor(Map<String, dynamic> request) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/register/doctor',
      data: request,
    );
    return AppUser.fromJson(response.data!);
  }

  Future<void> sendVerificationEmail({required String email}) async {
    await _dio.post<void>(
      '/auth/verify-email/send',
      data: {'email': email},
    );
  }

  Future<void> resendVerificationEmail({required String email}) async {
    await _dio.post<void>(
      '/auth/verify-email/resend',
      data: {'email': email},
    );
  }

  Future<void> confirmEmailVerification({
    required String email,
    required String code,
  }) async {
    await _dio.post<void>(
      '/auth/verify-email/confirm',
      data: {'email': email, 'code': code},
    );
  }

  Future<void> logout() async {
    await _dio.post<void>('/auth/logout');
  }
}

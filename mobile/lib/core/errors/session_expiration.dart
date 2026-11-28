import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/presentation/auth_controller.dart';

Future<void> handleSessionExpiration(WidgetRef ref, Object error) async {
  if (error is DioException && error.response?.statusCode == 401) {
    await ref.read(authControllerProvider.notifier).handleExpiredSession();
  }
}

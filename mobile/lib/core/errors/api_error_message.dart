import 'package:dio/dio.dart';

String apiErrorMessage(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map<String, dynamic> && data['detail'] is String) {
      return data['detail'] as String;
    }
    if (error.response == null) {
      return 'Unable to reach MediCare AI. Check your connection and try again.';
    }
    if (error.response?.statusCode == 422) {
      return 'Please check the information you entered and try again.';
    }
    return 'Something went wrong. Please try again.';
  }
  if (error is StateError) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

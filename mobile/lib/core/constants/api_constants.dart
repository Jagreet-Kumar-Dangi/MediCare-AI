abstract final class ApiConstants {
  static const baseUrl = String.fromEnvironment(
    'MEDICARE_API_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static const requestTimeout = Duration(seconds: 15);
}

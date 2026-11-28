import 'package:timezone/timezone.dart' as timezone;

String formatDate(DateTime value) {
  return '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';
}

String formatDateTimeInZone(DateTime value, String zoneName) {
  final zone = timezone.getLocation(zoneName);
  final local = timezone.TZDateTime.from(value.toUtc(), zone);
  final date = formatDate(local);
  final hour = local.hour % 12 == 0 ? 12 : local.hour % 12;
  final minute = local.minute.toString().padLeft(2, '0');
  final period = local.hour < 12 ? 'AM' : 'PM';
  return '$date at $hour:$minute $period ($zoneName)';
}

String formatTimeInZone(DateTime value, String zoneName) {
  final zone = timezone.getLocation(zoneName);
  final local = timezone.TZDateTime.from(value.toUtc(), zone);
  final hour = local.hour % 12 == 0 ? 12 : local.hour % 12;
  final minute = local.minute.toString().padLeft(2, '0');
  final period = local.hour < 12 ? 'AM' : 'PM';
  return '$hour:$minute $period';
}

String localDateString(DateTime date) {
  return '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';
}

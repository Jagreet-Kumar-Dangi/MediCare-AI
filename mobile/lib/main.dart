import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timezone/data/latest.dart' as timezone_data;

import 'app/medicare_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  timezone_data.initializeTimeZones();
  runApp(const ProviderScope(child: MedicareApp()));
}

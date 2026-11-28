import 'package:material_ui/material_ui.dart';

abstract final class AppTheme {
  static const teal = Color(0xFF087F8C);
  static const ink = Color(0xFF18343A);
  static const muted = Color(0xFF62777C);
  static const canvas = Color(0xFFF5FAFA);

  static final light = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: teal,
      primary: teal,
      surface: Colors.white,
      error: const Color(0xFFB3261E),
    ),
    scaffoldBackgroundColor: canvas,
    textTheme: const TextTheme(
      headlineMedium: TextStyle(
        color: ink,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.5,
      ),
      titleLarge: TextStyle(color: ink, fontWeight: FontWeight.w700),
      titleMedium: TextStyle(color: ink, fontWeight: FontWeight.w600),
      bodyLarge: TextStyle(color: muted, height: 1.45),
      bodyMedium: TextStyle(color: ink, height: 1.4),
      labelLarge: TextStyle(fontWeight: FontWeight.w600),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Color(0xFFDCE7E8)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Color(0xFFDCE7E8)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: teal, width: 1.6),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Color(0xFFB3261E)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: Color(0xFFE6EEEE)),
      ),
    ),
  );
}

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/email_verification_screen.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/auth/presentation/registration_screen.dart';
import '../features/appointment/presentation/appointment_detail_screen.dart';
import '../features/appointment/presentation/patient_appointments_screen.dart';
import '../features/dashboard/presentation/dashboard_screen.dart';
import '../features/doctor/presentation/doctor_detail_screen.dart';
import '../features/doctor/presentation/doctor_directory_screen.dart';
import '../features/profile/presentation/profile_screen.dart';
import 'splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _RouterRefresh(ref);
  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      final location = state.matchedLocation;
      const publicRoutes = <String>{
        '/login',
        '/register/patient',
        '/register/doctor',
        '/verify-email',
      };

      if (auth.isInitializing) {
        return location == '/splash' ? null : '/splash';
      }

      final user = auth.user;
      if (user == null) {
        return publicRoutes.contains(location) ? null : '/login';
      }

      final home = user.isDoctor ? '/doctor' : '/patient';
      final patientFeatureRoute =
          location == '/doctors' ||
          location.startsWith('/doctors/') ||
          location == '/appointments' ||
          location.startsWith('/appointments/');
      if (user.role == 'ADMIN') {
        return '/login';
      }
      if (user.isDoctor && patientFeatureRoute) {
        return home;
      }
      if (publicRoutes.contains(location) ||
          location == '/splash' ||
          (location == '/patient' && user.isDoctor) ||
          (location == '/doctor' && !user.isDoctor)) {
        return home;
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/register/patient',
        builder: (context, state) =>
            const RegistrationScreen(role: RegistrationRole.patient),
      ),
      GoRoute(
        path: '/register/doctor',
        builder: (context, state) =>
            const RegistrationScreen(role: RegistrationRole.doctor),
      ),
      GoRoute(
        path: '/verify-email',
        builder: (context, state) {
          final extra = state.extra;
          final values = extra is Map<String, Object?> ? extra : const {};
          return EmailVerificationScreen(
            email: values['email'] as String?,
            autoSend: values['autoSend'] as bool? ?? false,
            initialMessage: values['initialMessage'] as String?,
          );
        },
      ),
      GoRoute(
        path: '/patient',
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: '/doctor',
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/doctors',
        builder: (context, state) => const DoctorDirectoryScreen(),
      ),
      GoRoute(
        path: '/doctors/:doctorId',
        builder: (context, state) => DoctorDetailScreen(
          doctorId: int.tryParse(state.pathParameters['doctorId'] ?? '') ?? -1,
        ),
      ),
      GoRoute(
        path: '/appointments',
        builder: (context, state) => const PatientAppointmentsScreen(),
      ),
      GoRoute(
        path: '/appointments/:appointmentId',
        builder: (context, state) => AppointmentDetailScreen(
          appointmentId:
              int.tryParse(state.pathParameters['appointmentId'] ?? '') ?? -1,
        ),
      ),
    ],
  );
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });
  return router;
});

class _RouterRefresh extends ChangeNotifier {
  _RouterRefresh(Ref ref) {
    ref.listen(authControllerProvider, (previous, next) {
      notifyListeners();
    });
  }
}

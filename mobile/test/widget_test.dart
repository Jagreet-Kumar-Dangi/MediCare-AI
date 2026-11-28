import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:medicare_ai/features/auth/data/auth_repository.dart';
import 'package:medicare_ai/features/auth/presentation/email_verification_screen.dart';
import 'package:medicare_ai/app/medicare_app.dart';
import 'package:medicare_ai/core/storage/secure_token_storage.dart';

void main() {
  testWidgets('shows sign-in and password visibility controls', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(_MemoryTokenStorage()),
        ],
        child: const MedicareApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('MediCare AI'), findsOneWidget);
    expect(find.text('Email address'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsNWidgets(2));
    expect(find.text('Create a patient account'), findsOneWidget);
    expect(find.text('Register as a doctor'), findsOneWidget);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();
    expect(find.byTooltip('Hide password'), findsOneWidget);

    final patientLink = find.text('Create a patient account');
    await tester.ensureVisible(patientLink);
    await tester.tap(patientLink);
    await tester.pumpAndSettle();
    expect(find.text('First name'), findsOneWidget);
    expect(find.text('Last name'), findsOneWidget);

    await tester.tap(find.byTooltip('Back'));
    await tester.pumpAndSettle();
    final doctorLink = find.text('Register as a doctor');
    await tester.ensureVisible(doctorLink);
    await tester.tap(doctorLink);
    await tester.pumpAndSettle();
    expect(find.text('Full name'), findsOneWidget);
    expect(find.text('Medical registration number'), findsOneWidget);
  });

  testWidgets('requires a six-digit OTP and displays server rejection', (
    tester,
  ) async {
    final repository = _FakeAuthRepository(rejectCode: true);
    await _pumpVerification(tester, repository);

    await tester.ensureVisible(find.text('Verify email'));
    await tester.tap(find.text('Verify email'));
    await tester.pumpAndSettle();
    expect(find.text('Enter the six-digit verification code.'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).last, '123456');
    await tester.ensureVisible(find.text('Verify email'));
    await tester.tap(find.text('Verify email'));
    await tester.pumpAndSettle();
    expect(find.text('Invalid or expired verification code.'), findsOneWidget);
  });

  testWidgets('resend observes cooldown and verified user returns to login', (
    tester,
  ) async {
    final repository = _FakeAuthRepository();
    final router = _verificationRouter();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Resend code in 60s'), findsOneWidget);
    await tester.pump(const Duration(seconds: 60));
    expect(find.text('Resend verification code'), findsOneWidget);
    await tester.ensureVisible(find.text('Resend verification code'));
    await tester.tap(find.text('Resend verification code'));
    await tester.pump();
    expect(repository.resendCalls, 1);
    expect(find.text('Resend code in 60s'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).last, '123456');
    await tester.ensureVisible(find.text('Verify email'));
    await tester.tap(find.text('Verify email'));
    await tester.pumpAndSettle();
    expect(find.text('Email verified'), findsOneWidget);
    await tester.tap(find.text('Continue to sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Login destination'), findsOneWidget);
    router.dispose();
  });
}

Future<void> _pumpVerification(
  WidgetTester tester,
  _FakeAuthRepository repository,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repository)],
      child: MaterialApp.router(routerConfig: _verificationRouter()),
    ),
  );
  await tester.pumpAndSettle();
}

GoRouter _verificationRouter() => GoRouter(
  initialLocation: '/verify-email',
  routes: [
    GoRoute(
      path: '/verify-email',
      builder: (context, state) =>
          const EmailVerificationScreen(email: 'patient@example.com'),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) =>
          const Scaffold(body: Center(child: Text('Login destination'))),
    ),
  ],
);

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.rejectCode = false}) : super(Dio());

  final bool rejectCode;
  int resendCalls = 0;

  @override
  Future<void> resendVerificationEmail({required String email}) async {
    resendCalls++;
  }

  @override
  Future<void> confirmEmailVerification({
    required String email,
    required String code,
  }) async {
    if (rejectCode) {
      throw DioException(
        requestOptions: RequestOptions(path: '/auth/verify-email/confirm'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/verify-email/confirm'),
          statusCode: 400,
          data: {'detail': 'Invalid or expired verification code.'},
        ),
      );
    }
  }
}

class _MemoryTokenStorage implements TokenStorage {
  String? _token;

  @override
  Future<void> delete() async => _token = null;

  @override
  Future<String?> read() async => _token;

  @override
  Future<void> write(String token) async => _token = token;
}

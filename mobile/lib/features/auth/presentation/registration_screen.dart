import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/widgets/brand_mark.dart';
import 'auth_controller.dart';

enum RegistrationRole { patient, doctor }

class RegistrationScreen extends ConsumerStatefulWidget {
  const RegistrationScreen({super.key, required this.role});

  final RegistrationRole role;

  @override
  ConsumerState<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends ConsumerState<RegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _fullName = TextEditingController();
  final _specialization = TextEditingController();
  final _qualification = TextEditingController();
  final _registrationNumber = TextEditingController();
  final _experience = TextEditingController(text: '0');
  final _phone = TextEditingController();
  final _clinic = TextEditingController();
  final _fee = TextEditingController();
  final _biography = TextEditingController();
  bool _obscurePassword = true;

  bool get _isDoctor => widget.role == RegistrationRole.doctor;

  @override
  void dispose() {
    for (final controller in [
      _email,
      _password,
      _firstName,
      _lastName,
      _fullName,
      _specialization,
      _qualification,
      _registrationNumber,
      _experience,
      _phone,
      _clinic,
      _fee,
      _biography,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  String? _required(String? value) =>
      (value ?? '').trim().isEmpty ? 'This field is required.' : null;

  String? _emailValidator(String? value) {
    final email = value?.trim() ?? '';
    return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)
        ? null
        : 'Enter a valid email address.';
  }

  String? _passwordValidator(String? value) {
    if ((value ?? '').trim().isEmpty) {
      return 'Password must contain a non-whitespace character.';
    }
    if (value!.length < 12 || value.length > 128) {
      return 'Use a password between 12 and 128 characters.';
    }
    return null;
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      final auth = ref.read(authControllerProvider.notifier);
      if (_isDoctor) {
        final request = <String, dynamic>{
          'email': _email.text.trim(),
          'password': _password.text,
          'full_name': _fullName.text.trim(),
          'specialization': _specialization.text.trim(),
          'qualification': _qualification.text.trim(),
          'medical_registration_number': _registrationNumber.text.trim(),
          'years_of_experience': int.parse(_experience.text.trim()),
          if (_phone.text.trim().isNotEmpty) 'phone_number': _phone.text.trim(),
          if (_clinic.text.trim().isNotEmpty)
            'clinic_or_hospital': _clinic.text.trim(),
          if (_fee.text.trim().isNotEmpty) 'consultation_fee': _fee.text.trim(),
          if (_biography.text.trim().isNotEmpty)
            'biography': _biography.text.trim(),
        };
        await auth.registerDoctor(request);
      } else {
        await auth.registerPatient(
          email: _email.text.trim(),
          password: _password.text,
          firstName: _firstName.text.trim(),
          lastName: _lastName.text.trim(),
        );
      }
      if (!mounted) return;
      context.go(
        '/verify-email',
        extra: {'email': _email.text.trim()},
      );
    } catch (error) {
      if (!mounted) return;
      if (error is DioException &&
          (error.response?.statusCode == 429 ||
              error.response?.statusCode == 503)) {
        context.go(
          '/verify-email',
          extra: {
            'email': _email.text.trim(),
            'initialMessage': apiErrorMessage(error),
          },
        );
        return;
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
    }
  }

  Widget _textField(
    TextEditingController controller,
    String label, {
    String? Function(String?)? validator,
    TextInputType? keyboardType,
    int maxLines = 1,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      maxLines: maxLines,
      decoration: InputDecoration(labelText: label),
      validator: validator,
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(_isDoctor ? 'Doctor registration' : 'Patient registration'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: BrandMark(size: 52)),
                    const SizedBox(height: 14),
                    Text(
                      _isDoctor
                          ? 'Create your doctor account'
                          : 'Create your patient account',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 22),
                    if (_isDoctor) ...[
                      _textField(_fullName, 'Full name', validator: _required),
                      const SizedBox(height: 14),
                      _textField(
                        _specialization,
                        'Specialization',
                        validator: _required,
                      ),
                      const SizedBox(height: 14),
                      _textField(
                        _qualification,
                        'Qualification',
                        validator: _required,
                      ),
                      const SizedBox(height: 14),
                      _textField(
                        _registrationNumber,
                        'Medical registration number',
                        validator: _required,
                      ),
                      const SizedBox(height: 14),
                      _textField(
                        _experience,
                        'Years of experience',
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          final years = int.tryParse((value ?? '').trim());
                          if (years == null || years < 0 || years > 80) {
                            return 'Enter a number from 0 to 80.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      _textField(
                        _phone,
                        'Phone number (optional)',
                        keyboardType: TextInputType.phone,
                      ),
                      const SizedBox(height: 14),
                      _textField(_clinic, 'Clinic or hospital (optional)'),
                      const SizedBox(height: 14),
                      _textField(
                        _fee,
                        'Consultation fee (optional)',
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        validator: (value) {
                          if ((value ?? '').trim().isEmpty) return null;
                          final fee = num.tryParse(value!.trim());
                          if (fee == null || fee < 0 || fee > 99999999.99) {
                            return 'Enter a valid non-negative fee.';
                          }
                          if (value.contains('.') &&
                              value.split('.').last.length > 2) {
                            return 'Use no more than 2 decimal places.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      _textField(
                        _biography,
                        'Biography (optional)',
                        maxLines: 3,
                      ),
                    ] else ...[
                      _textField(
                        _firstName,
                        'First name',
                        validator: _required,
                      ),
                      const SizedBox(height: 14),
                      _textField(_lastName, 'Last name', validator: _required),
                    ],
                    const SizedBox(height: 14),
                    _textField(
                      _email,
                      'Email address',
                      keyboardType: TextInputType.emailAddress,
                      validator: _emailValidator,
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: 'Password (at least 12 characters)',
                        suffixIcon: IconButton(
                          tooltip: _obscurePassword
                              ? 'Show password'
                              : 'Hide password',
                          onPressed: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                        ),
                      ),
                      validator: _passwordValidator,
                    ),
                    const SizedBox(height: 22),
                    FilledButton(
                      onPressed: auth.isBusy ? null : _register,
                      child: auth.isBusy
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Create account'),
                    ),
                    const SizedBox(height: 10),
                    TextButton(
                      onPressed: () => context.go('/login'),
                      child: const Text('I already have an account'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

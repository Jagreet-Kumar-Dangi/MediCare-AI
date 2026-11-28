import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/errors/session_expiration.dart';
import '../../../core/utils/date_time_formatters.dart';
import '../../../core/widgets/async_states.dart';
import '../../../features/auth/presentation/auth_controller.dart';
import '../../patient/data/patient_repository.dart';
import '../../patient/domain/patient_profile.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _phoneNumber = TextEditingController();
  PatientProfile? _profile;
  DateTime? _dateOfBirth;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    if (ref.read(authControllerProvider).user?.role == 'PATIENT') {
      Future.microtask(_loadProfile);
    } else {
      _loading = false;
    }
  }

  @override
  void dispose() {
    _firstName.dispose();
    _lastName.dispose();
    _phoneNumber.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    if (ref.read(authControllerProvider).user?.role != 'PATIENT') return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final profile = await ref.read(patientRepositoryProvider).getMyProfile();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _firstName.text = profile.firstName;
        _lastName.text = profile.lastName;
        _phoneNumber.text = profile.phoneNumber ?? '';
        _dateOfBirth = profile.dateOfBirth;
      });
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (!mounted) return;
      setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickDateOfBirth() async {
    final today = DateTime.now();
    final initial =
        _dateOfBirth ?? DateTime(today.year - 18, today.month, today.day);
    final selected = await showDatePicker(
      context: context,
      initialDate: initial.isAfter(today) ? today : initial,
      firstDate: DateTime(1900),
      lastDate: today,
      helpText: 'Select date of birth',
    );
    if (selected != null && mounted) {
      setState(() {
        _dateOfBirth = DateTime(selected.year, selected.month, selected.day);
        _notice = null;
      });
    }
  }

  String? _validateName(String? value, String label) {
    final name = value?.trim() ?? '';
    if (name.isEmpty) return '$label is required.';
    if (name.length > 100) return '$label must be 100 characters or fewer.';
    return null;
  }

  String? _validatePhone(String? value) {
    final phone = value?.trim() ?? '';
    if (phone.isEmpty) return null;
    if (phone.length < 7 ||
        phone.length > 32 ||
        !RegExp(r'^\+?[0-9][0-9 ().-]*$').hasMatch(phone)) {
      return 'Enter a phone number with 7–32 valid characters.';
    }
    return null;
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
      _notice = null;
    });
    try {
      final profile = await ref
          .read(patientRepositoryProvider)
          .updateMyProfile(
            firstName: _firstName.text.trim(),
            lastName: _lastName.text.trim(),
            dateOfBirth: _dateOfBirth == null
                ? null
                : localDateString(_dateOfBirth!),
            phoneNumber: _phoneNumber.text.trim().isEmpty
                ? null
                : _phoneNumber.text.trim(),
          );
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _firstName.text = profile.firstName;
        _lastName.text = profile.lastName;
        _phoneNumber.text = profile.phoneNumber ?? '';
        _dateOfBirth = profile.dateOfBirth;
        _notice = 'Profile saved.';
      });
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (!mounted) return;
      setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).user!;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: RefreshIndicator(
        onRefresh: _loadProfile,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Account',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    _AccountRow(label: 'Email', value: user.email),
                    _AccountRow(label: 'Role', value: user.role),
                    _AccountRow(
                      label: 'Status',
                      value: user.isActive ? 'Active' : 'Inactive',
                    ),
                    _AccountRow(
                      label: 'Member since',
                      value: formatDate(user.createdAt),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (user.role != 'PATIENT')
              const EmptyPanel(
                title: 'Patient details unavailable',
                message: 'Patient profile details are only available for patient accounts.',
                icon: Icons.person_outline,
              )
            else if (_loading && _profile == null)
              const LoadingCards(count: 2)
            else if (_error != null && _profile == null)
              ErrorPanel(message: _error!, onRetry: _loadProfile)
            else
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'Patient details',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Only the fields supported by your profile API are shown.',
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          _MessageBanner(message: _error!, isError: true),
                        ],
                        if (_notice != null) ...[
                          const SizedBox(height: 12),
                          _MessageBanner(message: _notice!, isError: false),
                        ],
                        const SizedBox(height: 18),
                        TextFormField(
                          controller: _firstName,
                          textCapitalization: TextCapitalization.words,
                          maxLength: 100,
                          decoration: const InputDecoration(
                            labelText: 'First name',
                          ),
                          validator: (value) =>
                              _validateName(value, 'First name'),
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _lastName,
                          textCapitalization: TextCapitalization.words,
                          maxLength: 100,
                          decoration: const InputDecoration(
                            labelText: 'Last name',
                          ),
                          validator: (value) =>
                              _validateName(value, 'Last name'),
                        ),
                        const SizedBox(height: 14),
                        Semantics(
                          button: true,
                          label: 'Date of birth',
                          value: _dateOfBirth == null
                              ? 'Not set'
                              : formatDate(_dateOfBirth!),
                          child: OutlinedButton.icon(
                            onPressed: _pickDateOfBirth,
                            icon: const Icon(Icons.calendar_month_outlined),
                            label: Text(
                              _dateOfBirth == null
                                  ? 'Date of birth (optional)'
                                  : 'Date of birth: ${formatDate(_dateOfBirth!)}',
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: _dateOfBirth == null
                              ? null
                              : () => setState(() {
                                  _dateOfBirth = null;
                                  _notice = null;
                                }),
                          child: const Text('Clear date of birth'),
                        ),
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _phoneNumber,
                          keyboardType: TextInputType.phone,
                          maxLength: 32,
                          decoration: const InputDecoration(
                            labelText: 'Phone number (optional)',
                          ),
                          validator: _validatePhone,
                        ),
                        const SizedBox(height: 16),
                        FilledButton(
                          onPressed: _saving || _loading ? null : _saveProfile,
                          child: _saving
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text('Save profile'),
                        ),
                        if (_profile != null) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Last updated ${formatDate(_profile!.updatedAt)}',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: () => context.go('/patient'),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Back to dashboard'),
            ),
          ],
        ),
      ),
    );
  }
}

class _AccountRow extends StatelessWidget {
  const _AccountRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 108,
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class _MessageBanner extends StatelessWidget {
  const _MessageBanner({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError
        ? Theme.of(context).colorScheme.error
        : const Color(0xFF176B43);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(message, style: TextStyle(color: color)),
    );
  }
}

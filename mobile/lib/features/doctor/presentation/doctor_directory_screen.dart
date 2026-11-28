import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/errors/session_expiration.dart';
import '../../../core/widgets/async_states.dart';
import '../data/doctor_repository.dart';
import '../domain/doctor_profile.dart';

class DoctorDirectoryScreen extends ConsumerStatefulWidget {
  const DoctorDirectoryScreen({super.key});

  @override
  ConsumerState<DoctorDirectoryScreen> createState() =>
      _DoctorDirectoryScreenState();
}

class _DoctorDirectoryScreenState extends ConsumerState<DoctorDirectoryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _search = TextEditingController();
  final _specialization = TextEditingController();
  final _minExperience = TextEditingController();
  final _maxExperience = TextEditingController();
  final _maxFee = TextEditingController();
  List<DoctorProfile> _doctors = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadDoctors);
  }

  @override
  void dispose() {
    _search.dispose();
    _specialization.dispose();
    _minExperience.dispose();
    _maxExperience.dispose();
    _maxFee.dispose();
    super.dispose();
  }

  int? _intOrNull(String value) =>
      value.trim().isEmpty ? null : int.tryParse(value.trim());

  String? _validateExperience(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return null;
    final number = int.tryParse(text);
    if (number == null || number < 0 || number > 80) {
      return 'Enter a whole number from 0 to 80.';
    }
    return null;
  }

  String? _validateFee(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return null;
    final fee = num.tryParse(text);
    if (fee == null || fee < 0) return 'Enter a valid non-negative fee.';
    return null;
  }

  Future<void> _loadDoctors() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final doctors = await ref
          .read(doctorRepositoryProvider)
          .listDoctors(
            search: _search.text,
            specialization: _specialization.text,
            minExperience: _intOrNull(_minExperience.text),
            maxExperience: _intOrNull(_maxExperience.text),
            maxConsultationFee: _maxFee.text,
          );
      if (mounted) setState(() => _doctors = doctors);
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitFilters() async {
    if (!_formKey.currentState!.validate()) return;
    final minimum = _intOrNull(_minExperience.text);
    final maximum = _intOrNull(_maxExperience.text);
    if (minimum != null && maximum != null && minimum > maximum) {
      setState(
        () => _error = 'Minimum experience cannot exceed maximum experience.',
      );
      return;
    }
    await _loadDoctors();
  }

  void _clearFilters() {
    _search.clear();
    _specialization.clear();
    _minExperience.clear();
    _maxExperience.clear();
    _maxFee.clear();
    _loadDoctors();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Find a doctor'),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.push('/profile'),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadDoctors,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Verified care, matched to you',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Results are limited to doctors the server marks approved, active, '
              'and eligible with required credentials.',
            ),
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Search and filters',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _search,
                        textInputAction: TextInputAction.search,
                        onFieldSubmitted: (_) => _submitFilters(),
                        maxLength: 100,
                        decoration: const InputDecoration(
                          labelText: 'Doctor name or specialty',
                          prefixIcon: Icon(Icons.search),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _specialization,
                        maxLength: 120,
                        decoration: const InputDecoration(
                          labelText: 'Specialization',
                          prefixIcon: Icon(Icons.medical_services_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _minExperience,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Min experience',
                                suffixText: 'years',
                              ),
                              validator: _validateExperience,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _maxExperience,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Max experience',
                                suffixText: 'years',
                              ),
                              validator: _validateExperience,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _maxFee,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Maximum consultation fee',
                          prefixIcon: Icon(Icons.currency_rupee),
                        ),
                        validator: _validateFee,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          FilledButton.icon(
                            onPressed: _loading ? null : _submitFilters,
                            icon: const Icon(Icons.search),
                            label: const Text('Search'),
                          ),
                          OutlinedButton(
                            onPressed: _loading ? null : _clearFilters,
                            child: const Text('Clear filters'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 18),
            if (_error != null) ...[
              ErrorPanel(message: _error!, onRetry: _loadDoctors),
              const SizedBox(height: 12),
            ],
            if (_loading)
              const LoadingCards()
            else if (_error == null && _doctors.isEmpty)
              const EmptyPanel(
                title: 'No eligible doctors found',
                message:
                    'Try another search or check back later. Doctors who are '
                    'pending, rejected, suspended, inactive, or missing required '
                    'credentials are not shown.',
                icon: Icons.search_off,
              )
            else
              for (final doctor in _doctors) ...[
                _DoctorCard(
                  doctor: doctor,
                  onTap: () => context.push('/doctors/${doctor.id}'),
                ),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _DoctorCard extends StatelessWidget {
  const _DoctorCard({required this.doctor, required this.onTap});

  final DoctorProfile doctor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircleAvatar(
                  backgroundColor: Color(0xFFE2F3F3),
                  child: Icon(Icons.medical_services_outlined),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    doctor.fullName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              doctor.specialization,
              style: const TextStyle(
                color: Color(0xFF087F8C),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${doctor.qualification} · ${doctor.yearsOfExperience} years experience',
            ),
            if (doctor.clinicOrHospital != null) ...[
              const SizedBox(height: 4),
              Text(doctor.clinicOrHospital!),
            ],
            if (doctor.consultationFee != null) ...[
              const SizedBox(height: 4),
              Text('Consultation fee: ${doctor.consultationFee}'),
            ],
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onTap,
              icon: const Icon(Icons.arrow_forward),
              label: const Text('View profile and availability'),
            ),
          ],
        ),
      ),
    );
  }
}

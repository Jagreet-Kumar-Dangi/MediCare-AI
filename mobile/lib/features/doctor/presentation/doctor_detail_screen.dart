import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/errors/session_expiration.dart';
import '../../../core/utils/date_time_formatters.dart';
import '../../../core/widgets/async_states.dart';
import '../../../features/auth/presentation/auth_controller.dart';
import '../../appointment/data/appointment_repository.dart';
import '../../appointment/domain/patient_appointment.dart';
import '../data/doctor_repository.dart';
import '../domain/doctor_profile.dart';

class DoctorDetailScreen extends ConsumerStatefulWidget {
  const DoctorDetailScreen({super.key, required this.doctorId});

  final int doctorId;

  @override
  ConsumerState<DoctorDetailScreen> createState() => _DoctorDetailScreenState();
}

class _DoctorDetailScreenState extends ConsumerState<DoctorDetailScreen> {
  final _formKey = GlobalKey<FormState>();
  final _visitReason = TextEditingController();
  final _patientNotes = TextEditingController();
  DoctorProfile? _doctor;
  AvailableSlots? _available;
  DateTime _date = DateTime.now().add(const Duration(days: 7));
  DateTime? _selectedStart;
  bool _loading = true;
  bool _slotsLoading = false;
  bool _booking = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadDoctor);
  }

  @override
  void dispose() {
    _visitReason.dispose();
    _patientNotes.dispose();
    super.dispose();
  }

  Future<void> _loadDoctor() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final doctor = await ref
          .read(doctorRepositoryProvider)
          .getDoctor(widget.doctorId);
      if (!mounted) return;
      setState(() => _doctor = doctor);
      if (ref.read(authControllerProvider).user?.role == 'PATIENT') {
        await _loadSlots();
      }
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadSlots({bool clearError = true}) async {
    final doctor = _doctor;
    if (doctor == null) return;
    setState(() {
      _slotsLoading = true;
      if (clearError) _error = null;
      _available = null;
      _selectedStart = null;
    });
    final requestedDate = localDateString(_date);
    try {
      final slots = await ref
          .read(appointmentRepositoryProvider)
          .getAvailableSlots(doctorId: doctor.id, date: requestedDate);
      if (mounted && localDateString(_date) == requestedDate) {
        setState(() => _available = slots);
      }
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (mounted && clearError) {
        setState(() => _error = apiErrorMessage(error));
      }
    } finally {
      if (mounted) setState(() => _slotsLoading = false);
    }
  }

  Future<void> _pickDate() async {
    final today = DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: _date.isBefore(today) ? today : _date,
      firstDate: DateTime(today.year, today.month, today.day),
      lastDate: DateTime(today.year, today.month, today.day + 90),
      helpText: 'Choose appointment date',
    );
    if (selected == null || !mounted) return;
    setState(() {
      _date = DateTime(selected.year, selected.month, selected.day);
      _error = null;
    });
    await _loadSlots();
  }

  String? _validateReason(String? value) {
    final reason = (value ?? '').trim();
    if (reason.isEmpty) return 'Reason for visit is required.';
    if (reason.length > 1000) return 'Use 1000 characters or fewer.';
    return null;
  }

  String? _validateNotes(String? value) {
    if ((value ?? '').length > 4000) return 'Use 4000 characters or fewer.';
    return null;
  }

  Future<void> _bookAppointment() async {
    if (!_formKey.currentState!.validate() ||
        _selectedStart == null ||
        _booking) {
      return;
    }
    final doctor = _doctor;
    if (doctor == null) return;
    setState(() {
      _booking = true;
      _error = null;
    });
    try {
      final appointment = await ref
          .read(appointmentRepositoryProvider)
          .createAppointment(
            doctorId: doctor.id,
            scheduledStart: _selectedStart!,
            reasonForVisit: _visitReason.text.trim(),
            patientNotes: _patientNotes.text.trim(),
          );
      if (!mounted) return;
      context.push('/appointments/${appointment.id}');
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (!mounted) return;
      setState(() => _error = apiErrorMessage(error));
      await _loadSlots(clearError: false);
    } finally {
      if (mounted) setState(() => _booking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).user!;
    final doctor = _doctor;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Doctor details'),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.push('/profile'),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadDoctor,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            if (_loading && doctor == null)
              const LoadingCards(count: 2)
            else if (_error != null && doctor == null)
              ErrorPanel(message: _error!, onRetry: _loadDoctor)
            else if (doctor != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const CircleAvatar(
                        radius: 28,
                        backgroundColor: Color(0xFFE2F3F3),
                        child: Icon(Icons.medical_services_outlined, size: 28),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        doctor.fullName,
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        doctor.specialization,
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(color: const Color(0xFF087F8C)),
                      ),
                      const SizedBox(height: 18),
                      _DoctorDetailRow(
                        label: 'Qualification',
                        value: doctor.qualification,
                      ),
                      _DoctorDetailRow(
                        label: 'Experience',
                        value: '${doctor.yearsOfExperience} years',
                      ),
                      if (doctor.clinicOrHospital != null)
                        _DoctorDetailRow(
                          label: 'Clinic or hospital',
                          value: doctor.clinicOrHospital!,
                        ),
                      if (doctor.consultationFee != null)
                        _DoctorDetailRow(
                          label: 'Consultation fee',
                          value: doctor.consultationFee!,
                        ),
                      if (doctor.biography != null) ...[
                        const Divider(height: 26),
                        Text(
                          'About',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        Text(doctor.biography!),
                      ],
                      const SizedBox(height: 14),
                      const Text(
                        'This profile was returned by the eligible doctor directory.',
                        style: TextStyle(color: Color(0xFF176B43)),
                      ),
                    ],
                  ),
                ),
              ),
              if (user.role == 'PATIENT') ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            'Request an appointment',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'The doctor will confirm your request. Times are '
                            'provided by the clinic schedule.',
                          ),
                          if (_error != null) ...[
                            const SizedBox(height: 12),
                            _BookingMessage(message: _error!),
                          ],
                          const SizedBox(height: 16),
                          OutlinedButton.icon(
                            onPressed: _slotsLoading || _booking
                                ? null
                                : _pickDate,
                            icon: const Icon(Icons.calendar_month_outlined),
                            label: Text('Date: ${localDateString(_date)}'),
                          ),
                          const SizedBox(height: 12),
                          if (_slotsLoading)
                            const LinearProgressIndicator()
                          else if (_available != null &&
                              _available!.slots.isEmpty)
                            const EmptyPanel(
                              title: 'No available times',
                              message: 'Choose another date to check the clinic schedule.',
                              icon: Icons.event_busy_outlined,
                            )
                          else if (_available != null)
                            DropdownButtonFormField<DateTime>(
                              initialValue: _selectedStart,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Available appointment time',
                              ),
                              items: [
                                for (final slot in _available!.slots)
                                  DropdownMenuItem(
                                    value: slot.scheduledStart,
                                    child: Text(
                                      formatTimeInZone(
                                        slot.scheduledStart,
                                        _available!.timezone,
                                      ),
                                    ),
                                  ),
                              ],
                              onChanged: _booking
                                  ? null
                                  : (value) =>
                                        setState(() => _selectedStart = value),
                            ),
                          if (_available != null) ...[
                            const SizedBox(height: 6),
                            Text(
                              'Time zone: ${_available!.timezone}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                          const SizedBox(height: 14),
                          TextFormField(
                            controller: _visitReason,
                            maxLength: 1000,
                            textCapitalization: TextCapitalization.sentences,
                            decoration: const InputDecoration(
                              labelText: 'Reason for visit',
                            ),
                            validator: _validateReason,
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _patientNotes,
                            maxLength: 4000,
                            minLines: 2,
                            maxLines: 4,
                            textCapitalization: TextCapitalization.sentences,
                            decoration: const InputDecoration(
                              labelText: 'Notes for the doctor (optional)',
                              alignLabelWithHint: true,
                            ),
                            validator: _validateNotes,
                          ),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed:
                                _booking ||
                                    _slotsLoading ||
                                    _selectedStart == null
                                ? null
                                : _bookAppointment,
                            child: _booking
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text('Request appointment'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ],
            const SizedBox(height: 14),
            TextButton.icon(
              onPressed: () => context.go('/doctors'),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Back to doctor directory'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DoctorDetailRow extends StatelessWidget {
  const _DoctorDetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class _BookingMessage extends StatelessWidget {
  const _BookingMessage({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(message),
    );
  }
}

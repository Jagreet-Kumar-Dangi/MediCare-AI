import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/errors/session_expiration.dart';
import '../../../core/utils/date_time_formatters.dart';
import '../../../core/widgets/async_states.dart';
import '../data/appointment_repository.dart';
import '../domain/patient_appointment.dart';
import 'patient_appointments_screen.dart';

enum _AppointmentAction { cancel, reschedule }

class AppointmentDetailScreen extends ConsumerStatefulWidget {
  const AppointmentDetailScreen({super.key, required this.appointmentId});

  final int appointmentId;

  @override
  ConsumerState<AppointmentDetailScreen> createState() =>
      _AppointmentDetailScreenState();
}

class _AppointmentDetailScreenState
    extends ConsumerState<AppointmentDetailScreen> {
  final _reasonFormKey = GlobalKey<FormState>();
  final _reason = TextEditingController();
  PatientAppointment? _appointment;
  AvailableSlots? _available;
  DateTime _date = DateTime.now().add(const Duration(days: 7));
  DateTime? _selectedStart;
  _AppointmentAction? _action;
  bool _loading = true;
  bool _slotsLoading = false;
  bool _acting = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadAppointment);
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _loadAppointment() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final appointment = await ref
          .read(appointmentRepositoryProvider)
          .getAppointment(widget.appointmentId);
      if (mounted) setState(() => _appointment = appointment);
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadSlots({bool clearError = true}) async {
    final appointment = _appointment;
    if (appointment == null) return;
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
          .getAvailableSlots(
            doctorId: appointment.doctor.id,
            date: requestedDate,
          );
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

  Future<void> _pickRescheduleDate() async {
    final today = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _date.isBefore(today) ? today : _date,
      firstDate: DateTime(today.year, today.month, today.day),
      lastDate: DateTime(today.year, today.month, today.day + 90),
      helpText: 'Choose a new appointment date',
    );
    if (date != null && mounted) {
      setState(() {
        _date = DateTime(date.year, date.month, date.day);
        _available = null;
        _selectedStart = null;
      });
      await _loadSlots();
    }
  }

  Future<void> _submitAction() async {
    final appointment = _appointment;
    final reason = _reason.text.trim();
    final action = _action;
    if (appointment == null || action == null || _acting) return;
    if (!_reasonFormKey.currentState!.validate() ||
        reason.length < 5 ||
        reason.length > 1000) {
      setState(() => _error = 'Enter a reason between 5 and 1000 characters.');
      return;
    }
    if (action == _AppointmentAction.reschedule && _selectedStart == null) {
      setState(() => _error = 'Select an available appointment time.');
      return;
    }
    setState(() {
      _acting = true;
      _error = null;
      _notice = null;
    });
    try {
      final repository = ref.read(appointmentRepositoryProvider);
      final updated = action == _AppointmentAction.cancel
          ? await repository.cancelAppointment(
              appointmentId: appointment.id,
              reason: reason,
            )
          : await repository.rescheduleAppointment(
              appointmentId: appointment.id,
              scheduledStart: _selectedStart!,
              reason: reason,
            );
      if (!mounted) return;
      setState(() {
        _appointment = updated;
        _action = null;
        _reason.clear();
        _available = null;
        _selectedStart = null;
        _notice = action == _AppointmentAction.cancel
            ? 'Appointment cancelled.'
            : 'New appointment time requested. The doctor must confirm it.';
      });
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (!mounted) return;
      final message = apiErrorMessage(error);
      setState(() => _error = message);
      if (action == _AppointmentAction.reschedule) {
        await _loadSlots(clearError: false);
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  String? _validateReason(String? value) {
    final length = (value ?? '').trim().length;
    if (length < 5) return 'Enter at least 5 characters.';
    if (length > 1000) return 'Use 1000 characters or fewer.';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final appointment = _appointment;
    return Scaffold(
      appBar: AppBar(title: const Text('Appointment details')),
      body: RefreshIndicator(
        onRefresh: _loadAppointment,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            if (_loading && appointment == null)
              const LoadingCards(count: 2)
            else if (_error != null && appointment == null)
              ErrorPanel(message: _error!, onRetry: _loadAppointment)
            else if (appointment != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.medical_services_outlined, size: 28),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              appointment.doctor.fullName,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                          StatusChip(status: appointment.status),
                        ],
                      ),
                      const SizedBox(height: 18),
                      _DetailRow(
                        label: 'Appointment time',
                        value:
                            '${formatDate(appointment.scheduledStart.toLocal())} · '
                            '${_formatLocalDateTime(appointment.scheduledStart)} '
                            '(device time)',
                      ),
                      _DetailRow(
                        label: 'Reason for visit',
                        value: appointment.reasonForVisit,
                      ),
                      if (appointment.patientNotes != null)
                        _DetailRow(
                          label: 'Notes for doctor',
                          value: appointment.patientNotes!,
                        ),
                      if (appointment.cancellationReason != null)
                        _DetailRow(
                          label: 'Cancellation reason',
                          value: appointment.cancellationReason!,
                        ),
                      if (appointment.rejectionReason != null)
                        _DetailRow(
                          label: 'Doctor response',
                          value: appointment.rejectionReason!,
                        ),
                    ],
                  ),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                _Feedback(message: _error!, isError: true),
              ],
              if (_notice != null) ...[
                const SizedBox(height: 12),
                _Feedback(message: _notice!, isError: false),
              ],
              if (appointment.canChange) ...[
                const SizedBox(height: 14),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'Manage appointment',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Cancellation and rescheduling cutoffs are applied '
                          'by the clinic server.',
                        ),
                        const SizedBox(height: 14),
                        if (_action == null)
                          Wrap(
                            spacing: 10,
                            runSpacing: 8,
                            children: [
                              OutlinedButton.icon(
                                onPressed: _acting
                                    ? null
                                    : () {
                                        setState(() {
                                          _action =
                                              _AppointmentAction.reschedule;
                                          _reason.clear();
                                          _error = null;
                                          _date = DateTime.now().add(
                                            const Duration(days: 7),
                                          );
                                        });
                                        _loadSlots();
                                      },
                                icon: const Icon(Icons.event_repeat),
                                label: const Text('Reschedule'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _acting
                                    ? null
                                    : () => setState(() {
                                        _action = _AppointmentAction.cancel;
                                        _reason.clear();
                                        _error = null;
                                      }),
                                icon: const Icon(Icons.event_busy),
                                label: const Text('Cancel appointment'),
                              ),
                            ],
                          )
                        else ...[
                          if (_action == _AppointmentAction.reschedule) ...[
                            OutlinedButton.icon(
                              onPressed: _slotsLoading
                                  ? null
                                  : _pickRescheduleDate,
                              icon: const Icon(Icons.calendar_month),
                              label: Text('Date: ${localDateString(_date)}'),
                            ),
                            const SizedBox(height: 12),
                            if (_slotsLoading)
                              const LinearProgressIndicator()
                            else if (_error == null &&
                                _available?.slots.isEmpty == true)
                              const Text('No available times on this date.')
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
                                onChanged: _acting
                                    ? null
                                    : (value) => setState(
                                        () => _selectedStart = value,
                                      ),
                              ),
                            if (_available != null) ...[
                              const SizedBox(height: 6),
                              Text(
                                'Times are shown in ${_available!.timezone}.',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                            const SizedBox(height: 12),
                          ],
                          Form(
                            key: _reasonFormKey,
                            child: TextFormField(
                              controller: _reason,
                              maxLength: 1000,
                              minLines: 2,
                              maxLines: 4,
                              textCapitalization: TextCapitalization.sentences,
                              decoration: InputDecoration(
                                labelText: _action == _AppointmentAction.cancel
                                    ? 'Reason for cancellation'
                                    : 'Reason for rescheduling',
                                alignLabelWithHint: true,
                              ),
                              validator: _validateReason,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 10,
                            runSpacing: 8,
                            children: [
                              FilledButton(
                                onPressed:
                                    _acting ||
                                        (_action ==
                                                _AppointmentAction.reschedule &&
                                            (_selectedStart == null ||
                                                _slotsLoading))
                                    ? null
                                    : _submitAction,
                                child: _acting
                                    ? const SizedBox(
                                        width: 18,
                                        height: 18,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      )
                                    : Text(
                                        _action == _AppointmentAction.cancel
                                            ? 'Confirm cancellation'
                                            : 'Request new time',
                                      ),
                              ),
                              TextButton(
                                onPressed: _acting
                                    ? null
                                    : () => setState(() {
                                        _action = null;
                                        _error = null;
                                        _available = null;
                                        _selectedStart = null;
                                      }),
                                child: const Text('Keep appointment'),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Appointment activity',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      if (appointment.auditEvents.isEmpty)
                        const Text('No appointment updates to show.')
                      else
                        for (final event in appointment.auditEvents) ...[
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.history),
                            title: Text(_humanize(event.action)),
                            subtitle: Text(
                              [
                                _formatLocalDateTime(event.createdAt),
                                if (event.reason != null) event.reason!,
                              ].join(' · '),
                            ),
                          ),
                        ],
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: () => context.go('/appointments'),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Back to appointments'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          Text(value),
        ],
      ),
    );
  }
}

class _Feedback extends StatelessWidget {
  const _Feedback({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError
        ? Theme.of(context).colorScheme.error
        : const Color(0xFF176B43);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Text(message, style: TextStyle(color: color)),
    );
  }
}

String _formatLocalDateTime(DateTime value) {
  final local = value.toLocal();
  final hour = local.hour % 12 == 0 ? 12 : local.hour % 12;
  final minute = local.minute.toString().padLeft(2, '0');
  return '${formatDate(local)} · $hour:$minute ${local.hour < 12 ? 'AM' : 'PM'}';
}

String _humanize(String value) {
  return value
      .toLowerCase()
      .split('_')
      .map(
        (word) => word.isEmpty
            ? word
            : '${word[0].toUpperCase()}${word.substring(1)}',
      )
      .join(' ');
}

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/errors/session_expiration.dart';
import '../../../core/utils/date_time_formatters.dart';
import '../../../core/widgets/async_states.dart';
import '../data/appointment_repository.dart';
import '../domain/patient_appointment.dart';

class PatientAppointmentsScreen extends ConsumerStatefulWidget {
  const PatientAppointmentsScreen({super.key});

  @override
  ConsumerState<PatientAppointmentsScreen> createState() =>
      _PatientAppointmentsScreenState();
}

class _PatientAppointmentsScreenState
    extends ConsumerState<PatientAppointmentsScreen> {
  String _view = 'upcoming';
  List<PatientAppointment> _appointments = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadAppointments);
  }

  Future<void> _loadAppointments() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final appointments = await ref
          .read(appointmentRepositoryProvider)
          .listMyAppointments(view: _view);
      if (mounted) setState(() => _appointments = appointments);
    } catch (error) {
      await handleSessionExpiration(ref, error);
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My appointments'),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.push('/profile'),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAppointments,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Your care schedule',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Appointment times are returned in UTC and displayed in your '
              'device time zone. Cancellation and rescheduling rules are '
              'enforced by the clinic.',
            ),
            const SizedBox(height: 16),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'upcoming', label: Text('Upcoming')),
                ButtonSegment(value: 'history', label: Text('History')),
              ],
              selected: {_view},
              onSelectionChanged: _loading
                  ? null
                  : (selection) {
                      setState(() => _view = selection.first);
                      _loadAppointments();
                    },
            ),
            const SizedBox(height: 16),
            if (_error != null) ...[
              ErrorPanel(message: _error!, onRetry: _loadAppointments),
              const SizedBox(height: 12),
            ],
            if (_loading)
              const LoadingCards()
            else if (_error == null && _appointments.isEmpty)
              EmptyPanel(
                title: 'No $_view appointments',
                message: _view == 'upcoming'
                    ? 'Appointments you request will appear here.'
                    : 'Completed, cancelled, and past appointments will appear here.',
                icon: Icons.calendar_month_outlined,
                action: _view == 'upcoming'
                    ? OutlinedButton.icon(
                        onPressed: () => context.go('/doctors'),
                        icon: const Icon(Icons.search),
                        label: const Text('Find an eligible doctor'),
                      )
                    : null,
              )
            else
              for (final appointment in _appointments) ...[
                _AppointmentCard(
                  appointment: appointment,
                  onTap: () => context.push('/appointments/${appointment.id}'),
                ),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _AppointmentCard extends StatelessWidget {
  const _AppointmentCard({required this.appointment, required this.onTap});

  final PatientAppointment appointment;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final starts = appointment.scheduledStart.toLocal();
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.medical_services_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      appointment.doctor.fullName,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  StatusChip(status: appointment.status),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                '${formatDate(starts)} · ${_formatLocalTime(starts)} local',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 6),
              Text(
                appointment.reasonForVisit,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 10),
              const Text('View appointment details'),
            ],
          ),
        ),
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'CONFIRMED' => const Color(0xFF176B43),
      'CANCELLED' || 'REJECTED' => const Color(0xFF9E3434),
      'COMPLETED' => const Color(0xFF385C91),
      _ => const Color(0xFF765A11),
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Text(
          status,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

String _formatLocalTime(DateTime value) {
  final hour = value.hour % 12 == 0 ? 12 : value.hour % 12;
  final minute = value.minute.toString().padLeft(2, '0');
  return '$hour:$minute ${value.hour < 12 ? 'AM' : 'PM'}';
}

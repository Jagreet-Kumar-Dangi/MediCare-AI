import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/theme/app_theme.dart';
import '../../../features/auth/presentation/auth_controller.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user!;
    final isDoctor = user.isDoctor;
    final displayName = user.email.split('@').first;
    return Scaffold(
      appBar: AppBar(
        title: const Text('MediCare AI'),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.push('/profile'),
            icon: const Icon(Icons.account_circle_outlined),
          ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: () async {
              try {
                await ref.read(authControllerProvider.notifier).signOut();
              } catch (error) {
                if (!context.mounted) return;
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
              }
            },
            icon: const Icon(Icons.logout),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.teal,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isDoctor ? 'DOCTOR WORKSPACE' : 'PATIENT DASHBOARD',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Welcome, $displayName',
                    style: Theme.of(context).textTheme.headlineMedium
                        ?.copyWith(color: Colors.white, fontSize: 26),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    isDoctor
                        ? 'Your care workspace is ready.'
                        : 'Your health journey starts here.',
                    style: const TextStyle(color: Colors.white, fontSize: 16),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      isDoctor
                          ? Icons.medical_information_outlined
                          : Icons.health_and_safety_outlined,
                      color: AppTheme.teal,
                      size: 30,
                    ),
                    const SizedBox(height: 14),
                    Text(
                      isDoctor ? 'Doctor account' : 'Patient account',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      isDoctor
                          ? 'Your account is connected securely.'
                          : 'Your profile, doctor directory, and appointments '
                                'are ready to explore.',
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: () => context.push('/profile'),
                      icon: const Icon(Icons.person_outline),
                      label: const Text('View profile'),
                    ),
                  ],
                ),
              ),
            ),
            if (!isDoctor) ...[
              const SizedBox(height: 12),
              _DashboardActionCard(
                icon: Icons.search,
                title: 'Find a doctor',
                description: 'Explore approved doctors who are eligible to accept appointments.',
                actionLabel: 'Browse directory',
                onPressed: () => context.push('/doctors'),
              ),
              const SizedBox(height: 12),
              _DashboardActionCard(
                icon: Icons.calendar_month_outlined,
                title: 'My appointments',
                description: 'Review upcoming appointments and your appointment history.',
                actionLabel: 'View appointments',
                onPressed: () => context.push('/appointments'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DashboardActionCard extends StatelessWidget {
  const _DashboardActionCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.actionLabel,
    required this.onPressed,
  });

  final IconData icon;
  final String title;
  final String description;
  final String actionLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.teal, size: 30),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(description),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                      onPressed: onPressed,
                      child: Text(actionLabel),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

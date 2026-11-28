import 'dart:async';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error_message.dart';
import '../../../core/widgets/brand_mark.dart';
import '../data/auth_repository.dart';

class EmailVerificationScreen extends ConsumerStatefulWidget {
  const EmailVerificationScreen({
    super.key,
    this.email,
    this.autoSend = false,
    this.initialMessage,
  });

  final String? email;
  final bool autoSend;
  final String? initialMessage;

  @override
  ConsumerState<EmailVerificationScreen> createState() =>
      _EmailVerificationScreenState();
}

class _EmailVerificationScreenState
    extends ConsumerState<EmailVerificationScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _email;
  final _code = TextEditingController();
  Timer? _timer;
  int _countdown = 0;
  bool _busy = false;
  bool _verified = false;
  bool _autoSendStarted = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _email = TextEditingController(text: widget.email ?? '');
    _error = widget.initialMessage;
    if (widget.email != null &&
        !widget.autoSend &&
        widget.initialMessage == null) {
      _countdown = 60;
      _startCountdown();
    }
    if (widget.autoSend && widget.email != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_autoSendStarted) {
          _autoSendStarted = true;
          _requestCode(resend: false);
        }
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  void _startCountdown() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (_countdown <= 1) {
          _countdown = 0;
          timer.cancel();
        } else {
          _countdown--;
        }
      });
    });
  }

  String? _validateEmail(String? value) {
    final email = value?.trim() ?? '';
    return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)
        ? null
        : 'Enter a valid email address.';
  }

  String? _validateCode(String? value) =>
      RegExp(r'^\d{6}$').hasMatch(value ?? '')
      ? null
      : 'Enter the six-digit verification code.';

  Future<void> _requestCode({required bool resend}) async {
    final email = _email.text.trim();
    if (_validateEmail(email) != null) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      final repository = ref.read(authRepositoryProvider);
      if (resend) {
        await repository.resendVerificationEmail(email: email);
      } else {
        await repository.sendVerificationEmail(email: email);
      }
      if (!mounted) return;
      setState(() {
        _countdown = 60;
        _notice = 'If this address can be verified, a code has been sent.';
      });
      _startCountdown();
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await ref.read(authRepositoryProvider).confirmEmailVerification(
            email: _email.text.trim(),
            code: _code.text,
          );
      if (mounted) setState(() => _verified = true);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _maskedEmail(String email) {
    final parts = email.split('@');
    if (parts.length != 2 || parts.first.isEmpty) return email;
    final visible = parts.first.length < 3
        ? parts.first.substring(0, 1)
        : parts.first.substring(0, 2);
    final hiddenLength = parts.first.length - visible.length;
    final stars = List<String>.filled(hiddenLength < 3 ? 3 : hiddenLength, '*')
        .join();
    return '$visible$stars@${parts.last}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Email verification')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: _verified
                  ? _buildVerified(context)
                  : _buildVerificationForm(context),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildVerified(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Center(child: BrandMark(size: 56)),
        const SizedBox(height: 20),
        Text(
          'Email verified',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 12),
        const Text(
          'Your email address has been verified. You can now sign in.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => context.go('/login'),
          child: const Text('Continue to sign in'),
        ),
      ],
    );
  }

  Widget _buildVerificationForm(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Center(child: BrandMark(size: 56)),
          const SizedBox(height: 18),
          Text(
            'Verify your email',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          const Text(
            'Enter the six-digit code sent to your email address.',
            textAlign: TextAlign.center,
          ),
          if (_email.text.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Destination: ${_maskedEmail(_email.text.trim())}',
              textAlign: TextAlign.center,
            ),
          ],
          const SizedBox(height: 24),
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'Email address'),
            validator: _validateEmail,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _code,
            keyboardType: TextInputType.number,
            textInputAction: TextInputAction.done,
            autofillHints: const [AutofillHints.oneTimeCode],
            maxLength: 6,
            decoration: const InputDecoration(
              labelText: 'Six-digit code',
              counterText: '',
            ),
            onChanged: (value) {
              final digits = value.replaceAll(RegExp(r'\D'), '');
              if (digits != value) {
                _code.value = TextEditingValue(
                  text: digits.length > 6 ? digits.substring(0, 6) : digits,
                  selection: TextSelection.collapsed(
                    offset: digits.length > 6 ? 6 : digits.length,
                  ),
                );
              }
            },
            validator: _validateCode,
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
          if (_notice != null) ...[
            const SizedBox(height: 12),
            Text(_notice!, textAlign: TextAlign.center),
          ],
          const SizedBox(height: 18),
          FilledButton(
            onPressed: _busy ? null : _verify,
            child: _busy
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('Verify email'),
          ),
          const SizedBox(height: 10),
          OutlinedButton(
            onPressed: _busy || _countdown > 0
                ? null
                : () => _requestCode(resend: true),
            child: Text(
              _countdown > 0
                  ? 'Resend code in ${_countdown}s'
                  : 'Resend verification code',
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Codes expire after five minutes. Never share your code with anyone.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

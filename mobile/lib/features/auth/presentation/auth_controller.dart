import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/secure_token_storage.dart';
import '../data/auth_repository.dart';
import '../domain/app_user.dart';

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);

class AuthState {
  const AuthState({
    this.isInitializing = true,
    this.isBusy = false,
    this.user,
    this.message,
  });

  final bool isInitializing;
  final bool isBusy;
  final AppUser? user;
  final String? message;

  AuthState copyWith({
    bool? isInitializing,
    bool? isBusy,
    AppUser? user,
    bool clearUser = false,
    String? message,
    bool clearMessage = false,
  }) {
    return AuthState(
      isInitializing: isInitializing ?? this.isInitializing,
      isBusy: isBusy ?? this.isBusy,
      user: clearUser ? null : user ?? this.user,
      message: clearMessage ? null : message ?? this.message,
    );
  }
}

class AuthController extends Notifier<AuthState> {
  TokenStorage get _storage => ref.read(tokenStorageProvider);
  AuthRepository get _repository => ref.read(authRepositoryProvider);

  @override
  AuthState build() {
    Future.microtask(_restoreSession);
    return const AuthState();
  }

  Future<void> _restoreSession() async {
    try {
      final token = await _storage.read();
      if (token == null || token.isEmpty) {
        state = const AuthState(isInitializing: false);
        return;
      }
      final user = await _repository.currentUser();
      if (user.role == 'ADMIN') {
        await _storage.delete();
        state = const AuthState(
          isInitializing: false,
          message: 'Administrator accounts are not available in this app.',
        );
        return;
      }
      state = AuthState(isInitializing: false, user: user);
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        Object? storageError;
        try {
          await _storage.delete();
        } catch (error) {
          storageError = error;
        }
        state = AuthState(
          isInitializing: false,
          message: storageError == null
              ? 'Your session has expired. Please sign in again.'
              : 'Your session expired, but the saved sign-in could not be cleared.',
        );
        return;
      }
      state = AuthState(
        isInitializing: false,
        message: 'Unable to verify your saved session. Check your connection and try again.',
      );
    } catch (_) {
      state = AuthState(
        isInitializing: false,
        message: 'Could not restore your session. Please sign in again.',
      );
    }
  }

  Future<void> signIn({required String email, required String password}) async {
    state = state.copyWith(isBusy: true, clearMessage: true);
    try {
      final token = await _repository.login(email: email, password: password);
      await _storage.write(token);
      final user = await _repository.currentUser();
      if (user.role == 'ADMIN') {
        await _storage.delete();
        throw StateError(
          'Administrator accounts are not available in this app.',
        );
      }
      state = AuthState(isInitializing: false, user: user);
    } catch (error, stackTrace) {
      try {
        await _storage.delete();
      } finally {
        state = state.copyWith(isBusy: false, clearUser: true);
      }
      Error.throwWithStackTrace(error, stackTrace);
    }
  }

  Future<void> registerPatient({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    state = state.copyWith(isBusy: true, clearMessage: true);
    try {
      await _repository.registerPatient(
        email: email,
        password: password,
        firstName: firstName,
        lastName: lastName,
      );
      state = state.copyWith(isBusy: false);
    } catch (_) {
      state = state.copyWith(isBusy: false);
      rethrow;
    }
  }

  Future<void> registerDoctor(Map<String, dynamic> request) async {
    state = state.copyWith(isBusy: true, clearMessage: true);
    try {
      await _repository.registerDoctor(request);
      state = state.copyWith(isBusy: false);
    } catch (_) {
      state = state.copyWith(isBusy: false);
      rethrow;
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isBusy: true, clearMessage: true);
    Object? logoutError;
    Object? storageError;
    try {
      await _repository.logout();
    } catch (error) {
      logoutError = error;
    }
    try {
      await _storage.delete();
    } catch (error) {
      storageError = error;
    }
    final message = storageError != null
        ? 'Unable to clear the saved sign-in from this device.'
        : logoutError == null
        ? null
        : 'Signed out on this device, but server sign out could not be confirmed.';
    state = AuthState(isInitializing: false, message: message);
    if (storageError != null) {
      Error.throwWithStackTrace(storageError, StackTrace.current);
    }
    if (logoutError != null) {
      Error.throwWithStackTrace(logoutError, StackTrace.current);
    }
  }

  Future<void> handleExpiredSession() async {
    Object? storageError;
    try {
      await _storage.delete();
    } catch (error) {
      storageError = error;
    }
    state = AuthState(
      isInitializing: false,
      message: storageError == null
          ? 'Your session has expired. Please sign in again.'
          : 'Your session expired, but the saved sign-in could not be cleared.',
    );
  }
}

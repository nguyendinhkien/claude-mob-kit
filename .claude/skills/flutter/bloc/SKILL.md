---
name: bloc
description: BLoC state management pattern for Flutter.
  Use when building event-driven features with strict separation or on large teams.
  Preloaded into agents when project uses bloc.
user-invocable: false
disable-model-invocation: true
---

# BLoC State Management

## 1. When to Use

- Complex event-driven features: auth flows, multi-step forms, real-time data
- Large teams: enforced structure prevents cowboy coding
- Features needing event transformation: debounce, throttle, switchMap
- When audit logging of events is valuable (every state change has a traceable event)

## 2. When NOT to Use

- Simple CRUD screens with straightforward fetch/display
- Small features with 2-3 states (use Cubit instead — see section 9)
- Rapid prototyping where speed matters more than structure

## 3. Dependencies

Add via CLI to always get the latest versions:
```bash
flutter pub add flutter_bloc bloc equatable
flutter pub add --dev bloc_test
```

## 4. Folder Structure

```
lib/features/[feature]/presentation/
├── bloc/
│   ├── [feature]_bloc.dart       # Bloc class with event handlers
│   ├── [feature]_event.dart      # Sealed event class
│   └── [feature]_state.dart      # Sealed state class
├── pages/
│   └── [feature]_page.dart
└── widgets/
    └── [feature]_list.dart
```

## 5. Core Patterns

### Event — Sealed Class

Every user action or system trigger is an event. Use sealed classes for exhaustive matching.

```dart
// lib/features/auth/presentation/bloc/auth_event.dart
import 'package:equatable/equatable.dart';

sealed class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

final class AuthLoginRequested extends AuthEvent {
  const AuthLoginRequested({required this.email, required this.password});
  final String email;
  final String password;

  @override
  List<Object?> get props => [email, password];
}

final class AuthLogoutRequested extends AuthEvent {
  const AuthLogoutRequested();
}

final class AuthStatusChecked extends AuthEvent {
  const AuthStatusChecked();
}
```

### State — Sealed Class

Every possible output the UI can render. Never add fields directly on the base class — each state carries only what it needs.

```dart
// lib/features/auth/presentation/bloc/auth_state.dart
import 'package:equatable/equatable.dart';
import '../../../domain/entities/user.dart';

sealed class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

final class AuthInitial extends AuthState {
  const AuthInitial();
}

final class AuthLoading extends AuthState {
  const AuthLoading();
}

final class AuthSuccess extends AuthState {
  const AuthSuccess({required this.user});
  final User user;

  @override
  List<Object?> get props => [user];
}

final class AuthFailure extends AuthState {
  const AuthFailure({required this.message});
  final String message;

  @override
  List<Object?> get props => [message];
}
```

### Bloc — Event Handlers

```dart
// lib/features/auth/presentation/bloc/auth_bloc.dart
import 'package:bloc/bloc.dart';
import '../../../domain/usecases/login_user.dart';
import '../../../domain/usecases/logout_user.dart';
import 'auth_event.dart';
import 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc({
    required LoginUser loginUser,
    required LogoutUser logoutUser,
  })  : _loginUser = loginUser,
        _logoutUser = logoutUser,
        super(const AuthInitial()) {
    on<AuthLoginRequested>(_onLoginRequested);
    on<AuthLogoutRequested>(_onLogoutRequested);
    on<AuthStatusChecked>(_onStatusChecked);
  }

  final LoginUser _loginUser;
  final LogoutUser _logoutUser;

  Future<void> _onLoginRequested(
    AuthLoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());
    final result = await _loginUser(
      LoginParams(email: event.email, password: event.password),
    );
    result.fold(
      (failure) => emit(AuthFailure(message: failure.message)),
      (user) => emit(AuthSuccess(user: user)),
    );
  }

  Future<void> _onLogoutRequested(
    AuthLogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    await _logoutUser();
    emit(const AuthInitial());
  }

  Future<void> _onStatusChecked(
    AuthStatusChecked event,
    Emitter<AuthState> emit,
  ) async {
    // Check stored auth token, emit accordingly
  }
}
```

### BlocBuilder — Rebuild on State Change

```dart
class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
        return switch (state) {
          AuthInitial() => const LoginForm(),
          AuthLoading() => const Center(child: CircularProgressIndicator()),
          AuthSuccess(:final user) => Text('Welcome, ${user.name}'),
          AuthFailure(:final message) => LoginForm(errorMessage: message),
        };
      },
    );
  }
}
```

### BlocListener — Side Effects

Use `BlocListener` for one-time actions: navigation, snackbar, dialog. Never use `BlocBuilder` for side effects.

```dart
BlocListener<AuthBloc, AuthState>(
  listener: (context, state) {
    if (state is AuthSuccess) {
      Navigator.of(context).pushReplacementNamed('/home');
    }
    if (state is AuthFailure) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.message)),
      );
    }
  },
  child: const LoginForm(),
)
```

### BlocConsumer — Builder + Listener Combined

When you need both side effects and reactive UI in the same widget:

```dart
BlocConsumer<AuthBloc, AuthState>(
  listener: (context, state) {
    if (state is AuthSuccess) {
      Navigator.of(context).pushReplacementNamed('/home');
    }
  },
  builder: (context, state) {
    return LoginForm(isLoading: state is AuthLoading);
  },
)
```

### MultiBlocProvider — App Level

```dart
// main.dart
MultiBlocProvider(
  providers: [
    BlocProvider(create: (_) => getIt<AuthBloc>()..add(const AuthStatusChecked())),
    BlocProvider(create: (_) => getIt<ThemeBloc>()),
  ],
  child: const MyApp(),
)
```

## 6. Error Handling

Never throw inside a Bloc. Map errors to failure states.

```dart
Future<void> _onFetchRequested(
  FetchRequested event,
  Emitter<DataState> emit,
) async {
  emit(const DataLoading());
  try {
    final result = await _getData();
    result.fold(
      (failure) => emit(DataFailure(message: failure.message)),
      (data) => emit(DataSuccess(data: data)),
    );
  } catch (e, stack) {
    // Catch unexpected errors — log and emit failure
    emit(DataFailure(message: 'An unexpected error occurred'));
  }
}
```

## 7. Testing

```dart
import 'package:bloc_test/bloc_test.dart';

// blocTest handles create, act, expect, and verify in one call
blocTest<AuthBloc, AuthState>(
  'should_emit_loading_then_success_when_login_succeeds',
  build: () {
    when(() => mockLoginUser(any())).thenAnswer(
      (_) async => Right(testUser),
    );
    return AuthBloc(loginUser: mockLoginUser, logoutUser: mockLogoutUser);
  },
  act: (bloc) => bloc.add(
    const AuthLoginRequested(email: 'test@test.com', password: 'pass123'),
  ),
  expect: () => [
    const AuthLoading(),
    AuthSuccess(user: testUser),
  ],
  verify: (_) {
    verify(() => mockLoginUser(any())).called(1);
  },
);

blocTest<AuthBloc, AuthState>(
  'should_emit_loading_then_failure_when_login_fails',
  build: () {
    when(() => mockLoginUser(any())).thenAnswer(
      (_) async => Left(ServerFailure('Invalid credentials')),
    );
    return AuthBloc(loginUser: mockLoginUser, logoutUser: mockLogoutUser);
  },
  act: (bloc) => bloc.add(
    const AuthLoginRequested(email: 'test@test.com', password: 'wrong'),
  ),
  expect: () => [
    const AuthLoading(),
    const AuthFailure(message: 'Invalid credentials'),
  ],
);
```

## 8. Anti-patterns

| Anti-pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| Business logic in `BlocBuilder` | UI layer computing state instead of rendering it | Move all logic into Bloc event handlers or domain use cases |
| Not extending `Equatable` on events/states | Bloc can't detect duplicate states, causes unnecessary rebuilds or missed updates | Always extend `Equatable` and list all fields in `props` |
| Emitting the same state instance twice | Bloc deduplicates by reference; same instance = no rebuild | Create a new state instance each time, ensure `props` differ |
| Calling `bloc.close()` manually | `BlocProvider` handles lifecycle; manual close causes use-after-close errors | Let `BlocProvider` manage it. Only close in tests |
| Adding events in `dispose()` | Bloc may already be closed when widget disposes | Handle cleanup in the Bloc's `close()` override |

## 9. Cubit vs Bloc Decision

Use **Cubit** when:
- State changes are direct method calls (no complex event transformation)
- You don't need debounce, throttle, or event replay
- The feature has simple input→output flow (tap button → fetch data → show result)

Use **Bloc** when:
- You need event transformers (debounce search input, throttle scroll events)
- Event traceability matters (audit logs, analytics, debugging complex flows)
- Multiple events can trigger the same state transition in different ways

Cubit is a subset of Bloc. Every Cubit can be upgraded to a Bloc by wrapping methods in events. Start with Cubit, upgrade when you need event-level control.

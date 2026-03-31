---
name: flutter-navigation
description: GoRouter navigation patterns for Flutter apps following Clean Architecture.
  Auto-loads when working with Dart files.
paths: "lib/**/*.dart, test/**/*.dart"
allowed-tools: Read, Write, Edit, Bash(flutter *)
---

# Flutter Navigation — GoRouter

## 1. Standard: GoRouter

GoRouter is the standard navigation solution. Do not use `Navigator.push()` / `Navigator.pop()` directly — GoRouter wraps Navigator and adds declarative routing, deep linking, and auth guards.

Install:
```bash
flutter pub add go_router
```

## 2. Setup Pattern

Router configuration lives in `core/router/`, not inside any feature.

```
lib/core/router/
├── app_router.dart        # GoRouter instance and route definitions
├── route_names.dart       # Route name constants
└── route_guards.dart      # Redirect logic (auth, onboarding)
```

## 3. Complete GoRouter Setup

### Route Name Constants

```dart
// lib/core/router/route_names.dart
abstract final class RouteNames {
  static const splash = 'splash';
  static const login = 'login';
  static const home = 'home';
  static const transactionDetail = 'transaction-detail';
  static const profile = 'profile';
  static const settings = 'settings';
}

abstract final class RoutePaths {
  static const splash = '/splash';
  static const login = '/login';
  static const home = '/';
  static const transactionDetail = '/transactions/:id';
  static const profile = '/profile';
  static const settings = '/settings';
}
```

### AppRouter

```dart
// lib/core/router/app_router.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/home/presentation/pages/home_page.dart';
import '../../features/transaction/presentation/pages/transaction_detail_page.dart';
import '../../features/profile/presentation/pages/profile_page.dart';
import '../../features/settings/presentation/pages/settings_page.dart';
import 'route_names.dart';

class AppRouter {
  AppRouter({required this.isAuthenticated});

  final ValueNotifier<bool> isAuthenticated;

  late final GoRouter router = GoRouter(
    initialLocation: RoutePaths.home,
    refreshListenable: isAuthenticated,
    redirect: _redirect,
    errorBuilder: (context, state) => ErrorPage(error: state.error),
    routes: [
      GoRoute(
        path: RoutePaths.login,
        name: RouteNames.login,
        builder: (context, state) => const LoginPage(),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: RoutePaths.home,
            name: RouteNames.home,
            builder: (context, state) => const HomePage(),
            routes: [
              GoRoute(
                path: 'transactions/:id',
                name: RouteNames.transactionDetail,
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return TransactionDetailPage(transactionId: id);
                },
              ),
            ],
          ),
          GoRoute(
            path: RoutePaths.profile,
            name: RouteNames.profile,
            builder: (context, state) => const ProfilePage(),
          ),
          GoRoute(
            path: RoutePaths.settings,
            name: RouteNames.settings,
            builder: (context, state) => const SettingsPage(),
          ),
        ],
      ),
    ],
  );

  String? _redirect(BuildContext context, GoRouterState state) {
    final loggedIn = isAuthenticated.value;
    final isLoginRoute = state.matchedLocation == RoutePaths.login;

    if (!loggedIn && !isLoginRoute) return RoutePaths.login;
    if (loggedIn && isLoginRoute) return RoutePaths.home;
    return null; // No redirect
  }
}

// Error page
class ErrorPage extends StatelessWidget {
  const ErrorPage({super.key, this.error});
  final Exception? error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Page not found', style: TextStyle(fontSize: 24)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => context.go(RoutePaths.home),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    );
  }
}
```

### Wire Into App

```dart
// lib/main.dart
class MyApp extends StatelessWidget {
  const MyApp({super.key, required this.appRouter});
  final AppRouter appRouter;

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      routerConfig: appRouter.router,
      theme: appTheme(),
    );
  }
}
```

## 4. Navigation Patterns

### context.go() vs context.push() vs context.pop()

| Method | Behavior | Use When |
|--------|----------|----------|
| `context.go('/path')` | Replaces the entire navigation stack up to the matched route | Navigating between top-level sections (home → profile) |
| `context.push('/path')` | Pushes on top of current stack | Drilling into a detail screen (list → detail) |
| `context.pop()` | Pops the topmost route | Going back from a pushed screen |
| `context.pushReplacement('/path')` | Replaces current route on the stack | Login → Home (user shouldn't go back to login) |

```dart
// Top-level navigation — switches sections
BottomNavigationBar(
  onTap: (index) {
    switch (index) {
      case 0: context.go(RoutePaths.home);
      case 1: context.go(RoutePaths.profile);
      case 2: context.go(RoutePaths.settings);
    }
  },
)

// Drill into detail — pushes onto stack
onTap: () => context.push('/transactions/${transaction.id}')

// Go back
onPressed: () => context.pop()

// Pass result back
onPressed: () => context.pop(selectedItem)
```

### Passing Data Between Routes

```dart
// Path parameters — for IDs and required identifiers
context.push('/transactions/${transaction.id}');
// Read: state.pathParameters['id']

// Query parameters — for optional filters
context.push('/transactions?status=completed&page=2');
// Read: state.uri.queryParameters['status']

// Extras — for complex objects already in memory
context.push('/transactions/detail', extra: transaction);
// Read: state.extra as Transaction
// WARNING: extras don't survive app restart or deep links. Use only for in-memory navigation.
```

### Nested Navigation with ShellRoute

```dart
ShellRoute(
  builder: (context, state, child) {
    return Scaffold(
      body: child, // Active route renders here
      bottomNavigationBar: const AppBottomNav(),
    );
  },
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomePage()),
    GoRoute(path: '/profile', builder: (_, __) => const ProfilePage()),
    GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
  ],
)
```

## 5. Deep Linking Setup

### Android — AndroidManifest.xml

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<activity ...>
  <intent-filter android:autoVerify="true">
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="https" android:host="myapp.com" />
  </intent-filter>
</activity>
```

### iOS — Info.plist + Associated Domains

```xml
<!-- ios/Runner/Info.plist -->
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>myapp</string>
    </array>
  </dict>
</array>
```

Add Associated Domains in Xcode: `applinks:myapp.com`

GoRouter handles deep links automatically — any URL matching a defined route path will navigate to it.

## 6. Auth Guard Pattern

```dart
// lib/core/router/route_guards.dart
String? authRedirect(BuildContext context, GoRouterState state) {
  final authState = context.read<AuthBloc>().state;
  final isAuthenticated = authState is AuthSuccess;
  final isAuthRoute = state.matchedLocation == RoutePaths.login;

  // Not logged in and not on login page → redirect to login
  if (!isAuthenticated && !isAuthRoute) {
    return '${RoutePaths.login}?redirect=${state.matchedLocation}';
  }

  // Logged in and on login page → redirect to intended destination or home
  if (isAuthenticated && isAuthRoute) {
    final redirect = state.uri.queryParameters['redirect'];
    return redirect ?? RoutePaths.home;
  }

  return null; // No redirect needed
}
```

## 7. Testing

```dart
// Widget test with GoRouter
testWidgets('should_navigate_to_detail_on_tap', (tester) async {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(path: '/', builder: (_, __) => const TransactionListPage()),
      GoRoute(
        path: '/transactions/:id',
        builder: (_, state) => TransactionDetailPage(
          transactionId: state.pathParameters['id']!,
        ),
      ),
    ],
  );

  await tester.pumpWidget(MaterialApp.router(routerConfig: router));
  await tester.pumpAndSettle();

  await tester.tap(find.byType(TransactionTile).first);
  await tester.pumpAndSettle();

  expect(find.byType(TransactionDetailPage), findsOneWidget);
});

// Mock GoRouter for isolated widget testing
testWidgets('should_call_go_on_button_press', (tester) async {
  final mockRouter = MockGoRouter();

  await tester.pumpWidget(
    MaterialApp(
      home: InheritedGoRouter(
        goRouter: mockRouter,
        child: const HomePage(),
      ),
    ),
  );

  await tester.tap(find.text('View Profile'));
  verify(() => mockRouter.go(RoutePaths.profile)).called(1);
});
```

## 8. Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| `Navigator.push()` mixed with GoRouter | Two navigation systems fight; back button behaves unpredictably | Use only `context.go()` / `context.push()` / `context.pop()` |
| Passing large objects via `extra` | Extras are lost on app restart, don't survive deep links | Pass ID via path parameter, fetch data on the detail page |
| Hardcoded path strings | Typos cause silent failures; no compile-time check | Use `RouteNames` / `RoutePaths` constants |
| Route logic in widgets | Widget knows too much about navigation structure | Centralize all routes in `AppRouter`, widgets just call `context.go()` |
| Not handling error routes | Unmatched deep links show blank screen | Always define `errorBuilder` in GoRouter |

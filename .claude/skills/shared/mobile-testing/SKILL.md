---
name: mobile-testing
description: Testing strategy for mobile apps across all platforms.
  Use when writing tests, reviewing test coverage, or setting up test infrastructure.
user-invocable: true
---

# Mobile Testing Strategy

## 1. Test Pyramid

```
        ╱  Integration (E2E)  ╲        ← Few, slow, high confidence
       ╱   Widget / UI Tests   ╲       ← Moderate count, medium speed
      ╱     Unit Tests (bulk)    ╲     ← Many, fast, low-level confidence
```

**Coverage targets by layer:**

| Layer | Target | Rationale |
|-------|--------|-----------|
| domain (entities + use cases) | **80%** | Pure logic, easy to test, highest business value |
| data (repositories + models) | **60%** | Serialization and data coordination are common failure points |
| presentation (pages + widgets) | **40%** | UI tests are brittle; cover key interactions, not pixel layouts |

## 2. Naming Convention

Pattern: `should_[expected behavior]_when_[condition or action]`

**Good examples:**
```
should_return_user_when_credentials_are_valid
should_throw_cache_exception_when_local_storage_is_empty
should_emit_loading_then_success_when_fetch_completes
should_display_error_message_when_network_is_unavailable
should_navigate_to_home_when_login_succeeds
```

**Bad examples:**
```
test_login          # What about login? No expected behavior stated
user_test           # Not a behavior description, just a noun
should_work         # "Work" is not a verifiable outcome
```

## 3. What to Test per Layer

### Domain Layer
- **Use cases:** Given valid input, returns expected `Right` result. Given invalid input, returns expected `Left` failure. Verify the repository method is called with correct arguments.
- **Entities:** Validation logic, computed properties, equality (if using `Equatable`).
- **Repository interfaces:** Test through mocks — verify the contract is called correctly by use cases.

```dart
// Example: testing a use case
test('should_return_account_balance_when_account_exists', () async {
  when(mockRepo.getBalance('acc-1')).thenAnswer((_) async => const Right(1500.0));
  final result = await getAccountBalance(const Params(accountId: 'acc-1'));
  expect(result, const Right(1500.0));
  verify(mockRepo.getBalance('acc-1')).called(1);
});
```

### Data Layer
- **Repositories:** Given remote datasource returns data, returns mapped entity. Given remote throws, tries local cache. Given both fail, returns Failure.
- **Models:** `fromJson` with valid JSON produces correct fields. `fromJson` with missing fields throws or uses defaults. `toJson` round-trips correctly.
- **Datasources:** Test with fake HTTP client, verify correct endpoints, headers, and error codes.

```dart
// Example: testing model parsing
test('should_parse_user_model_when_json_is_valid', () {
  final json = {'id': '1', 'name': 'Alice', 'email': 'alice@test.com'};
  final model = UserModel.fromJson(json);
  expect(model.id, '1');
  expect(model.name, 'Alice');
});
```

### Presentation Layer
- **Widgets:** Renders expected text/icons given a state. Tapping a button triggers the correct callback or state change. Loading/error/empty states render correctly.
- **State management:** Emits correct state sequence for a given event. Calls correct use case. Handles errors without crashing.

```dart
// Example: testing widget rendering
testWidgets('should_display_balance_when_state_is_loaded', (tester) async {
  await tester.pumpWidget(MaterialApp(home: BalanceCard(balance: 1500.0)));
  expect(find.text('\$1,500.00'), findsOneWidget);
});
```

## 4. Mock vs Fake Rule

| Use | When | Example |
|-----|------|---------|
| **Mock** | External services you don't control | API client, database driver, platform channels (camera, GPS), third-party SDKs |
| **Fake** | Internal implementations you can replicate | In-memory repository, fake local storage, stub navigation observer |

**Why it matters:** Mocks verify interactions ("was this method called?"). Fakes simulate behavior ("return this data"). Use mocks at boundaries, fakes for internal wiring.

```dart
// Mock: external API
class MockAuthRemoteDatasource extends Mock implements AuthRemoteDatasource {}

// Fake: internal implementation
class FakeLocalStorage implements LocalStorage {
  final _store = <String, String>{};
  @override
  Future<void> write(String key, String value) async => _store[key] = value;
  @override
  Future<String?> read(String key) async => _store[key];
}
```

## 5. Test File Structure

Test files **mirror** the `lib/` structure exactly. Every `lib/` file has a corresponding `test/` file.

```
test/
├── core/
│   ├── error/
│   │   └── failures_test.dart
│   ├── network/
│   │   └── api_client_test.dart
│   └── utils/
│       └── validators_test.dart
├── features/
│   └── auth/
│       ├── data/
│       │   ├── datasources/
│       │   │   └── auth_remote_datasource_test.dart
│       │   ├── models/
│       │   │   └── user_model_test.dart
│       │   └── repositories/
│       │       └── auth_repository_impl_test.dart
│       ├── domain/
│       │   └── usecases/
│       │       └── login_user_test.dart
│       └── presentation/
│           ├── pages/
│           │   └── login_page_test.dart
│           └── bloc/
│               └── auth_bloc_test.dart
└── helpers/
    ├── test_helpers.dart
    ├── mock_generators.dart
    └── fixtures/
        └── user_fixture.json
```

## 6. Setup Patterns

```dart
// Group related tests by behavior, not by method
group('AuthRepository', () {
  late AuthRepositoryImpl repository;
  late MockAuthRemoteDatasource mockRemote;
  late FakeLocalStorage fakeLocal;

  setUp(() {
    mockRemote = MockAuthRemoteDatasource();
    fakeLocal = FakeLocalStorage();
    repository = AuthRepositoryImpl(remote: mockRemote, local: fakeLocal);
  });

  tearDown(() {
    // Clean up resources that persist between tests
    fakeLocal.clear();
  });

  group('login', () {
    test('should_return_user_when_remote_succeeds', () async { /* ... */ });
    test('should_cache_user_when_remote_succeeds', () async { /* ... */ });
    test('should_return_server_failure_when_remote_throws', () async { /* ... */ });
  });
});
```

## 7. Async Testing

```dart
// Use async/await for Future-based tests
test('should_fetch_data', () async {
  final result = await useCase.execute();
  expect(result.isRight(), true);
});

// Widget tests: pump() advances one frame, pumpAndSettle() waits for all animations
testWidgets('should_show_loading_then_content', (tester) async {
  await tester.pumpWidget(MyApp());
  expect(find.byType(CircularProgressIndicator), findsOneWidget); // loading state

  await tester.pumpAndSettle(); // wait for async + animations
  expect(find.text('Content loaded'), findsOneWidget); // loaded state
});

// Stream-based: use expectLater with emitsInOrder
test('should_emit_states_in_order', () {
  expectLater(
    bloc.stream,
    emitsInOrder([AuthLoading(), AuthSuccess(user)]),
  );
  bloc.add(LoginRequested(email, password));
});
```

## 8. Common Test Utilities

Create these in `test/helpers/` to avoid repetition:

| File | Purpose | Contents |
|------|---------|----------|
| `test_helpers.dart` | Shared setup for widget tests | `buildTestableWidget()` wrapping MaterialApp + providers + navigation |
| `mock_generators.dart` | Centralized mock/fake creation | All `@GenerateMocks` annotations or manual mock classes in one place |
| `fixtures/` | JSON test data | Static JSON files loaded by model tests — no inline JSON strings |
| `pump_app.dart` | Helper to pump app with dependencies | Wraps widget in required providers, theme, and localization |

```dart
// test/helpers/test_helpers.dart
Widget buildTestableWidget(Widget child) {
  return MaterialApp(
    home: Scaffold(body: child),
  );
}

// test/helpers/fixtures — load JSON fixtures
String loadFixture(String name) {
  return File('test/helpers/fixtures/$name').readAsStringSync();
}
```

## 9. Red Flags — Bad Tests

1. **Testing implementation details** — Verifying that a private method was called internally rather than asserting on the output. If you refactor internals, these tests break for no reason.
2. **No assertions** — A test that calls a function but never `expect()`s anything. It passes even if the code is broken. Every test must assert.
3. **Testing the framework** — Writing a test that `ElevatedButton` renders. The framework already guarantees that. Test *your* behavior: what happens when the button is tapped.
4. **Giant arrange blocks** — If setup is 30 lines and the assertion is 1 line, the test is doing too much. Split into smaller focused tests or extract setup into helpers.
5. **Flaky async tests** — Tests that sometimes pass and sometimes fail because they rely on timing rather than deterministic state. Use `pumpAndSettle()`, `completer.complete()`, or explicit state waits instead of `Future.delayed`.

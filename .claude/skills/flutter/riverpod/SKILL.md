---
name: riverpod
description: Riverpod state management pattern for Flutter.
  Use when building new projects, managing complex async state, or needing compile-safe DI.
  Preloaded into agents when project uses riverpod.
user-invocable: false
disable-model-invocation: true
---

# Riverpod State Management

## 1. When to Use

- New Flutter projects — Riverpod is the default recommendation
- Complex async state: fetching, caching, pagination, optimistic updates
- Compile-safe dependency injection without `BuildContext`
- Features that need to share state across unrelated widget trees
- Projects that benefit from code generation for reduced boilerplate

## 2. When NOT to Use

- Trivially simple apps with 1-2 screens and no async state (plain `StatefulWidget` is enough)
- Team has zero Riverpod experience and delivery deadline is tight (use what the team knows)
- Legacy codebase deeply invested in Provider — migrate incrementally, don't rewrite

## 3. Dependencies

Add via CLI to always get the latest versions:
```bash
flutter pub add flutter_riverpod riverpod_annotation
flutter pub add --dev riverpod_generator build_runner
```

Run codegen after defining providers:
```bash
dart run build_runner build --delete-conflicting-outputs
```

## 4. Folder Structure

```
lib/features/[feature]/presentation/
├── pages/
│   └── [feature]_page.dart
├── widgets/
│   └── [feature]_list.dart
├── providers/
│   └── [feature]_providers.dart      # Generated providers (codegen output)
└── notifiers/
    └── [feature]_notifier.dart       # AsyncNotifier / Notifier classes
```

## 5. Core Patterns

### AsyncNotifier — Async Operations (CRUD)

Use `AsyncNotifier` for any state that involves fetching, creating, updating, or deleting data.

```dart
// lib/features/transaction/presentation/notifiers/transaction_notifier.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../domain/entities/transaction.dart';
import '../../domain/usecases/get_transactions.dart';
import '../../domain/usecases/create_transaction.dart';

part 'transaction_notifier.g.dart';

@riverpod
class TransactionNotifier extends _$TransactionNotifier {
  @override
  Future<List<Transaction>> build() async {
    // build() is called on first read — fetch initial data here
    final getTransactions = ref.read(getTransactionsUseCaseProvider);
    final result = await getTransactions();
    return result.fold(
      (failure) => throw failure,
      (transactions) => transactions,
    );
  }

  Future<void> create(CreateTransactionParams params) async {
    state = const AsyncLoading();
    final createTransaction = ref.read(createTransactionUseCaseProvider);
    final result = await createTransaction(params);
    result.fold(
      (failure) => state = AsyncError(failure, StackTrace.current),
      (transaction) => state = AsyncData([...state.valueOrNull ?? [], transaction]),
    );
  }

  Future<void> delete(String id) async {
    // Optimistic delete — remove from list first, restore on failure
    final previous = state.valueOrNull ?? [];
    state = AsyncData(previous.where((t) => t.id != id).toList());

    final deleteTransaction = ref.read(deleteTransactionUseCaseProvider);
    final result = await deleteTransaction(id);
    result.fold(
      (failure) {
        state = AsyncData(previous); // Restore on failure
      },
      (_) {}, // Success — already removed
    );
  }
}
```

### Notifier — Synchronous State

Use `Notifier` for state that doesn't involve async operations.

```dart
@riverpod
class ThemeMode extends _$ThemeMode {
  @override
  ThemeMode build() => ThemeMode.light;

  void toggle() {
    state = state == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
  }
}
```

### ref.watch vs ref.read vs ref.listen

| Method | Where | When | Example |
|--------|-------|------|---------|
| `ref.watch` | Inside `build()` methods | Reactively rebuild when state changes | `final transactions = ref.watch(transactionNotifierProvider);` |
| `ref.read` | Inside callbacks, event handlers | One-time read, no rebuild | `onPressed: () => ref.read(transactionNotifierProvider.notifier).create(params)` |
| `ref.listen` | Inside `build()` or Notifier | Side effects (navigation, snackbar) without rebuild | `ref.listen(authProvider, (prev, next) { if (next is Unauthenticated) context.go('/login'); });` |

### Provider Scoping

```dart
// main.dart — wrap entire app
void main() {
  runApp(const ProviderScope(child: MyApp()));
}

// Override providers for testing or per-screen scope
ProviderScope(
  overrides: [
    apiClientProvider.overrideWithValue(MockApiClient()),
  ],
  child: const MyApp(),
)
```

### Family Providers — Parameterized

```dart
@riverpod
Future<Transaction> transactionDetail(Ref ref, String transactionId) async {
  final repo = ref.read(transactionRepositoryProvider);
  final result = await repo.getById(transactionId);
  return result.fold((f) => throw f, (t) => t);
}

// Usage in widget:
final detail = ref.watch(transactionDetailProvider('txn-123'));
```

### Invalidation and Refreshing

```dart
// Force a provider to re-fetch its data
ref.invalidate(transactionNotifierProvider);

// Refresh and get the new value
final newValue = await ref.refresh(transactionNotifierProvider.future);
```

## 6. Error Handling with AsyncValue

Always handle all three states. Never just extract `.value` — it's null during loading and error.

```dart
class TransactionPage extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final transactionsAsync = ref.watch(transactionNotifierProvider);

    return transactionsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => ErrorState(
        message: error.toString(),
        onRetry: () => ref.invalidate(transactionNotifierProvider),
      ),
      data: (transactions) => transactions.isEmpty
          ? const EmptyState(message: 'No transactions yet')
          : ListView.builder(
              itemCount: transactions.length,
              itemBuilder: (context, index) => TransactionTile(transactions[index]),
            ),
    );
  }
}
```

## 7. Testing

```dart
// Use ProviderContainer for unit tests (no Flutter dependency)
test('should_load_transactions_when_initialized', () async {
  final container = ProviderContainer(
    overrides: [
      transactionRepositoryProvider.overrideWithValue(MockTransactionRepository()),
    ],
  );
  addTearDown(container.dispose);

  // Wait for the async build to complete
  await container.read(transactionNotifierProvider.future);
  final state = container.read(transactionNotifierProvider);

  expect(state.valueOrNull, isNotEmpty);
});

// Widget test with ProviderScope overrides
testWidgets('should_display_transactions', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        transactionNotifierProvider.overrideWith(() => FakeTransactionNotifier()),
      ],
      child: const MaterialApp(home: TransactionPage()),
    ),
  );
  await tester.pumpAndSettle();
  expect(find.byType(TransactionTile), findsWidgets);
});
```

## 8. Anti-patterns

| Anti-pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| `ref.read` inside `build()` | Reads once, never rebuilds on change — UI goes stale | Use `ref.watch` for reactive state in `build()` |
| Not handling loading/error in `AsyncValue` | Crashes or shows blank screen | Always use `.when()` or `switch` on all three states |
| `StateProvider` for complex state | No encapsulation, state logic leaks into UI | Use `Notifier` or `AsyncNotifier` with methods |
| Creating providers inside widgets | New provider on every rebuild, loses state | Define providers at top level or in a dedicated file |
| Watching too many providers in one widget | Entire widget rebuilds on any change | Split into smaller widgets, each watching one provider |

## 9. Migration from Provider to Riverpod (5 Steps)

1. **Add dependencies** — add `flutter_riverpod` alongside existing `provider`. Both can coexist.
2. **Wrap app in ProviderScope** — add `ProviderScope` at the root, above existing `MultiProvider`.
3. **Convert one feature at a time** — start with the simplest feature. Convert its `ChangeNotifier` to a `Notifier` or `AsyncNotifier`.
4. **Replace Consumer/context.watch** — change `Consumer<T>` to Riverpod's `ConsumerWidget` or `Consumer`. Replace `context.watch<T>()` with `ref.watch(provider)`.
5. **Remove old providers** — once all features are converted, remove `provider` dependency and the `MultiProvider` wrapper.

Do not convert all features at once. Ship each feature conversion independently.

---
name: provider
description: Provider state management pattern for Flutter.
  Use when maintaining existing Provider-based codebases or for simple DI.
  Preloaded into agents when project uses provider.
user-invocable: false
disable-model-invocation: true
---

# Provider State Management

## 1. When to Use

- Maintaining an existing codebase that already uses Provider
- Simple dependency injection where full Riverpod is overkill
- Apps with straightforward state: a few ChangeNotifiers, minimal async complexity

## 2. When NOT to Use

- **New projects** — use Riverpod instead. Provider's author (Remi Rousselet) created Riverpod as its successor
- Complex async state: Provider has no built-in `AsyncValue`, making loading/error handling manual
- Performance-critical features: Provider rebuilds entire Consumer subtrees unless you use Selector carefully

## 3. Dependencies

Add via CLI to always get the latest version:
```bash
flutter pub add provider
```

## 4. Folder Structure

```
lib/features/[feature]/presentation/
├── providers/
│   └── [feature]_provider.dart    # ChangeNotifier class
├── pages/
│   └── [feature]_page.dart
└── widgets/
    └── [feature]_item.dart
```

## 5. Core Patterns

### ChangeNotifier with notifyListeners()

```dart
// lib/features/cart/presentation/providers/cart_provider.dart
import 'package:flutter/foundation.dart';
import '../../../domain/entities/cart_item.dart';
import '../../../domain/usecases/add_to_cart.dart';
import '../../../domain/usecases/remove_from_cart.dart';

class CartProvider extends ChangeNotifier {
  CartProvider({
    required AddToCart addToCart,
    required RemoveFromCart removeFromCart,
  })  : _addToCart = addToCart,
        _removeFromCart = removeFromCart;

  final AddToCart _addToCart;
  final RemoveFromCart _removeFromCart;

  List<CartItem> _items = [];
  bool _isLoading = false;
  String? _error;

  List<CartItem> get items => List.unmodifiable(_items);
  bool get isLoading => _isLoading;
  String? get error => _error;
  double get total => _items.fold(0, (sum, item) => sum + item.price * item.quantity);
  int get itemCount => _items.length;

  Future<void> addItem(CartItem item) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final result = await _addToCart(item);
    result.fold(
      (failure) {
        _error = failure.message;
      },
      (updatedCart) {
        _items = updatedCart;
      },
    );

    _isLoading = false;
    notifyListeners();
  }

  Future<void> removeItem(String itemId) async {
    // Optimistic removal
    final previous = List<CartItem>.from(_items);
    _items.removeWhere((item) => item.id == itemId);
    notifyListeners();

    final result = await _removeFromCart(itemId);
    result.fold(
      (failure) {
        _items = previous; // Restore on failure
        _error = failure.message;
        notifyListeners();
      },
      (_) {}, // Already removed
    );
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
```

### Consumer\<T\> for Rebuilding Widgets

```dart
class CartPage extends StatelessWidget {
  const CartPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cart')),
      body: Consumer<CartProvider>(
        builder: (context, cart, child) {
          if (cart.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (cart.error != null) {
            return ErrorState(
              message: cart.error!,
              onRetry: () => cart.clearError(),
            );
          }
          if (cart.items.isEmpty) {
            return const EmptyState(message: 'Your cart is empty');
          }
          return ListView.builder(
            itemCount: cart.items.length,
            itemBuilder: (_, index) => CartItemTile(cart.items[index]),
          );
        },
      ),
    );
  }
}
```

### Selector\<T, S\> for Partial State (Performance)

`Selector` rebuilds only when the selected value changes — not on every `notifyListeners()`.

```dart
// Only rebuilds when itemCount changes, not when items themselves change
Selector<CartProvider, int>(
  selector: (_, cart) => cart.itemCount,
  builder: (_, count, __) => Badge(
    label: Text('$count'),
    child: const Icon(Icons.shopping_cart),
  ),
)

// Only rebuilds when total changes
Selector<CartProvider, double>(
  selector: (_, cart) => cart.total,
  builder: (_, total, __) => Text('\$${total.toStringAsFixed(2)}'),
)
```

### context.read vs context.watch vs context.select

| Method | Rebuilds Widget? | Use In | Example |
|--------|-----------------|--------|---------|
| `context.read<T>()` | No | Callbacks, `onPressed`, `initState` | `onPressed: () => context.read<CartProvider>().removeItem(id)` |
| `context.watch<T>()` | Yes, on any change | `build()` method | `final cart = context.watch<CartProvider>();` |
| `context.select<T, S>()` | Yes, only when selected value changes | `build()` method, for performance | `final count = context.select<CartProvider, int>((c) => c.itemCount);` |

**Rule:** Use `context.read` in callbacks. Use `context.watch` or `context.select` in `build()`. Never use `context.watch` in callbacks — it throws.

### MultiProvider at App Level

```dart
// main.dart
MultiProvider(
  providers: [
    ChangeNotifierProvider(create: (_) => CartProvider(
      addToCart: getIt<AddToCart>(),
      removeFromCart: getIt<RemoveFromCart>(),
    )),
    ChangeNotifierProvider(create: (_) => AuthProvider(
      loginUser: getIt<LoginUser>(),
    )),
    // Non-ChangeNotifier providers for DI
    Provider(create: (_) => getIt<ApiClient>()),
  ],
  child: const MyApp(),
)
```

## 6. Performance — Why and How to Use Selector

`Consumer<CartProvider>` rebuilds every time `notifyListeners()` is called — even if the specific data that widget needs hasn't changed. In a cart with frequent updates, this causes unnecessary rebuilds.

```dart
// WRONG — rebuilds on every notifyListeners(), even if total hasn't changed
Consumer<CartProvider>(
  builder: (_, cart, __) => Text('Total: \$${cart.total.toStringAsFixed(2)}'),
)

// RIGHT — rebuilds only when total value actually changes
Selector<CartProvider, double>(
  selector: (_, cart) => cart.total,
  builder: (_, total, __) => Text('Total: \$${total.toStringAsFixed(2)}'),
)
```

**When to use Selector:**
- Widgets that read one or two fields from a large ChangeNotifier
- Badge counts, totals, status indicators
- Any widget that appears in a list (each item should select only its own data)

## 7. Testing

```dart
// Widget test with mock provider
testWidgets('should_display_cart_items', (tester) async {
  final mockCartProvider = MockCartProvider();
  when(() => mockCartProvider.items).thenReturn(testCartItems);
  when(() => mockCartProvider.isLoading).thenReturn(false);
  when(() => mockCartProvider.error).thenReturn(null);

  await tester.pumpWidget(
    MaterialApp(
      home: ChangeNotifierProvider<CartProvider>.value(
        value: mockCartProvider,
        child: const CartPage(),
      ),
    ),
  );

  expect(find.byType(CartItemTile), findsNWidgets(testCartItems.length));
});

// Unit test ChangeNotifier directly
test('should_add_item_and_update_total', () async {
  final provider = CartProvider(
    addToCart: mockAddToCart,
    removeFromCart: mockRemoveFromCart,
  );

  when(() => mockAddToCart(any())).thenAnswer(
    (_) async => Right([testCartItem]),
  );

  await provider.addItem(testCartItem);

  expect(provider.items, contains(testCartItem));
  expect(provider.isLoading, false);
  expect(provider.error, isNull);
});
```

## 8. Migration Path to Riverpod

Migrate incrementally. Both packages coexist without conflict.

| Step | Action | Details |
|------|--------|---------|
| 1 | Add Riverpod dependency | Add `flutter_riverpod` to pubspec.yaml alongside `provider` |
| 2 | Wrap app in ProviderScope | Add `ProviderScope` above `MultiProvider` — both work simultaneously |
| 3 | Convert one feature | Pick the simplest feature. Replace its `ChangeNotifier` with a Riverpod `Notifier` or `AsyncNotifier`. Replace `Consumer<T>` with `ConsumerWidget` |
| 4 | Update widget reads | Replace `context.watch<T>()` with `ref.watch(provider)`. Replace `context.read<T>()` with `ref.read(provider)` |
| 5 | Remove old provider | Remove the `ChangeNotifierProvider` entry from `MultiProvider`. Once all features are converted, remove `provider` from pubspec.yaml |

## 9. Anti-patterns

| Anti-pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| Calling `notifyListeners()` on every field set | 5 field updates = 5 rebuilds per frame | Batch updates: set all fields, call `notifyListeners()` once at the end |
| Accessing `context` inside ChangeNotifier | ChangeNotifier should not know about the widget tree | Pass callbacks or use cases through the constructor, not context |
| Manually disposing providers | `ChangeNotifierProvider` handles disposal; manual dispose causes use-after-dispose | Let the Provider widget manage lifecycle |
| Using `Provider.of<T>(context)` everywhere | Verbose and easy to forget `listen: false` | Use `context.read<T>()` (no listen) or `context.watch<T>()` (listen) |
| Storing UI state in ChangeNotifier | Scroll position, text field values, tab index are widget concerns | Use `StatefulWidget` for ephemeral UI state; ChangeNotifier is for shared app state |

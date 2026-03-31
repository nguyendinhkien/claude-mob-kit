---
name: cubit
description: Cubit state management pattern for Flutter.
  Use when features need simpler state than Bloc with no complex event transformation.
  Preloaded into agents when project uses cubit.
user-invocable: false
disable-model-invocation: true
---

# Cubit State Management

## 1. When to Use

- Features with straightforward state transitions: fetch, display, retry
- Teams new to the BLoC pattern — Cubit is the simpler entry point
- CRUD operations: list items, create item, update item, delete item
- When you want Bloc's structure (sealed states, BlocBuilder) without event boilerplate

## 2. When NOT to Use

- Features needing event transformation: debounce on search, throttle on scroll
- When event traceability is required for audit logging or debugging
- When multiple distinct inputs should trigger the same transition differently (use Bloc events instead)

## 3. Dependencies

Add via CLI to always get the latest versions:
```bash
flutter pub add flutter_bloc bloc equatable
flutter pub add --dev bloc_test
```

## 4. Folder Structure

```
lib/features/[feature]/presentation/
├── cubit/
│   ├── [feature]_cubit.dart     # Cubit class with methods
│   └── [feature]_state.dart     # Sealed state class
├── pages/
│   └── [feature]_page.dart
└── widgets/
    └── [feature]_card.dart
```

## 5. Core Patterns

### State — Sealed Class

Identical to Bloc states. Define all possible UI states.

```dart
// lib/features/product/presentation/cubit/product_state.dart
import 'package:equatable/equatable.dart';
import '../../../domain/entities/product.dart';

sealed class ProductState extends Equatable {
  const ProductState();

  @override
  List<Object?> get props => [];
}

final class ProductInitial extends ProductState {
  const ProductInitial();
}

final class ProductLoading extends ProductState {
  const ProductLoading();
}

final class ProductLoaded extends ProductState {
  const ProductLoaded({required this.products});
  final List<Product> products;

  @override
  List<Object?> get props => [products];
}

final class ProductError extends ProductState {
  const ProductError({required this.message});
  final String message;

  @override
  List<Object?> get props => [message];
}
```

### Cubit — Methods That Call emit()

No events, no `on<Event>` handlers. Just methods.

```dart
// lib/features/product/presentation/cubit/product_cubit.dart
import 'package:bloc/bloc.dart';
import '../../../domain/usecases/get_products.dart';
import '../../../domain/usecases/delete_product.dart';
import 'product_state.dart';

class ProductCubit extends Cubit<ProductState> {
  ProductCubit({
    required GetProducts getProducts,
    required DeleteProduct deleteProduct,
  })  : _getProducts = getProducts,
        _deleteProduct = deleteProduct,
        super(const ProductInitial());

  final GetProducts _getProducts;
  final DeleteProduct _deleteProduct;

  Future<void> fetchProducts() async {
    emit(const ProductLoading());
    final result = await _getProducts();
    result.fold(
      (failure) => emit(ProductError(message: failure.message)),
      (products) => emit(ProductLoaded(products: products)),
    );
  }

  Future<void> deleteProduct(String id) async {
    final currentState = state;
    if (currentState is! ProductLoaded) return;

    // Optimistic delete
    final updated = currentState.products.where((p) => p.id != id).toList();
    emit(ProductLoaded(products: updated));

    final result = await _deleteProduct(id);
    result.fold(
      (failure) {
        // Restore on failure
        emit(currentState);
      },
      (_) {}, // Already removed
    );
  }

  Future<void> refresh() async {
    // Don't show loading spinner on pull-to-refresh — keep current data visible
    final result = await _getProducts();
    result.fold(
      (failure) {
        // Keep current data, just show error message
        if (state is ProductLoaded) return;
        emit(ProductError(message: failure.message));
      },
      (products) => emit(ProductLoaded(products: products)),
    );
  }
}
```

### emit() Rules

1. **Never emit after close()** — guard async gaps:
```dart
Future<void> fetchData() async {
  emit(const Loading());
  final result = await _repository.getData();
  // Cubit may have been closed while awaiting
  if (isClosed) return;
  result.fold(
    (f) => emit(Error(message: f.message)),
    (d) => emit(Loaded(data: d)),
  );
}
```

2. **Always emit a new instance** — Bloc deduplicates identical states by value (Equatable), so changing a field and re-emitting works. But emitting the same instance with no field changes does nothing.

3. **Don't call emit synchronously in sequence without a reason** — only the last emit will be rendered. Intermediate states are only useful with async gaps between them.

### BlocBuilder for UI

```dart
class ProductPage extends StatelessWidget {
  const ProductPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Products')),
      body: BlocBuilder<ProductCubit, ProductState>(
        builder: (context, state) {
          return switch (state) {
            ProductInitial() => const SizedBox.shrink(),
            ProductLoading() => const Center(child: CircularProgressIndicator()),
            ProductError(:final message) => ErrorState(
                message: message,
                onRetry: () => context.read<ProductCubit>().fetchProducts(),
              ),
            ProductLoaded(:final products) => products.isEmpty
                ? const EmptyState(message: 'No products found')
                : RefreshIndicator(
                    onRefresh: () => context.read<ProductCubit>().refresh(),
                    child: ListView.builder(
                      itemCount: products.length,
                      itemBuilder: (_, i) => ProductCard(products[i]),
                    ),
                  ),
          };
        },
      ),
    );
  }
}
```

### BlocListener for Side Effects

```dart
BlocListener<ProductCubit, ProductState>(
  listener: (context, state) {
    if (state is ProductError) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.message)),
      );
    }
  },
  child: const ProductListView(),
)
```

## 6. Testing

```dart
import 'package:bloc_test/bloc_test.dart';

blocTest<ProductCubit, ProductState>(
  'should_emit_loading_then_loaded_when_fetch_succeeds',
  build: () {
    when(() => mockGetProducts()).thenAnswer(
      (_) async => Right(testProducts),
    );
    return ProductCubit(
      getProducts: mockGetProducts,
      deleteProduct: mockDeleteProduct,
    );
  },
  act: (cubit) => cubit.fetchProducts(),
  expect: () => [
    const ProductLoading(),
    ProductLoaded(products: testProducts),
  ],
);

blocTest<ProductCubit, ProductState>(
  'should_remove_product_optimistically_when_delete_called',
  build: () {
    when(() => mockDeleteProduct(any())).thenAnswer((_) async => const Right(null));
    return ProductCubit(
      getProducts: mockGetProducts,
      deleteProduct: mockDeleteProduct,
    );
  },
  seed: () => ProductLoaded(products: testProducts),
  act: (cubit) => cubit.deleteProduct('product-1'),
  expect: () => [
    ProductLoaded(products: testProducts.where((p) => p.id != 'product-1').toList()),
  ],
);
```

## 7. When to Upgrade from Cubit to Bloc

Upgrade when you hit any of these 3 signals:

1. **You need debounce or throttle** — a search field fires on every keystroke and you need to wait 300ms before fetching. Cubit has no event transformer. Bloc does:
```dart
on<SearchChanged>(_onSearch, transformer: debounce(const Duration(milliseconds: 300)));
```

2. **You need to distinguish how a state was reached** — the same "loaded" state can come from initial fetch, pull-to-refresh, or pagination. With Cubit, you'd need separate methods that emit the same state. With Bloc, each has its own event and handler.

3. **You need event replay or event sourcing** — replaying events for debugging or undo. Cubit methods are fire-and-forget. Bloc events can be stored and replayed.

## 8. Anti-patterns

| Anti-pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| Calling `emit()` in the constructor | Cubit isn't fully initialized, can cause undefined behavior | Call initial fetch from the widget: `context.read<ProductCubit>().fetchProducts()` in `initState` or via `BlocProvider` create callback |
| Making `emit` public or exposing it | External callers can emit arbitrary states, bypassing business logic | `emit` is protected by default — never wrap it in a public method that takes a state |
| Putting domain logic in the Cubit | Cubit becomes a God class; violates Clean Architecture | Cubit calls use cases, which contain the logic. Cubit only maps results to states |
| Not using `isClosed` guard after await | `emit` after `close()` throws a `StateError` | Check `if (isClosed) return;` after every `await` |
| Multiple Cubits for tightly coupled state | Two Cubits that always change together create sync bugs | Merge into one Cubit or coordinate via a shared use case |

---
name: flutter-widget
description: Widget patterns and rules for Flutter apps following Clean Architecture.
  Auto-loads when working with Dart files.
paths: "lib/**/*.dart, test/**/*.dart"
allowed-tools: Read, Write, Edit, Bash(flutter *)
---

# Flutter Widget Patterns

## 1. Widget Type Decision Tree

```
Do you need local mutable state (TextEditingController, AnimationController, toggle)?
├── NO → StatelessWidget
└── YES
    ├── Using flutter_hooks? → HookWidget
    └── Not using hooks? → StatefulWidget
```

| Type | Use When | Example |
|------|----------|---------|
| `StatelessWidget` | Widget output depends only on constructor args and inherited state (provider/bloc) | Display cards, labels, layout wrappers |
| `StatefulWidget` | Widget needs local state: controllers, toggles, animation, form fields | Pages with TextEditingController, TabController, scroll listeners |
| `HookWidget` | Project uses `flutter_hooks`; replaces StatefulWidget for common patterns | Replacing boilerplate initState/dispose with `useTextEditingController()` |

## 2. Mandatory Patterns

### const Constructor — Always

Every widget must have a `const` constructor if all fields are final. Without it, Flutter can't optimize rebuilds.

```dart
// CORRECT
class BalanceCard extends StatelessWidget {
  const BalanceCard({super.key, required this.balance});
  final double balance;

  @override
  Widget build(BuildContext context) => Text('\$${balance.toStringAsFixed(2)}');
}

// WRONG — missing const: compile warning, lost optimization
class BalanceCard extends StatelessWidget {
  BalanceCard({super.key, required this.balance}); // Missing const!
  final double balance;

  @override
  Widget build(BuildContext context) => Text('\$${balance.toStringAsFixed(2)}');
}
```

### key Parameter

Always provide `key` for:
- Items in `ListView.builder` → use a stable ID, never index
- Conditionally rendered widgets that swap positions
- Widgets in `AnimatedSwitcher`

```dart
ListView.builder(
  itemCount: transactions.length,
  itemBuilder: (_, index) {
    final txn = transactions[index];
    return TransactionTile(key: ValueKey(txn.id), transaction: txn);
  },
)
```

### Composition Over Inheritance

Never extend another widget. Wrap it instead.

```dart
// WRONG — inheriting from another widget
class PrimaryButton extends ElevatedButton { ... }

// CORRECT — composing
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.label, required this.onPressed});
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        minimumSize: const Size.fromHeight(48),
        backgroundColor: Theme.of(context).colorScheme.primary,
      ),
      child: Text(label),
    );
  }
}
```

## 3. Widget Decomposition Rules

**Extract a widget when:**
- The `build()` method exceeds ~100 lines
- The same widget structure appears in 2+ places
- The widget has a clear, nameable responsibility (e.g., `TransactionHeader`, `AmountInput`)

**Do NOT extract:**
- Purely for line count — 80 lines of straightforward layout is fine as one widget
- Private helper methods that return widgets — extract as a separate widget class instead (helper methods don't get their own rebuild boundary)

```dart
// WRONG — helper method doesn't get a rebuild boundary
Widget _buildHeader() => Text(title);

// CORRECT — separate widget with its own build lifecycle
class _TransactionHeader extends StatelessWidget {
  const _TransactionHeader({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) => Text(title);
}
```

## 4. Code Examples

### Correct StatelessWidget

```dart
// lib/features/account/presentation/widgets/account_balance_card.dart
import 'package:flutter/material.dart';
import '../../domain/entities/account.dart';

class AccountBalanceCard extends StatelessWidget {
  const AccountBalanceCard({super.key, required this.account});
  final Account account;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(account.name, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              '\$${account.balance.toStringAsFixed(2)}',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

### Correct StatefulWidget with Proper dispose()

```dart
// lib/features/search/presentation/widgets/search_input.dart
import 'package:flutter/material.dart';

class SearchInput extends StatefulWidget {
  const SearchInput({super.key, required this.onChanged});
  final ValueChanged<String> onChanged;

  @override
  State<SearchInput> createState() => _SearchInputState();
}

class _SearchInputState extends State<SearchInput> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
    _focusNode = FocusNode();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() => widget.onChanged(_controller.text);

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _controller,
      focusNode: _focusNode,
      decoration: const InputDecoration(
        hintText: 'Search...',
        prefixIcon: Icon(Icons.search),
        border: OutlineInputBorder(),
      ),
    );
  }
}
```

### Page Widget — Uses UseCase via State Management

```dart
// lib/features/transaction/presentation/pages/transaction_list_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../bloc/transaction_bloc.dart';
import '../bloc/transaction_state.dart';
import '../widgets/transaction_tile.dart';

class TransactionListPage extends StatelessWidget {
  const TransactionListPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Transactions')),
      body: BlocBuilder<TransactionBloc, TransactionState>(
        builder: (context, state) {
          return switch (state) {
            TransactionInitial() => const SizedBox.shrink(),
            TransactionLoading() => const Center(child: CircularProgressIndicator()),
            TransactionError(:final message) => _ErrorView(
                message: message,
                onRetry: () => context.read<TransactionBloc>().add(const TransactionsFetched()),
              ),
            TransactionLoaded(:final transactions) => transactions.isEmpty
                ? const Center(child: Text('No transactions'))
                : ListView.builder(
                    itemCount: transactions.length,
                    itemBuilder: (_, i) => TransactionTile(
                      key: ValueKey(transactions[i].id),
                      transaction: transactions[i],
                    ),
                  ),
          };
        },
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 16),
          ElevatedButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
```

### Reusable Component — No Business Logic

```dart
// lib/features/shared/presentation/widgets/status_badge.dart
import 'package:flutter/material.dart';

class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12),
      ),
    );
  }
}
```

## 5. Presentation Layer Rules

| Rule | Violation Example | Fix |
|------|------------------|-----|
| No business logic in widgets | `if (balance > 1000) applyDiscount()` in `build()` | Move to use case: `ApplyDiscount` called from bloc/cubit |
| No direct API calls | `http.get('api/users')` in a widget | Call through use case → repository → datasource |
| No direct DB calls | `database.query('SELECT * FROM users')` in a widget | Same data layer flow via repository |
| Receive data via constructor or state management | `widget.fetchData()` calling API internally | Widget receives data, doesn't fetch it |

## 6. Performance Patterns

### const Placement

```dart
// Mark the ENTIRE subtree const when possible — not just individual widgets
return const Column(
  children: [
    Icon(Icons.check),     // Also const because parent is const
    SizedBox(height: 8),   // Also const
    Text('Done'),          // Also const
  ],
);
```

### Avoid Unnecessary Rebuilds

```dart
// WRONG — anonymous function creates new closure every build
ElevatedButton(
  onPressed: () => doSomething(),
  child: const Text('Tap'),
)

// BETTER for hot paths — reference a method directly
ElevatedButton(
  onPressed: _handleTap,
  child: const Text('Tap'),
)
```

### RepaintBoundary

```dart
// Wrap expensive subtrees that repaint independently
RepaintBoundary(
  child: CustomPaint(painter: ChartPainter(data: chartData)),
)
```

## 7. Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| `BuildContext` across async gaps | Context may be deactivated after await; crashes on use | Check `mounted` before using context, or use `BlocListener` for side effects |
| `setState()` after `dispose()` | Throws `setState() called after dispose()` | Check `mounted` or cancel async operations in `dispose()` |
| Logic in `build()` | `build()` runs 60fps; heavy logic causes jank | Pre-compute in state management layer, `build()` only renders |
| Deeply nested widget trees | 10+ levels of nesting is unreadable | Extract subtrees into named widget classes |
| Using `GlobalKey` for communication | Breaks encapsulation, causes tight coupling | Use state management or callbacks |

```dart
// WRONG — BuildContext across async gap
onPressed: () async {
  await Future.delayed(const Duration(seconds: 2));
  Navigator.of(context).pop(); // context may be invalid!
}

// CORRECT — guard with mounted check
onPressed: () async {
  await Future.delayed(const Duration(seconds: 2));
  if (!context.mounted) return;
  Navigator.of(context).pop();
}
```

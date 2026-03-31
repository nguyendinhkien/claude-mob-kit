---
name: mobile-architecture
description: Clean Architecture with Feature-first structure for mobile apps.
  Auto-loaded for all platforms. Use when creating features, reviewing structure,
  or deciding where code belongs.
user-invocable: true
---

# Mobile Architecture — Clean Architecture + Feature-first

## 1. The Rule

Every mobile project uses **Clean Architecture + Feature-first** organization. This is fixed. No alternatives, no debate, no "flat structure for small apps." The cost of restructuring later always exceeds the cost of starting correctly.

## 2. Mandatory Folder Structure

```
lib/
├── core/
│   ├── error/
│   │   ├── exceptions.dart        # Thrown by data layer
│   │   └── failures.dart          # Returned by domain layer (sealed class)
│   ├── network/
│   │   ├── api_client.dart        # HTTP client wrapper
│   │   ├── api_endpoints.dart     # All endpoint constants
│   │   └── network_info.dart      # Connectivity checker interface
│   ├── storage/
│   │   ├── local_storage.dart     # Key-value storage interface
│   │   └── secure_storage.dart    # Encrypted storage interface
│   └── utils/
│       ├── constants.dart         # App-wide constants
│       ├── extensions.dart        # Dart extension methods
│       └── validators.dart        # Input validation functions
├── features/
│   └── [feature_name]/
│       ├── data/
│       │   ├── datasources/
│       │   │   ├── [name]_remote_datasource.dart
│       │   │   └── [name]_local_datasource.dart
│       │   ├── models/
│       │   │   └── [name]_model.dart        # extends/implements Entity, has fromJson/toJson
│       │   └── repositories/
│       │       └── [name]_repository_impl.dart  # implements domain repository interface
│       ├── domain/
│       │   ├── entities/
│       │   │   └── [name].dart              # Pure Dart class, no dependencies
│       │   ├── repositories/
│       │   │   └── [name]_repository.dart   # Abstract class defining contract
│       │   └── usecases/
│       │       └── [verb]_[noun].dart       # Single responsibility use case
│       └── presentation/
│           ├── pages/
│           │   └── [name]_page.dart         # Full screen widget
│           ├── widgets/
│           │   └── [name]_widget.dart       # Reusable sub-components
│           └── [state_management]/          # bloc/ or providers/ or controllers/
│               └── [name]_[type].dart       # State management files
└── main.dart
```

## 3. Dependency Rule

Imports flow inward only: `presentation → domain ← data`. Domain never imports outward.

| Layer | CAN Import | CANNOT Import |
|-------|-----------|---------------|
| **domain** | `dart:core`, `equatable`, `dartz`/`fpdart` | Flutter, any package, data layer, presentation layer |
| **data** | domain entities + repository interfaces, http/dio, hive/sqflite, `dart:convert` | presentation layer, Flutter widgets |
| **presentation** | domain entities + use cases, Flutter, state management package | data layer directly (datasources, models, repository impls) |

**Violation example:** A page importing `UserModel` from data/models/ instead of `User` from domain/entities/. The page must only know about the domain entity.

## 4. Layer Responsibilities

| Layer | Responsibility | One-line Example |
|-------|---------------|-----------------|
| **Entity** | Business object with validation rules | `class Transaction { bool get isValid => amount > 0; }` |
| **Use Case** | Single business operation | `class GetAccountBalance { Future<Either<Failure, double>> call(String accountId); }` |
| **Repository (domain)** | Contract defining data operations | `abstract class AuthRepository { Future<Either<Failure, User>> login(String email, String password); }` |
| **Repository (data)** | Implements contract, coordinates datasources | `class AuthRepositoryImpl implements AuthRepository { /* tries remote, falls back to cache */ }` |
| **Model** | Serialization/deserialization of entities | `class UserModel extends User { factory UserModel.fromJson(Map<String, dynamic> json); }` |
| **Datasource** | Single data source access | `class AuthRemoteDatasource { Future<UserModel> login(String email, String password); }` |
| **Page** | Full screen, assembles widgets, connects to state | `class LoginPage extends StatelessWidget { /* reads AuthState, renders form */ }` |
| **Widget** | Reusable UI component | `class BalanceCard extends StatelessWidget { final double balance; }` |

## 5. Decision Guide — "Where Does This Code Belong?"

| Scenario | Belongs In | Why |
|----------|-----------|-----|
| Parsing a JSON response into an object | `data/models/` | Serialization is a data concern |
| Checking if a user can perform an action | `domain/usecases/` or `domain/entities/` | Business rule belongs in domain |
| Formatting a date for display | `presentation/` or `core/utils/` | Display formatting is a UI concern |
| Switching between API and cache | `data/repositories/` | Data source coordination is a data concern |
| Validating an email format | `core/utils/validators.dart` | Shared validation, not feature-specific |

## 6. New Feature vs Extend Existing

Create a **new feature** when:
- It has its own screen/route
- It has its own data source (different API endpoint or DB table)
- It can be developed, tested, and deployed independently

**Extend existing** when:
- It adds a sub-screen or dialog within an existing flow
- It reuses the same data source with minor additions
- Removing it does not affect the existing feature's functionality

## 7. core/ vs features/ Decision Rule

Put it in `core/` only if **two or more features** need it today — not "might need it someday."

- Network client, error types, storage interfaces → `core/` (used by all features)
- A utility function used by only one feature → keep it in that feature's folder
- When a second feature needs it → move it to `core/` at that point

## 8. Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| **Feature folder** | `snake_case`, noun | `features/user_profile/` |
| **Entity** | `PascalCase`, noun | `class Transaction` |
| **Use case** | `PascalCase`, verb_noun | `class GetTransactionHistory` |
| **Repository interface** | `PascalCase`, noun + Repository | `abstract class TransactionRepository` |
| **Repository impl** | `PascalCase`, noun + RepositoryImpl | `class TransactionRepositoryImpl` |
| **Model** | `PascalCase`, noun + Model | `class TransactionModel` |
| **Datasource** | `PascalCase`, noun + RemoteDatasource/LocalDatasource | `class TransactionRemoteDatasource` |
| **Page** | `PascalCase`, noun + Page | `class TransactionDetailPage` |
| **File names** | `snake_case.dart` | `get_transaction_history.dart` |
| **Test files** | `[name]_test.dart` | `get_transaction_history_test.dart` |

## 9. Red Flags — Architecture Violations

1. **A page imports from `data/`** — Presentation must go through domain. The page should depend on a use case, never a datasource or model directly.
2. **A use case imports Flutter** — Domain must be pure Dart. If you need `BuildContext` or `Widget`, the logic belongs in presentation.
3. **A repository returns a Model instead of an Entity** — The data layer must convert models to entities before returning. Domain should not know about JSON structure.
4. **Business logic lives in a widget's `build()` method** — Extract it to a use case or at minimum to the state management layer. Widgets render state, they don't compute it.
5. **`core/` contains feature-specific code** — If a utility class is only used by one feature, it belongs in that feature's folder, not in core.

---
name: flutter-local-storage
description: Local storage patterns for Flutter apps following Clean Architecture.
  Auto-loads when working with Dart files.
paths: "lib/**/*.dart, test/**/*.dart"
allowed-tools: Read, Write, Edit, Bash(flutter *)
---

# Flutter Local Storage

## 1. Storage Options Comparison

| Storage | Best For | Encrypted | Structured | Performance |
|---------|----------|-----------|------------|-------------|
| **SharedPreferences** | User preferences (theme, locale, flags) | No | No (key-value) | Fast for small data |
| **flutter_secure_storage** | Tokens, passwords, API keys, PII | Yes (Keychain/EncryptedSharedPrefs) | No (key-value) | Slower (encryption overhead) |
| **Hive** | Structured local data, offline-first cache | Optional (AES) | Yes (type adapters) | Very fast (binary) |
| **sqflite** | Complex relational data, queries with joins | No (app-level) | Yes (SQL tables) | Good for large datasets |
| **Isar** | Modern alternative to Hive, full-text search | Optional | Yes (schema) | Fastest (native binary) |

## 2. Decision Guide

| Scenario | Use | Why |
|----------|-----|-----|
| Store auth token | `flutter_secure_storage` | Must be encrypted at rest |
| Store user's theme preference | `SharedPreferences` | Non-sensitive, simple boolean |
| Cache API response for offline reading | `Hive` or `Isar` | Structured data, fast reads |
| Store chat message history | `sqflite` | Relational queries (by user, by date, search) |
| Store user's onboarding completion flag | `SharedPreferences` | Simple boolean, non-sensitive |
| Store credit card info | **Don't** — use tokenization | Never store payment data locally |
| Store 10,000+ searchable records | `Isar` | Full-text search, sorted queries, native speed |

## 3. Repository Pattern for Local Storage

Local storage is a data source. It lives in `data/datasources/`, never in presentation.

```
lib/features/[feature]/data/
├── datasources/
│   ├── [feature]_remote_datasource.dart   # API calls
│   └── [feature]_local_datasource.dart    # Local storage
├── models/
│   └── [feature]_model.dart
└── repositories/
    └── [feature]_repository_impl.dart     # Coordinates remote + local
```

## 4. Complete Examples

### SecureStorage Wrapper

```dart
// lib/core/storage/secure_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract class SecureStorage {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
  Future<void> deleteAll();
}

class SecureStorageImpl implements SecureStorage {
  const SecureStorageImpl({required this.storage});

  final FlutterSecureStorage storage;

  static const _options = AndroidOptions(encryptedSharedPreferences: true);

  @override
  Future<String?> read(String key) => storage.read(key: key, aOptions: _options);

  @override
  Future<void> write(String key, String value) =>
      storage.write(key: key, value: value, aOptions: _options);

  @override
  Future<void> delete(String key) => storage.delete(key: key, aOptions: _options);

  @override
  Future<void> deleteAll() => storage.deleteAll(aOptions: _options);
}
```

Install:
```bash
flutter pub add flutter_secure_storage
```

### Hive Box with Type Adapter

```dart
// lib/features/article/data/datasources/article_local_datasource.dart
import 'package:hive/hive.dart';
import '../models/article_model.dart';

abstract class ArticleLocalDataSource {
  Future<List<ArticleModel>> getCachedArticles();
  Future<void> cacheArticles(List<ArticleModel> articles);
  Future<void> clearCache();
}

class ArticleLocalDataSourceImpl implements ArticleLocalDataSource {
  const ArticleLocalDataSourceImpl({required this.box});
  final Box<ArticleModel> box;

  static const _cacheKey = 'cached_articles';
  static const _maxCacheAge = Duration(hours: 1);

  @override
  Future<List<ArticleModel>> getCachedArticles() async {
    final cached = box.values.toList();
    if (cached.isEmpty) throw const CacheException('No cached articles');
    return cached;
  }

  @override
  Future<void> cacheArticles(List<ArticleModel> articles) async {
    await box.clear();
    await box.addAll(articles);
  }

  @override
  Future<void> clearCache() async {
    await box.clear();
  }
}

// Type adapter — register in main.dart before runApp
@HiveType(typeId: 0)
class ArticleModel extends HiveObject {
  @HiveField(0)
  final String id;

  @HiveField(1)
  final String title;

  @HiveField(2)
  final String content;

  @HiveField(3)
  final DateTime publishedAt;

  ArticleModel({
    required this.id,
    required this.title,
    required this.content,
    required this.publishedAt,
  });
}
```

Install:
```bash
flutter pub add hive hive_flutter
flutter pub add --dev hive_generator build_runner
```

### SharedPreferences Wrapper (Typed)

```dart
// lib/core/storage/app_preferences.dart
import 'package:shared_preferences/shared_preferences.dart';

class AppPreferences {
  const AppPreferences({required this.prefs});
  final SharedPreferences prefs;

  // Theme
  bool get isDarkMode => prefs.getBool(_Keys.darkMode) ?? false;
  Future<void> setDarkMode(bool value) => prefs.setBool(_Keys.darkMode, value);

  // Locale
  String get locale => prefs.getString(_Keys.locale) ?? 'en';
  Future<void> setLocale(String value) => prefs.setString(_Keys.locale, value);

  // Onboarding
  bool get hasCompletedOnboarding => prefs.getBool(_Keys.onboarding) ?? false;
  Future<void> setOnboardingComplete() => prefs.setBool(_Keys.onboarding, true);

  // Clear all preferences
  Future<void> clear() => prefs.clear();
}

// Private key constants — never use magic strings elsewhere
abstract final class _Keys {
  static const darkMode = 'pref_dark_mode';
  static const locale = 'pref_locale';
  static const onboarding = 'pref_onboarding_complete';
}
```

Install:
```bash
flutter pub add shared_preferences
```

## 5. Offline-first Pattern

```dart
// lib/features/article/data/repositories/article_repository_impl.dart
class ArticleRepositoryImpl implements ArticleRepository {
  const ArticleRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
    required this.networkInfo,
  });

  final ArticleRemoteDataSource remoteDataSource;
  final ArticleLocalDataSource localDataSource;
  final NetworkInfo networkInfo;

  @override
  Future<Either<Failure, List<Article>>> getArticles() async {
    if (await networkInfo.isConnected) {
      try {
        // Fetch fresh data
        final articles = await remoteDataSource.getArticles();
        // Cache for offline use
        await localDataSource.cacheArticles(articles);
        return Right(articles);
      } on DioException catch (e) {
        // Network call failed — try cache
        return _fallbackToCache();
      }
    } else {
      // No network — serve from cache
      return _fallbackToCache();
    }
  }

  Future<Either<Failure, List<Article>>> _fallbackToCache() async {
    try {
      final cached = await localDataSource.getCachedArticles();
      return Right(cached);
    } on CacheException {
      return const Left(CacheFailure('No cached data available. Connect to the internet to load.'));
    }
  }
}
```

### Cache Invalidation Strategy

```dart
class CachePolicy {
  const CachePolicy({required this.maxAge});
  final Duration maxAge;

  static const articles = CachePolicy(maxAge: Duration(hours: 1));
  static const userProfile = CachePolicy(maxAge: Duration(minutes: 15));
  static const staticContent = CachePolicy(maxAge: Duration(days: 7));

  bool isExpired(DateTime cachedAt) {
    return DateTime.now().difference(cachedAt) > maxAge;
  }
}
```

### Conflict Resolution

```dart
// When offline changes conflict with server changes:
// 1. Last-write-wins: simplest, server always wins on sync
// 2. Merge: compare timestamps, keep newest per field
// 3. User prompt: show diff, let user choose

// Example: last-write-wins sync
Future<void> syncOfflineChanges() async {
  final pendingChanges = await localDataSource.getPendingChanges();
  for (final change in pendingChanges) {
    try {
      await remoteDataSource.push(change);
      await localDataSource.markSynced(change.id);
    } on ConflictException {
      // Server has newer version — discard local change, fetch server version
      final serverVersion = await remoteDataSource.getById(change.id);
      await localDataSource.overwrite(serverVersion);
    }
  }
}
```

## 6. Keys Management

```dart
// lib/core/storage/storage_keys.dart
// All storage keys in one file. Never use string literals elsewhere.
abstract final class StorageKeys {
  // Secure storage
  static const accessToken = 'secure_access_token';
  static const refreshToken = 'secure_refresh_token';
  static const userPin = 'secure_user_pin';

  // SharedPreferences
  static const darkMode = 'pref_dark_mode';
  static const locale = 'pref_locale';
  static const onboardingComplete = 'pref_onboarding_complete';
  static const lastSyncTimestamp = 'pref_last_sync';

  // Hive boxes
  static const articlesBox = 'box_articles';
  static const userBox = 'box_user';
}
```

## 7. Testing — In-Memory Fakes

```dart
// test/helpers/fake_secure_storage.dart
class FakeSecureStorage implements SecureStorage {
  final _store = <String, String>{};

  @override
  Future<String?> read(String key) async => _store[key];

  @override
  Future<void> write(String key, String value) async => _store[key] = value;

  @override
  Future<void> delete(String key) async => _store.remove(key);

  @override
  Future<void> deleteAll() async => _store.clear();
}

// test/helpers/fake_shared_preferences.dart
class FakeAppPreferences implements AppPreferences {
  bool _isDarkMode = false;
  String _locale = 'en';

  @override
  bool get isDarkMode => _isDarkMode;

  @override
  Future<void> setDarkMode(bool value) async => _isDarkMode = value;

  @override
  String get locale => _locale;

  @override
  Future<void> setLocale(String value) async => _locale = value;
}

// Usage in test
test('should_cache_articles_and_return_from_cache', () async {
  final fakeLocal = FakeArticleLocalDataSource();
  final repo = ArticleRepositoryImpl(
    remoteDataSource: mockRemote,
    localDataSource: fakeLocal,
    networkInfo: FakeNetworkInfo(isConnected: false),
  );

  // Pre-populate cache
  await fakeLocal.cacheArticles(testArticles);

  final result = await repo.getArticles();
  expect(result.isRight(), true);
});
```

## 8. Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| Storage access in presentation layer | Widget reads SharedPreferences directly, bypasses architecture | Access through repository → datasource chain only |
| Sensitive data in SharedPreferences | Tokens/passwords stored in plaintext XML file | Use `flutter_secure_storage` for anything sensitive |
| No cache invalidation | Stale data served forever, user sees outdated info | Implement `CachePolicy` with `maxAge` per data type |
| Storage operations in UI event handlers | `onPressed: () async { await prefs.setString(...); }` | Dispatch to state management layer, which calls the repository |
| Magic string keys | `prefs.getString('token')` scattered across files | Centralize in `StorageKeys` constants class |
| Not handling storage errors | App crashes if storage is full or corrupted | Wrap in try/catch, return `Failure`, show user-friendly message |

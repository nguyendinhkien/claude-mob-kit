---
name: flutter-networking
description: Dio-based networking patterns for Flutter apps following Clean Architecture.
  Auto-loads when working with Dart files.
paths: "lib/**/*.dart, test/**/*.dart"
allowed-tools: Read, Write, Edit, Bash(flutter *)
---

# Flutter Networking — Dio + Clean Architecture

## 1. Standard: Dio

Dio is the standard HTTP client. It supports interceptors, cancellation, timeouts, and FormData out of the box.

Install:
```bash
flutter pub add dio
```

## 2. Setup in Data Layer

### DioClient — core/network/

```dart
// lib/core/network/dio_client.dart
import 'package:dio/dio.dart';

class DioClient {
  DioClient({
    required String baseUrl,
    required List<Interceptor> interceptors,
  }) : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(seconds: 30),
            sendTimeout: const Duration(seconds: 30),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        )..interceptors.addAll(interceptors);

  final Dio _dio;

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) =>
      _dio.get(path, queryParameters: queryParameters, cancelToken: cancelToken);

  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    CancelToken? cancelToken,
  }) =>
      _dio.post(path, data: data, cancelToken: cancelToken);

  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    CancelToken? cancelToken,
  }) =>
      _dio.put(path, data: data, cancelToken: cancelToken);

  Future<Response<T>> delete<T>(
    String path, {
    CancelToken? cancelToken,
  }) =>
      _dio.delete(path, cancelToken: cancelToken);
}
```

### API Endpoints Constants

```dart
// lib/core/network/api_endpoints.dart
abstract final class ApiEndpoints {
  static const String baseUrl = 'https://api.example.com/v1';

  // Auth
  static const String login = '/auth/login';
  static const String refreshToken = '/auth/refresh';

  // Transactions
  static const String transactions = '/transactions';
  static String transactionById(String id) => '/transactions/$id';

  // User
  static const String profile = '/users/me';
}
```

## 3. Repository Pattern — Clean Architecture Connection

```
UseCase → Repository (domain interface) → RepositoryImpl (data) → RemoteDataSource → DioClient
```

### Remote DataSource

```dart
// lib/features/transaction/data/datasources/transaction_remote_datasource.dart
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../models/transaction_model.dart';

abstract class TransactionRemoteDataSource {
  Future<List<TransactionModel>> getTransactions();
  Future<TransactionModel> getTransactionById(String id);
  Future<TransactionModel> createTransaction(Map<String, dynamic> data);
}

class TransactionRemoteDataSourceImpl implements TransactionRemoteDataSource {
  const TransactionRemoteDataSourceImpl({required this.client});
  final DioClient client;

  @override
  Future<List<TransactionModel>> getTransactions() async {
    final response = await client.get(ApiEndpoints.transactions);
    final list = response.data['data'] as List;
    return list.map((json) => TransactionModel.fromJson(json as Map<String, dynamic>)).toList();
  }

  @override
  Future<TransactionModel> getTransactionById(String id) async {
    final response = await client.get(ApiEndpoints.transactionById(id));
    return TransactionModel.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  @override
  Future<TransactionModel> createTransaction(Map<String, dynamic> data) async {
    final response = await client.post(ApiEndpoints.transactions, data: data);
    return TransactionModel.fromJson(response.data['data'] as Map<String, dynamic>);
  }
}
```

### Domain Repository Interface

```dart
// lib/features/transaction/domain/repositories/transaction_repository.dart
import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../entities/transaction.dart';

abstract class TransactionRepository {
  Future<Either<Failure, List<Transaction>>> getTransactions();
  Future<Either<Failure, Transaction>> getTransactionById(String id);
  Future<Either<Failure, Transaction>> createTransaction(CreateTransactionParams params);
}
```

### Repository Implementation

```dart
// lib/features/transaction/data/repositories/transaction_repository_impl.dart
import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';
import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/network/network_info.dart';
import '../../domain/entities/transaction.dart';
import '../../domain/repositories/transaction_repository.dart';
import '../datasources/transaction_remote_datasource.dart';
import '../datasources/transaction_local_datasource.dart';

class TransactionRepositoryImpl implements TransactionRepository {
  const TransactionRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
    required this.networkInfo,
  });

  final TransactionRemoteDataSource remoteDataSource;
  final TransactionLocalDataSource localDataSource;
  final NetworkInfo networkInfo;

  @override
  Future<Either<Failure, List<Transaction>>> getTransactions() async {
    if (await networkInfo.isConnected) {
      try {
        final models = await remoteDataSource.getTransactions();
        await localDataSource.cacheTransactions(models);
        return Right(models);
      } on DioException catch (e) {
        return Left(_mapDioException(e));
      }
    } else {
      try {
        final cached = await localDataSource.getCachedTransactions();
        return Right(cached);
      } on CacheException {
        return const Left(CacheFailure('No cached data available'));
      }
    }
  }

  @override
  Future<Either<Failure, Transaction>> getTransactionById(String id) async {
    try {
      final model = await remoteDataSource.getTransactionById(id);
      return Right(model);
    } on DioException catch (e) {
      return Left(_mapDioException(e));
    }
  }

  @override
  Future<Either<Failure, Transaction>> createTransaction(CreateTransactionParams params) async {
    try {
      final model = await remoteDataSource.createTransaction(params.toJson());
      return Right(model);
    } on DioException catch (e) {
      return Left(_mapDioException(e));
    }
  }

  Failure _mapDioException(DioException e) {
    return switch (e.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.receiveTimeout ||
      DioExceptionType.sendTimeout =>
        const NetworkFailure('Connection timed out'),
      DioExceptionType.connectionError =>
        const NetworkFailure('No internet connection'),
      DioExceptionType.badResponse => _mapStatusCode(e.response?.statusCode),
      _ => ServerFailure(e.message ?? 'An unexpected error occurred'),
    };
  }

  Failure _mapStatusCode(int? statusCode) {
    return switch (statusCode) {
      400 => const ServerFailure('Bad request'),
      401 => const AuthFailure('Session expired. Please log in again'),
      403 => const AuthFailure('You do not have permission'),
      404 => const ServerFailure('Resource not found'),
      422 => const ServerFailure('Validation failed'),
      429 => const ServerFailure('Too many requests. Please try again later'),
      >= 500 => const ServerFailure('Server error. Please try again later'),
      _ => const ServerFailure('An unexpected error occurred'),
    };
  }
}
```

## 4. Complete Flow: UseCase → DataSource

```dart
// lib/features/transaction/domain/usecases/get_transactions.dart
import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../entities/transaction.dart';
import '../repositories/transaction_repository.dart';

class GetTransactions {
  const GetTransactions({required this.repository});
  final TransactionRepository repository;

  Future<Either<Failure, List<Transaction>>> call() {
    return repository.getTransactions();
  }
}
```

## 5. Error Handling

### Failure Types

```dart
// lib/core/error/failures.dart
sealed class Failure {
  const Failure(this.message);
  final String message;
}

final class ServerFailure extends Failure {
  const ServerFailure(super.message);
}

final class NetworkFailure extends Failure {
  const NetworkFailure(super.message);
}

final class CacheFailure extends Failure {
  const CacheFailure(super.message);
}

final class AuthFailure extends Failure {
  const AuthFailure(super.message);
}
```

### Network Connectivity Check

```dart
// lib/core/network/network_info.dart
import 'package:connectivity_plus/connectivity_plus.dart';

abstract class NetworkInfo {
  Future<bool> get isConnected;
}

class NetworkInfoImpl implements NetworkInfo {
  const NetworkInfoImpl({required this.connectivity});
  final Connectivity connectivity;

  @override
  Future<bool> get isConnected async {
    final result = await connectivity.checkConnectivity();
    return !result.contains(ConnectivityResult.none);
  }
}
```

## 6. Response Models

```dart
// lib/features/transaction/data/models/transaction_model.dart
import '../../domain/entities/transaction.dart';

class TransactionModel extends Transaction {
  const TransactionModel({
    required super.id,
    required super.amount,
    required super.description,
    required super.date,
    required super.status,
  });

  factory TransactionModel.fromJson(Map<String, dynamic> json) {
    return TransactionModel(
      id: json['id'] as String,
      amount: (json['amount'] as num).toDouble(),
      description: json['description'] as String? ?? '',
      date: DateTime.parse(json['date'] as String),
      status: TransactionStatus.values.byName(json['status'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'amount': amount,
      'description': description,
      'date': date.toIso8601String(),
      'status': status.name,
    };
  }
}
```

### API Response Wrapper

```dart
// lib/core/network/api_response.dart
class ApiResponse<T> {
  const ApiResponse({required this.data, this.message, this.meta});
  final T data;
  final String? message;
  final PaginationMeta? meta;

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(dynamic) fromJsonT,
  ) {
    return ApiResponse(
      data: fromJsonT(json['data']),
      message: json['message'] as String?,
      meta: json['meta'] != null
          ? PaginationMeta.fromJson(json['meta'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PaginationMeta {
  const PaginationMeta({required this.page, required this.totalPages, required this.totalItems});
  final int page;
  final int totalPages;
  final int totalItems;

  factory PaginationMeta.fromJson(Map<String, dynamic> json) {
    return PaginationMeta(
      page: json['page'] as int,
      totalPages: json['total_pages'] as int,
      totalItems: json['total_items'] as int,
    );
  }

  bool get hasNextPage => page < totalPages;
}
```

## 7. Interceptors

### Auth Interceptor

```dart
// lib/core/network/interceptors/auth_interceptor.dart
import 'package:dio/dio.dart';
import '../../storage/secure_storage.dart';

class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.secureStorage, required this.dio});

  final SecureStorage secureStorage;
  final Dio dio;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await secureStorage.read('access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      final refreshToken = await secureStorage.read('refresh_token');
      if (refreshToken == null) {
        handler.next(err);
        return;
      }

      try {
        final response = await dio.post(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
        );
        final newAccessToken = response.data['access_token'] as String;
        final newRefreshToken = response.data['refresh_token'] as String;
        await secureStorage.write('access_token', newAccessToken);
        await secureStorage.write('refresh_token', newRefreshToken);

        // Retry the original request with new token
        err.requestOptions.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await dio.fetch(err.requestOptions);
        handler.resolve(retryResponse);
      } on DioException {
        // Refresh failed — clear tokens, force re-login
        await secureStorage.deleteAll();
        handler.next(err);
      }
    } else {
      handler.next(err);
    }
  }
}
```

### Logging Interceptor

```dart
// lib/core/network/interceptors/logging_interceptor.dart
import 'dart:developer' as dev;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class AppLoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (kDebugMode) {
      dev.log('→ ${options.method} ${options.uri}');
      // NEVER log: Authorization header, request bodies with passwords/tokens
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (kDebugMode) {
      dev.log('← ${response.statusCode} ${response.requestOptions.uri}');
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (kDebugMode) {
      dev.log('✗ ${err.response?.statusCode} ${err.requestOptions.uri} — ${err.message}');
    }
    handler.next(err);
  }
}
```

## 8. Testing

```dart
import 'package:dio/dio.dart';
import 'package:http_mock_adapter/http_mock_adapter.dart';

test('should_return_transactions_when_api_succeeds', () async {
  final dio = Dio(BaseOptions(baseUrl: 'https://api.test.com'));
  final adapter = DioAdapter(dio: dio);

  adapter.onGet(
    '/transactions',
    (server) => server.reply(200, {
      'data': [
        {'id': '1', 'amount': 100.0, 'description': 'Test', 'date': '2024-01-01T00:00:00Z', 'status': 'completed'},
      ],
    }),
  );

  final client = DioClient(baseUrl: 'https://api.test.com', interceptors: []);
  final datasource = TransactionRemoteDataSourceImpl(client: client);
  final result = await datasource.getTransactions();

  expect(result, isNotEmpty);
  expect(result.first.id, '1');
});
```

## 9. Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| Dio instance in presentation layer | UI layer makes network calls, bypasses domain and data layers | Dio lives in `core/network/`, only accessed by DataSource classes |
| No error handling on API calls | Unhandled `DioException` crashes the app | Wrap every DataSource call in try/catch, map to domain `Failure` |
| Parsing JSON in UI code | `jsonDecode` in a widget mixes data concerns with UI | Parse in `Model.fromJson()` inside data layer |
| Storing token in SharedPreferences | Plaintext, readable on rooted devices | Use `flutter_secure_storage` (Keychain/EncryptedSharedPrefs) |
| Logging request/response bodies in production | Leaks PII, tokens, and passwords to device logs | Guard with `kDebugMode`, never log auth headers or sensitive fields |
| Hardcoded API URLs | Can't switch environments | Use `ApiEndpoints` constants, inject base URL via DI |

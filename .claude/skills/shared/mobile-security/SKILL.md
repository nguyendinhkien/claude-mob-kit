---
name: mobile-security
description: Security checklist and patterns for mobile apps.
  Use when handling sensitive data, authentication, storage, or network calls.
user-invocable: true
---

# Mobile Security

## 1. Never Do List

These are non-negotiable. Violating any of these is a ship-blocker.

| # | Rule | What Goes Wrong |
|---|------|----------------|
| 1 | **No secrets, API keys, or tokens in source code or version control** | Bots scrape GitHub for keys within minutes. Keys in compiled code are trivially extractable with `strings` or decompilers. Use environment variables or a secrets manager. |
| 2 | **No sensitive data in SharedPreferences / UserDefaults unencrypted** | SharedPreferences is a plaintext XML file on Android. UserDefaults is a plaintext plist on iOS. Both are readable on rooted/jailbroken devices and in backups. |
| 3 | **No HTTP in production — HTTPS only** | HTTP traffic is readable by anyone on the same network. ATS (iOS) and cleartext traffic rules (Android) block HTTP by default — never disable these protections. |
| 4 | **No logging of sensitive data** | Logs persist on device and are accessible via `adb logcat` (Android) or Console.app (iOS). Auth tokens, passwords, credit card numbers, and PII must never appear in logs. |
| 5 | **No trusting user input without validation** | All user input — form fields, deep link parameters, intent extras, clipboard data — must be validated in the domain layer before processing. |

## 2. Secure Storage by Platform

### Flutter
```dart
// Use flutter_secure_storage — backed by Keychain (iOS) and EncryptedSharedPreferences (Android)
final storage = FlutterSecureStorage();
await storage.write(key: 'auth_token', value: token);
final token = await storage.read(key: 'auth_token');
await storage.delete(key: 'auth_token'); // on logout
```

### Android (Native)
```kotlin
// EncryptedSharedPreferences backed by Android Keystore
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()
val securePrefs = EncryptedSharedPreferences.create(
    context, "secure_prefs", masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
```

### iOS (Native)
```swift
// Keychain Services — data persists across app reinstalls unless explicitly deleted
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "auth_token",
    kSecValueData as String: tokenData,
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
]
SecItemAdd(query as CFDictionary, nil)
```

**What goes where:**

| Data | Storage | Why |
|------|---------|-----|
| Auth tokens, refresh tokens | Secure storage (Keychain / EncryptedSharedPrefs) | Must survive app restarts, must be encrypted at rest |
| User preferences (theme, locale) | SharedPreferences / UserDefaults | Not sensitive, no encryption needed |
| Cached API responses | SQLite / Hive with app-level encryption | Potentially contains PII depending on the API |
| Passwords | Never stored locally | Always use token-based auth; re-authenticate via biometric |

## 3. Network Security

### Certificate Pinning
Pin the leaf certificate or public key, not the root CA. Update pins before certificate rotation.

```dart
// Flutter: using dio with certificate pinning
final dio = Dio();
(dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
  final client = HttpClient();
  client.badCertificateCallback = (cert, host, port) {
    return cert.pem == expectedPem; // compare against pinned cert
  };
  return client;
};
```

### Logging Rules

| Log Level | Allowed Content | Forbidden Content |
|-----------|----------------|-------------------|
| Debug | Request URLs, response status codes, timing | Request/response bodies with PII |
| Info | User actions (screen viewed, button tapped) | User IDs, emails, names |
| Error | Error type, stack trace, correlation ID | Auth tokens, passwords, API keys |

**Rule:** If you wouldn't put it on a billboard, don't put it in a log.

### Timeout Configuration
```
Connection timeout: 15 seconds
Read timeout: 30 seconds
Write timeout: 30 seconds
```
Never use infinite timeouts — they cause hanging connections that leak memory and sockets.

## 4. Authentication Patterns

### Token Storage and Refresh
```
1. Login → receive access_token (short-lived, 15min) + refresh_token (long-lived, 30 days)
2. Store both in secure storage (never SharedPreferences)
3. Attach access_token to every API request via interceptor
4. On 401 → use refresh_token to get new access_token
5. On refresh failure → clear tokens, redirect to login
6. On logout → clear both tokens, invalidate refresh_token server-side
```

**Critical:** Refresh token rotation — each refresh request returns a new refresh token and invalidates the old one. If a stolen refresh token is used, the real user's next refresh fails, signaling compromise.

### Biometric Authentication
```
1. Biometric does NOT replace password login — it gates access to the stored token
2. Flow: User logs in with password → token stored in secure storage → biometric enrolled
3. On next launch: biometric prompt → if success, read token from secure storage → API call
4. If biometric fails 3 times → fall back to password entry
5. If device biometric settings change → re-authenticate with password
```

### Session Management
- Set maximum session duration (e.g., 30 days for consumer, 8 hours for enterprise)
- Implement idle timeout (5 minutes for fintech, 30 minutes for general apps)
- On background → start idle timer. On foreground → check if expired
- Provide "sign out all devices" option that invalidates all refresh tokens server-side

## 5. Input Validation

Input validation lives in the **domain layer** — it's a business rule, not a UI concern. The presentation layer provides inline feedback, but domain enforces.

| Field | Validation Rule | Where |
|-------|----------------|-------|
| Email | RFC 5322 regex + max 254 chars | `core/utils/validators.dart` |
| Password | Min 8 chars, at least 1 upper + 1 lower + 1 digit | `core/utils/validators.dart` |
| Phone | E.164 format, country code required | `core/utils/validators.dart` |
| Currency amount | Positive, max 2 decimal places, max value check | Feature domain entity |
| Free text | Max length, strip HTML tags, no script injection | `core/utils/validators.dart` |
| Deep link params | Whitelist allowed paths, validate IDs are UUIDs | Feature domain use case |

## 6. Release Build Checklist

- [ ] **Obfuscation enabled** — `--obfuscate --split-debug-info` (Flutter), ProGuard/R8 (Android), bitcode (iOS)
- [ ] **Debug logs removed** — use `kReleaseMode` guard or `dart:developer` log that strips in release
- [ ] **Root/jailbreak detection** — if handling financial or health data, detect and warn (not block — blocking causes false positives on custom ROMs)
- [ ] **Permissions audit** — remove unused permissions from AndroidManifest.xml and Info.plist. Request at point of use, not on launch
- [ ] **Network security config** — no `cleartextTrafficPermitted="true"` in release. No `NSAllowsArbitraryLoads` in Info.plist
- [ ] **Source maps / debug symbols** — stored securely for crash reporting, never bundled in the release artifact
- [ ] **Third-party SDK audit** — review data collection by analytics, crash reporting, and ad SDKs. Remove test/debug SDKs

## 7. Dependency Security

Before adding any package, check:

1. **Maintenance status** — last published date, open issues count, response time to security issues
2. **Permissions** — does the package request network, storage, camera, or location? Why?
3. **Transitive dependencies** — run `flutter pub deps` or `./gradlew dependencies` to see the full tree. Every transitive dependency is an attack surface
4. **Known vulnerabilities** — check pub.dev advisories, GitHub security advisories, or `npm audit` equivalent
5. **License compatibility** — GPL packages cannot be used in proprietary apps. Prefer MIT, BSD, Apache 2.0

**Rule:** Every dependency is code you didn't write and can't fully audit. The bar for adding one should be: "Is writing this myself significantly harder and more error-prone than trusting this dependency?"

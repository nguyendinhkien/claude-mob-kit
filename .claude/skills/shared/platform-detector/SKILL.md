---
name: platform-detector
description: Detect mobile platform from project file signatures.
  Preloaded into all agents. Must be the first step of every agent session.
user-invocable: false
disable-model-invocation: true
---

# Platform Detector

Run this detection before doing anything else. The detected platform determines which skills, commands, build tools, and state management patterns are available.

## 1. Detection Rules

Execute in order. Stop at the first match.

**Step 1 — Check for Flutter:**
```bash
# Search current directory and up to 5 parent directories
find . -maxdepth 1 -name "pubspec.yaml" 2>/dev/null
# If not found, check parent directories
find .. -maxdepth 1 -name "pubspec.yaml" 2>/dev/null
find ../.. -maxdepth 1 -name "pubspec.yaml" 2>/dev/null
```
If `pubspec.yaml` is found anywhere in the current directory or ancestor directories → **PLATFORM = flutter**

**Step 2 — Check for Android:**
```bash
# Look for Gradle build files at the project root (not inside a flutter android/ subfolder)
find . -maxdepth 1 -name "build.gradle.kts" -o -name "build.gradle" 2>/dev/null
```
If `build.gradle.kts` or `build.gradle` exists at the project root AND no `pubspec.yaml` exists in any ancestor directory → **PLATFORM = android**

**Step 3 — Check for iOS:**
```bash
find . -maxdepth 1 -name "Package.swift" 2>/dev/null
find . -maxdepth 1 -name "*.xcodeproj" -type d 2>/dev/null
find . -maxdepth 1 -name "*.xcworkspace" -type d 2>/dev/null
```
If `Package.swift`, `*.xcodeproj`, or `*.xcworkspace` exists → **PLATFORM = ios**

**Step 4 — No match:**
If none of the above matched → proceed to Ambiguous Cases (section 3).

## 2. Monorepo Handling

Flutter projects always contain `android/` and `ios/` subfolders. This creates false positives if detection is naive.

| Situation | Correct Detection | Why |
|-----------|------------------|-----|
| Root has `pubspec.yaml` + `android/` + `ios/` | **Flutter** | This is a standard Flutter project |
| Working inside `android/` subfolder, `pubspec.yaml` exists in parent | **Flutter** | The `android/` folder is Flutter's native host, not a standalone Android project |
| Working inside `ios/` subfolder, `pubspec.yaml` exists in parent | **Flutter** | Same — the `ios/` folder is Flutter's native host |
| Root has `build.gradle.kts`, no `pubspec.yaml` anywhere above | **Android** | True standalone Android project |
| Root has `*.xcodeproj`, no `pubspec.yaml` anywhere above | **iOS** | True standalone iOS project |
| Monorepo with `apps/mobile-flutter/` and `apps/backend/` | **Flutter** | Detect from the directory containing `pubspec.yaml` |

**The key rule:** If `pubspec.yaml` exists anywhere in the current directory or any ancestor directory, it is always Flutter — regardless of what other files exist alongside it.

## 3. Ambiguous Cases

If no platform files are found, or if multiple platform signatures conflict at the same directory level:

**Resolution order:**
1. Check which files the user explicitly mentioned in their request
2. Check which files were most recently modified (`ls -lt` the candidate files)
3. If still unclear, ask the user **once** with clear options:

```
I detected multiple platforms in this project. Which are you working on?
1. Flutter
2. Android (native)
3. iOS (native)
```

- Store the user's answer for the rest of the session — never ask again
- If the user doesn't answer or says "all," default to **Flutter** (cross-platform covers the most ground)

## 4. Result Format

After detection, store and log the result:

```
PLATFORM = flutter | android | ios
```

Log the detection reason so it can be reviewed:
```
Detected Flutter — found pubspec.yaml at /Users/dev/myapp/pubspec.yaml
Detected Android — found build.gradle.kts at /Users/dev/myapp/build.gradle.kts, no pubspec.yaml in ancestor dirs
Detected iOS — found MyApp.xcodeproj at /Users/dev/myapp/MyApp.xcodeproj
```

If the platform is queried later in the session, report both the platform and the detection reason.

## 5. Platform Capability Map

Once the platform is detected, the following skills, commands, and tools become available:

### Flutter
```
State management skills:
  - riverpod    → .claude/skills/flutter/riverpod/SKILL.md
  - bloc        → .claude/skills/flutter/bloc/SKILL.md
  - cubit       → .claude/skills/flutter/cubit/SKILL.md
  - provider    → .claude/skills/flutter/provider/SKILL.md
  - getx        → .claude/skills/flutter/getx/SKILL.md

Platform skills:
  - flutter-widget         → .claude/skills/flutter/flutter-widget/SKILL.md
  - flutter-navigation     → .claude/skills/flutter/flutter-navigation/SKILL.md
  - flutter-networking      → .claude/skills/flutter/flutter-networking/SKILL.md
  - flutter-local-storage  → .claude/skills/flutter/flutter-local-storage/SKILL.md
  - flutter-animation      → .claude/skills/flutter/flutter-animation/SKILL.md

Build:     flutter build apk --debug
Test:      flutter test --coverage
Run:       flutter run -d <device_id>
Packages:  flutter pub add <package_name>
Analyze:   flutter analyze
Format:    dart format .
```

### Android
```
State management skills:
  - viewmodel-stateflow    → ViewModel + StateFlow (Jetpack standard)
  - hilt                   → Dependency injection
  - compose-state          → Compose remember/mutableStateOf
  - livedata               → Legacy LiveData (migration path only)

Platform skills:
  - android-compose        → Jetpack Compose UI
  - android-navigation     → Navigation Component / Compose Navigation
  - android-retrofit       → Retrofit + OkHttp networking
  - android-room           → Room database
  - android-gradle         → Gradle build configuration

Build:     ./gradlew assembleDebug
Test:      ./gradlew test
Run:       ./gradlew installDebug
Packages:  libs.versions.toml + build.gradle.kts (version catalog)
Analyze:   ./gradlew lint
Format:    ./gradlew ktlintFormat
```

### iOS
```
State management skills:
  - swiftui-state          → @State, @StateObject, @ObservedObject, @EnvironmentObject
  - combine                → Publishers, Subscribers, Operators
  - async-actor            → Swift concurrency with actors

Platform skills:
  - ios-swiftui            → SwiftUI views and modifiers
  - ios-navigation         → NavigationStack / NavigationSplitView
  - ios-networking         → URLSession / async-await networking
  - ios-coredata           → Core Data / SwiftData persistence
  - ios-spm                → Swift Package Manager

Build:     xcodebuild build -scheme AppName -sdk iphonesimulator
Test:      xcodebuild test -scheme AppName -destination 'platform=iOS Simulator,name=iPhone 15'
Run:       Open in Xcode → Cmd+R
Packages:  Swift Package Manager (Xcode UI or Package.swift)
Analyze:   swiftlint
Format:    swiftformat .
```

### Shared Skills (loaded for ALL platforms)
```
  - mobile-architecture    → .claude/skills/shared/mobile-architecture/SKILL.md
  - mobile-testing         → .claude/skills/shared/mobile-testing/SKILL.md
  - mobile-security        → .claude/skills/shared/mobile-security/SKILL.md
  - mobile-performance     → .claude/skills/shared/mobile-performance/SKILL.md
  - platform-detector      → .claude/skills/shared/platform-detector/SKILL.md (this file)
```

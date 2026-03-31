---
name: mobile-performance
description: Performance patterns and checklist for mobile apps.
  Use when implementing lists, images, animations, or any data-heavy features.
user-invocable: true
---

# Mobile Performance

## 1. Golden Rules

1. **Measure first, optimize second.** Never optimize based on intuition. Profile, identify the actual bottleneck, fix that specific thing.
2. **Profile in profile/release mode, not debug.** Debug mode disables optimizations, enables asserts, and uses JIT — performance numbers in debug are meaningless. Flutter: `flutter run --profile`. Android: release build with profiling enabled. iOS: Instruments on a release build.
3. **Test on the lowest-spec device you support.** If it runs well on a 2019 budget phone, it runs well everywhere.

## 2. List Performance

### Always Use Lazy Loading
```dart
// WRONG — builds ALL items upfront, even off-screen ones
ListView(
  children: items.map((item) => ItemWidget(item)).toList(),
)

// RIGHT — builds only visible items + a small buffer
ListView.builder(
  itemCount: items.length,
  itemBuilder: (context, index) => ItemWidget(items[index]),
)
```

### Pagination
- Load **20 items** per page (adjustable, but start here)
- Trigger next page load when user scrolls within **3 items** of the end
- Show a loading indicator at the bottom while fetching
- Stop requesting when the server returns fewer items than the page size

```dart
// Scroll listener for pagination
if (index >= items.length - 3 && !isLoadingMore && hasMoreItems) {
  loadNextPage();
}
```

### Const Widgets
Mark widgets `const` whenever all constructor parameters are compile-time constants. This tells Flutter to reuse the same instance and skip rebuilding.

```dart
// WRONG — new instance created every build cycle
return Padding(padding: EdgeInsets.all(16), child: Text('Hello'));

// RIGHT — reused across rebuilds
return const Padding(padding: EdgeInsets.all(16), child: Text('Hello'));
```

### Avoid Rebuilding Unchanged Items
- Use `key` on list items tied to a stable ID (not index)
- For state management: select only the fields each item needs, not the entire list state
- Use `AutomaticKeepAliveClientMixin` sparingly — only for items with expensive state (e.g., video players)

## 3. Image Performance

| Rule | Why | Implementation |
|------|-----|----------------|
| **Always specify width and height** | Without dimensions, the layout engine must wait for the image to load before sizing, causing layout shifts | `Image.network(url, width: 200, height: 200, fit: BoxFit.cover)` |
| **Use cached_network_image** (Flutter) | Caches to disk, shows placeholder, handles loading/error states | `CachedNetworkImage(imageUrl: url, placeholder: shimmer)` |
| **Compress before upload** | Users upload 12MP photos; your server doesn't need 12MP | Resize to max 1920px on longest edge, compress to 80% quality JPEG |
| **Use appropriate format** | WebP is 25-35% smaller than JPEG at same quality | Serve WebP to Android, HEIC to iOS when possible. JPEG as universal fallback |
| **Resize on the server** | Don't send a 2000px image for a 100px thumbnail | Use CDN image transforms: `?w=200&h=200&fit=cover` |

## 4. State Management Performance

### Select Minimal State Slices
```dart
// WRONG — rebuilds when ANY part of AppState changes
final state = ref.watch(appStateProvider);
return Text(state.user.name);

// RIGHT — rebuilds only when user.name changes
final name = ref.watch(appStateProvider.select((s) => s.user.name));
return Text(name);
```

### Avoid Rebuilding the Entire Tree
- Split large widgets into smaller widgets with their own `build()` methods
- Each small widget watches only the state it needs
- Parent widgets should pass data down, not watch state that only children need

### Provider/Bloc Scoping
- Scope providers to the route or feature that needs them, not at the app root
- Dispose providers when the route is popped
- Never put high-frequency state (scroll position, text input) in global state

## 5. Async Operations

### Never Block the Main Thread
```dart
// WRONG — parsing 10MB JSON on the main thread
final data = jsonDecode(largeJsonString);

// RIGHT — offload to isolate
final data = await compute(jsonDecode, largeJsonString);
```

Heavy operations that must run on a background thread/isolate:
- JSON parsing of large payloads (>100KB)
- Image processing (resize, compress, filter)
- Database queries returning >1000 rows
- Cryptographic operations
- File I/O for large files

### Show Loading State Immediately
```dart
// Set loading state BEFORE the async call, not after
emit(Loading());
final result = await repository.fetchData();
emit(result.fold((f) => Error(f), (d) => Loaded(d)));
```

### Cancel on Dispose
```dart
class _MyPageState extends State<MyPage> {
  CancelableOperation<void>? _fetchOperation;

  void _loadData() {
    _fetchOperation?.cancel();
    _fetchOperation = CancelableOperation.fromFuture(repository.fetchData());
  }

  @override
  void dispose() {
    _fetchOperation?.cancel();
    super.dispose();
  }
}
```

## 6. Memory Leak Checklist

Every `dispose()` method must clean up everything the widget created. Missing any of these leaks memory.

| Resource | Cleanup Method | What Leaks If Missed |
|----------|---------------|---------------------|
| `AnimationController` | `controller.dispose()` | Ticker keeps firing, holds reference to State |
| `TextEditingController` | `controller.dispose()` | Listener list holds references to disposed widgets |
| `ScrollController` | `controller.dispose()` | Scroll position listener keeps firing |
| `FocusNode` | `focusNode.dispose()` | Focus tree retains reference to detached node |
| `StreamSubscription` | `subscription.cancel()` | Stream keeps emitting to a dead listener, holds widget in memory |
| `StreamController` | `controller.close()` | Open stream holds all listeners in memory |
| `Timer` / `Timer.periodic` | `timer.cancel()` | Callback fires after widget is disposed, causes setState-after-dispose |
| Platform channels | Remove method call handler | Native side holds reference to Dart callback |

**Self-check:** If your `initState()` creates it, your `dispose()` must destroy it. Every `addListener` needs a `removeListener`. Every `listen()` needs a `cancel()`.

## 7. Build Performance

### Split Large Widgets
If a `build()` method is longer than 80 lines, it's doing too much. Extract sub-widgets as separate classes (not methods — methods don't get independent rebuild boundaries).

```dart
// WRONG — helper method rebuilds with parent every time
Widget _buildHeader() => Text(title);

// RIGHT — separate widget only rebuilds when its inputs change
class HeaderWidget extends StatelessWidget {
  final String title;
  const HeaderWidget({required this.title});
  @override
  Widget build(BuildContext context) => Text(title);
}
```

### Const Constructors
Every widget that takes only final primitive fields should have a `const` constructor. This allows Flutter to skip diffing entirely.

### RepaintBoundary
Wrap expensive painting operations (custom painters, complex animations) in `RepaintBoundary` to isolate their repaint from the rest of the tree.

```dart
// The animation repaints 60 times/sec — don't repaint the rest of the screen
RepaintBoundary(
  child: CustomPaint(painter: MyComplexPainter()),
)
```

Use sparingly — each `RepaintBoundary` allocates an offscreen buffer. Only use when the profiler shows unnecessary repaints propagating.

## 8. Profiling Guide

### When to Profile
- After implementing a new list or grid with >50 items
- After adding animations or transitions
- After integrating image loading or media playback
- Before every release — run the profiling checklist

### How to Profile

| Platform | Tool | What It Shows |
|----------|------|---------------|
| **Flutter** | DevTools Performance tab | Frame build/render times, jank frames (>16ms), widget rebuild counts |
| **Flutter** | DevTools Memory tab | Object allocation, retained size, GC pressure, leak detection |
| **Android** | Android Studio Profiler | CPU flame chart, memory heap dump, network request timeline |
| **Android** | Systrace / Perfetto | System-level thread scheduling, binder transactions, frame drops |
| **iOS** | Xcode Instruments (Time Profiler) | CPU hot paths, thread utilization, method-level timing |
| **iOS** | Xcode Instruments (Allocations) | Object lifecycle, retain cycles, transient allocation spikes |
| **iOS** | Xcode Instruments (Core Animation) | Offscreen renders, blending, dropped frames |

### What to Look For
1. **Jank frames** — any frame taking >16ms (60fps) or >8ms (120fps). Find the heaviest `build()` method in the flame chart
2. **Memory growth** — memory that grows without bound over time. Navigate back and forth between screens 10 times; memory should return to baseline
3. **Unnecessary rebuilds** — use `debugPrintRebuildDirtyWidgets = true` (Flutter) to see which widgets rebuild on each frame. If a widget rebuilds but its output hasn't changed, add `const` or use selectors
4. **Large images in memory** — look for decoded image bitmaps larger than their display size. A 4000x3000 image displayed at 200x150 wastes 45MB of GPU memory

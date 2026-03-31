---
name: flutter-animation
description: Animation patterns and performance rules for Flutter apps.
  Auto-loads when working with Dart files.
paths: "lib/**/*.dart, test/**/*.dart"
allowed-tools: Read, Write, Edit, Bash(flutter *)
---

# Flutter Animation

## 1. Animation Types

| Type | What | When | Performance |
|------|------|------|-------------|
| **Implicit** | `AnimatedContainer`, `AnimatedOpacity`, `TweenAnimationBuilder` | Simple property changes (size, color, opacity) | Best — framework handles everything |
| **Explicit** | `AnimationController` + `Tween` + `AnimatedBuilder` | Complex choreography, repeating, chained animations | Good — full control, more code |
| **Hero** | `Hero` widget with matching tags | Cross-route element transitions | Good — built into navigation |
| **Lottie** | `lottie` package | Complex illustrations, loading animations, onboarding | Varies — depends on composition complexity |

## 2. Decision: Implicit First

```
Can the animation be described as "property A changes to value B"?
├── YES → Use implicit animation (AnimatedContainer, AnimatedOpacity, etc.)
└── NO
    ├── Does it repeat, chain, or need precise timing control?
    │   ├── YES → Use explicit animation (AnimationController)
    │   └── NO → Use TweenAnimationBuilder
    └── Is it a pre-designed illustration or complex vector animation?
        └── YES → Use Lottie
```

Always start with implicit. Upgrade to explicit only when implicit can't do what you need.

## 3. Implicit Animation Examples

### AnimatedContainer — Size, Color, Shape Changes

```dart
class ExpandableCard extends StatefulWidget {
  const ExpandableCard({super.key});

  @override
  State<ExpandableCard> createState() => _ExpandableCardState();
}

class _ExpandableCardState extends State<ExpandableCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => setState(() => _isExpanded = !_isExpanded),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        width: double.infinity,
        height: _isExpanded ? 200 : 80,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: _isExpanded
              ? Theme.of(context).colorScheme.primaryContainer
              : Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(_isExpanded ? 16 : 8),
        ),
        child: Text(_isExpanded ? 'Expanded content here' : 'Tap to expand'),
      ),
    );
  }
}
```

### AnimatedSwitcher — Widget Transitions

```dart
class ContentSwitcher extends StatelessWidget {
  const ContentSwitcher({super.key, required this.showFirst});
  final bool showFirst;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 200),
      transitionBuilder: (child, animation) {
        return FadeTransition(opacity: animation, child: child);
      },
      child: showFirst
          ? const Text('First', key: ValueKey('first'))
          : const Text('Second', key: ValueKey('second')),
      // Key is REQUIRED — without it, AnimatedSwitcher can't detect the change
    );
  }
}
```

### TweenAnimationBuilder — Custom Implicit

```dart
// Animate a custom value without explicit AnimationController
class AnimatedCounter extends StatelessWidget {
  const AnimatedCounter({super.key, required this.value});
  final double value;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(end: value),
      duration: const Duration(milliseconds: 500),
      curve: Curves.easeOut,
      builder: (context, animatedValue, child) {
        return Text(
          '\$${animatedValue.toStringAsFixed(2)}',
          style: Theme.of(context).textTheme.headlineMedium,
        );
      },
    );
  }
}
```

## 4. Explicit Animation Setup

### AnimationController in StatefulWidget

```dart
class PulsingDot extends StatefulWidget {
  const PulsingDot({super.key, required this.color});
  final Color color;

  @override
  State<PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    _opacityAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn),
    );
  }

  @override
  void dispose() {
    _controller.dispose(); // CRITICAL — always dispose
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Opacity(
          opacity: _opacityAnimation.value,
          child: Transform.scale(
            scale: _scaleAnimation.value,
            child: child,
          ),
        );
      },
      // child is passed through — not rebuilt on each frame
      child: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: widget.color,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}
```

### CurvedAnimation

```dart
// Common curves and when to use them:
// Curves.easeInOut  — most UI transitions (default choice)
// Curves.easeOut    — elements entering the screen (fast start, slow end)
// Curves.easeIn     — elements leaving the screen (slow start, fast end)
// Curves.bounceOut  — playful confirmations (use sparingly)
// Curves.elasticOut — spring effect for attention-grabbing (use sparingly)

final animation = CurvedAnimation(
  parent: controller,
  curve: Curves.easeInOut,       // Forward curve
  reverseCurve: Curves.easeIn,   // Optional reverse curve
);
```

### Multiple Animations with Same Controller

```dart
// Use Interval to stagger animations on a single controller
final slideAnimation = Tween<Offset>(
  begin: const Offset(0, 0.3),
  end: Offset.zero,
).animate(CurvedAnimation(
  parent: _controller,
  curve: const Interval(0.0, 0.6, curve: Curves.easeOut), // First 60% of duration
));

final fadeAnimation = Tween<double>(begin: 0, end: 1).animate(
  CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.0, 0.4, curve: Curves.easeIn), // First 40%
  ),
);

final scaleAnimation = Tween<double>(begin: 0.8, end: 1).animate(
  CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.4, 1.0, curve: Curves.easeOut), // Last 60%
  ),
);
```

## 5. Performance Rules

### Animate Only Transform and Opacity

Transform and opacity are GPU-composited — they don't trigger relayout or repaint of children. Animating other properties (size, color, padding) forces the widget subtree to relayout every frame.

```dart
// FAST — GPU composited, no relayout
Transform.scale(scale: animation.value, child: child)
Opacity(opacity: animation.value, child: child)
FadeTransition(opacity: animation, child: child)
SlideTransition(position: animation, child: child)

// SLOWER — triggers relayout per frame (OK for simple cases, avoid in lists)
AnimatedContainer(width: animation.value * 200, ...)
AnimatedPadding(padding: EdgeInsets.all(animation.value * 16), ...)
```

### AnimationController.dispose() — Always

Every `AnimationController` must be disposed. No exceptions. If you create it in `initState()`, you dispose it in `dispose()`. A leaked controller keeps its `Ticker` alive, which holds a reference to the `State`, which holds the entire widget subtree.

### RepaintBoundary

```dart
// Isolate animation repaints from the rest of the tree
RepaintBoundary(
  child: AnimatedBuilder(
    animation: _controller,
    builder: (context, child) {
      return Transform.rotate(angle: _controller.value * 2 * pi, child: child);
    },
    child: const Icon(Icons.refresh, size: 32),
  ),
)
```

### Respect Reduced Motion

```dart
@override
Widget build(BuildContext context) {
  final reduceMotion = MediaQuery.of(context).disableAnimations;

  return AnimatedContainer(
    duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 300),
    // When reduced motion is on, change happens instantly
    height: _isExpanded ? 200 : 80,
  );
}
```

## 6. Timing Guidelines

| Animation Type | Duration | Examples |
|---------------|----------|---------|
| Micro-interactions | 100–200ms | Button press feedback, checkbox toggle, ripple, opacity fade |
| Standard transitions | 200–400ms | Page slide, bottom sheet, modal appear, tab switch |
| Complex animations | 400–600ms | Shared element, hero transition, onboarding sequence |
| **Hard limit** | **Never > 600ms** | Anything over 600ms feels sluggish and blocks user flow |

```dart
// Define timing constants — use throughout the app
abstract final class AnimationDurations {
  static const micro = Duration(milliseconds: 150);
  static const standard = Duration(milliseconds: 300);
  static const complex = Duration(milliseconds: 500);
}
```

## 7. Lottie Integration

```bash
flutter pub add lottie
```

```dart
// Place .json animation files in assets/animations/
// pubspec.yaml:
//   assets:
//     - assets/animations/

class LoadingAnimation extends StatelessWidget {
  const LoadingAnimation({super.key});

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    // Show static frame if reduced motion is on
    if (reduceMotion) {
      return Lottie.asset(
        'assets/animations/loading.json',
        animate: false,
        width: 120,
        height: 120,
      );
    }

    return Lottie.asset(
      'assets/animations/loading.json',
      width: 120,
      height: 120,
      repeat: true,
      frameRate: FrameRate.max,
    );
  }
}

// With controller for precise control
class OnboardingAnimation extends StatefulWidget {
  const OnboardingAnimation({super.key});

  @override
  State<OnboardingAnimation> createState() => _OnboardingAnimationState();
}

class _OnboardingAnimationState extends State<OnboardingAnimation>
    with TickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Lottie.asset(
      'assets/animations/onboarding.json',
      controller: _controller,
      onLoaded: (composition) {
        _controller
          ..duration = composition.duration
          ..forward();
      },
    );
  }
}
```

## 8. Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| AnimationController without `dispose()` | Memory leak — Ticker keeps alive, holds State reference, holds widget subtree | Always dispose in `dispose()`. Use `with SingleTickerProviderStateMixin` |
| Animating too many properties simultaneously | Layout thrashing — CPU recalculates layout 60 times/sec for each property | Stick to transform + opacity. Animate one layout property at a time max |
| Ignoring `disableAnimations` | Users with vestibular disorders experience nausea; violates accessibility | Check `MediaQuery.of(context).disableAnimations`, skip or shorten animations |
| Animations blocking interaction | User can't tap during a 2-second animation | Keep animations under 600ms. Use `IgnorePointer` only for the animated element, not the whole screen |
| Using `setState` to drive animations | `setState` triggers full rebuild of the widget; `AnimatedBuilder` only rebuilds its subtree | Use `AnimatedBuilder` or `*Transition` widgets |
| Creating AnimationController in `build()` | New controller every frame — instant memory leak | Always create in `initState()`, never in `build()` |

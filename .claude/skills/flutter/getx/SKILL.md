---
name: getx
description: GetX state management pattern for Flutter.
  Use when rapid prototyping or team is already familiar with GetX.
  Preloaded into agents when project uses getx.
user-invocable: false
disable-model-invocation: true
---

# GetX State Management

## 1. When to Use

- Rapid prototyping where shipping speed outweighs architectural purity
- Team already knows GetX and has established patterns with it
- Small to medium apps that need routing + state + DI in a single package
- MVPs and proof-of-concept apps with a planned future rewrite

## 2. When NOT to Use

- Large teams (>4 devs) — GetX's flexibility becomes inconsistency at scale
- Projects requiring strict testability — GetX's global state makes isolated testing difficult
- Apps that need long-term maintainability — GetX encourages patterns that don't scale
- When Clean Architecture is mandated — GetX's shortcuts bypass layer separation

## 3. Dependencies

Add via CLI to always get the latest version:
```bash
flutter pub add get
```

Single package covers state management, routing, dependency injection, and utilities.

## 4. Folder Structure

```
lib/features/[feature]/presentation/
├── controllers/
│   └── [feature]_controller.dart    # GetxController class
├── pages/
│   └── [feature]_page.dart
├── widgets/
│   └── [feature]_card.dart
└── bindings/
    └── [feature]_binding.dart       # Dependency binding
```

## 5. Core Patterns

### GetxController with Lifecycle

```dart
// lib/features/task/presentation/controllers/task_controller.dart
import 'package:get/get.dart';
import '../../../domain/entities/task.dart';
import '../../../domain/usecases/get_tasks.dart';
import '../../../domain/usecases/create_task.dart';

class TaskController extends GetxController {
  TaskController({
    required GetTasks getTasks,
    required CreateTask createTask,
  })  : _getTasks = getTasks,
        _createTask = createTask;

  final GetTasks _getTasks;
  final CreateTask _createTask;

  final tasks = <Task>[].obs;
  final isLoading = false.obs;
  final error = Rxn<String>();

  @override
  void onInit() {
    super.onInit();
    fetchTasks();
  }

  @override
  void onClose() {
    // Clean up resources: cancel subscriptions, close streams
    super.onClose();
  }

  Future<void> fetchTasks() async {
    isLoading.value = true;
    error.value = null;

    final result = await _getTasks();
    result.fold(
      (failure) => error.value = failure.message,
      (data) => tasks.assignAll(data),
    );

    isLoading.value = false;
  }

  Future<void> addTask(CreateTaskParams params) async {
    isLoading.value = true;
    final result = await _createTask(params);
    result.fold(
      (failure) {
        error.value = failure.message;
        Get.snackbar('Error', failure.message);
      },
      (task) {
        tasks.add(task);
        Get.snackbar('Success', 'Task created');
      },
    );
    isLoading.value = false;
  }

  void clearError() => error.value = null;
}
```

### Rx Variables — Observable State

```dart
// Primitive types — use .obs extension
final count = 0.obs;                    // RxInt
final name = ''.obs;                    // RxString
final isActive = false.obs;             // RxBool
final price = 0.0.obs;                  // RxDouble

// Collections
final items = <String>[].obs;           // RxList
final settings = <String, dynamic>{}.obs; // RxMap

// Nullable
final selectedId = Rxn<String>();       // RxnString (nullable)
final user = Rxn<User>();               // Rx<User?> (nullable object)

// Updating values
count.value = 5;                        // Primitives: use .value
items.add('new item');                  // Collections: mutate directly
items.assignAll(newList);               // Replace entire collection
```

### Obx() — Reactive Widget

Automatically rebuilds when any `.obs` variable inside changes.

```dart
class TaskPage extends StatelessWidget {
  const TaskPage({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<TaskController>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tasks'),
        actions: [
          Obx(() => Badge(
            label: Text('${controller.tasks.length}'),
            child: const Icon(Icons.list),
          )),
        ],
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }
        if (controller.error.value != null) {
          return ErrorState(
            message: controller.error.value!,
            onRetry: controller.fetchTasks,
          );
        }
        if (controller.tasks.isEmpty) {
          return const EmptyState(message: 'No tasks yet');
        }
        return ListView.builder(
          itemCount: controller.tasks.length,
          itemBuilder: (_, index) => TaskCard(controller.tasks[index]),
        );
      }),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Get.toNamed('/tasks/create'),
        child: const Icon(Icons.add),
      ),
    );
  }
}
```

### GetBuilder — Non-Reactive (Manual Update)

Use when you don't need automatic reactivity. Rebuilds only on explicit `update()`.

```dart
class SettingsPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GetBuilder<SettingsController>(
      builder: (controller) {
        return SwitchListTile(
          title: const Text('Dark Mode'),
          value: controller.isDarkMode,
          onChanged: controller.toggleDarkMode,
        );
      },
    );
  }
}

// In controller: call update() to trigger GetBuilder rebuild
void toggleDarkMode(bool value) {
  isDarkMode = value;
  update(); // Manual rebuild trigger
}
```

### Dependency Injection — Get.put / Get.lazyPut / Get.find

| Method | When Created | When to Use |
|--------|-------------|-------------|
| `Get.put(Controller())` | Immediately | Controller needed right now, on the current screen |
| `Get.lazyPut(() => Controller())` | On first `Get.find()` | Controller may not be needed; create on demand |
| `Get.find<Controller>()` | N/A (retrieves) | Access an already-registered controller |

```dart
// Register eagerly
Get.put(TaskController(getTasks: getIt(), createTask: getIt()));

// Register lazily — created only when first accessed
Get.lazyPut(() => TaskController(getTasks: getIt(), createTask: getIt()));

// Retrieve anywhere
final controller = Get.find<TaskController>();
```

### GetView\<T\> Shortcut

Provides `controller` getter automatically. Saves writing `Get.find<T>()`.

```dart
class TaskPage extends GetView<TaskController> {
  const TaskPage({super.key});

  @override
  Widget build(BuildContext context) {
    // controller is automatically Get.find<TaskController>()
    return Obx(() => Text('${controller.tasks.length} tasks'));
  }
}
```

### Routing

```dart
// Navigate
Get.to(() => const DetailPage());              // Push
Get.off(() => const HomePage());               // Push and remove current
Get.offAll(() => const LoginPage());           // Push and remove all
Get.back();                                     // Pop

// Named routes (preferred)
Get.toNamed('/tasks/detail', arguments: task);
Get.offNamed('/home');
Get.offAllNamed('/login');

// Retrieve arguments
final task = Get.arguments as Task;

// Define routes in GetMaterialApp
GetMaterialApp(
  initialRoute: '/home',
  getPages: [
    GetPage(name: '/home', page: () => const HomePage(), binding: HomeBinding()),
    GetPage(name: '/tasks', page: () => const TaskPage(), binding: TaskBinding()),
    GetPage(name: '/tasks/detail', page: () => const TaskDetailPage()),
  ],
)
```

## 6. Dependency Management — Bindings

Bindings register controllers when a route is opened and dispose them when left.

```dart
class TaskBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => TaskController(
      getTasks: Get.find<GetTasks>(),
      createTask: Get.find<CreateTask>(),
    ));
  }
}

// Use in route definition
GetPage(
  name: '/tasks',
  page: () => const TaskPage(),
  binding: TaskBinding(),
)
```

## 7. Testing

```dart
void main() {
  late TaskController controller;
  late MockGetTasks mockGetTasks;
  late MockCreateTask mockCreateTask;

  setUp(() {
    mockGetTasks = MockGetTasks();
    mockCreateTask = MockCreateTask();
    // Register controller for GetX's dependency system
    controller = Get.put(TaskController(
      getTasks: mockGetTasks,
      createTask: mockCreateTask,
    ));
  });

  tearDown(() {
    // Critical: reset GetX's internal state between tests
    Get.reset();
  });

  test('should_load_tasks_on_init', () async {
    when(() => mockGetTasks()).thenAnswer((_) async => Right(testTasks));

    // onInit is called by Get.put, so tasks should already be loading
    await Future.delayed(Duration.zero); // Let async complete

    expect(controller.tasks, testTasks);
    expect(controller.isLoading.value, false);
  });

  test('should_set_error_when_fetch_fails', () async {
    when(() => mockGetTasks()).thenAnswer(
      (_) async => Left(ServerFailure('Network error')),
    );

    await controller.fetchTasks();

    expect(controller.error.value, 'Network error');
    expect(controller.tasks, isEmpty);
  });
}
```

**Testing limitation:** GetX uses global singletons. `Get.reset()` is required between every test to avoid state leakage. This is the primary reason GetX is not recommended for large projects.

## 8. Anti-patterns

| Anti-pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| Using `Get.context` or `Get.overlayContext` | Accesses the global context, which can be stale or wrong after navigation | Pass `BuildContext` from the widget, or use `Get.snackbar` / `Get.dialog` which manage context internally |
| Not calling `super.onClose()` or forgetting cleanup | Memory leaks from workers, streams, and timers that keep running | Always override `onClose()` and cancel/dispose everything created in `onInit()` |
| Business logic in Obx() | UI layer computes state — violates separation | Move logic to controller methods; Obx should only read values |
| Using `Get.put` everywhere without `Get.delete` | Controllers accumulate in memory even after screens are popped | Use Bindings with routes for automatic lifecycle management |
| Mixing `Obx` and `GetBuilder` in the same controller | Confusing — some state is reactive (.obs), some requires manual `update()` | Pick one approach per controller. Prefer `.obs` + `Obx` for consistency |

## 9. When to Migrate Away from GetX

Consider migration when:

1. **Team grows beyond 4 developers** — GetX's lack of enforced structure means each dev writes different patterns. Code reviews become arguments about style.
2. **Test coverage becomes a requirement** — GetX's global singletons make isolated testing painful. Every test needs `Get.reset()`, and concurrent test execution is unreliable.
3. **App complexity exceeds CRUD** — Real-time features, complex form flows, multi-step processes need explicit state machines that GetX's reactive variables can't model cleanly.
4. **Performance profiling reveals rebuild issues** — `Obx` rebuilds on any `.obs` change inside it. Without selector-level granularity, large Obx blocks cause unnecessary rebuilds.
5. **Dependency audit flags GetX** — GetX is a single massive package. If any part has a security issue or breaking change, the entire state/routing/DI stack is affected.

**Migration target:** Riverpod for state + GoRouter for routing + GetIt for DI. Migrate one feature at a time. Both systems coexist during transition.

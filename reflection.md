# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial design centred on four classes that map directly to real-world entities:

- **Task** (dataclass) — holds everything about a single care activity: title, start time, duration, priority (`high / medium / low`), recurrence frequency (`once / daily / weekly`), a due date, and a `completed` flag.
- **Pet** (dataclass) — stores a pet's name, species, and an owned list of `Task` objects. Exposes `add_task`, `remove_task`, and `get_tasks`.
- **Owner** — manages a collection of `Pet` objects and provides a convenience method (`get_all_tasks`) that flattens every pet's tasks into a single `(pet, task)` list. This is the data source the `Scheduler` reads from.
- **Scheduler** — the algorithmic brain. It receives an `Owner` and implements sorting (by time, by priority), filtering (by pet, by completion status), conflict detection, and the `build_schedule` method that produces today's prioritised plan.

Three core user actions the system supports:
1. **Add a pet** — create a `Pet` and register it with the `Owner`.
2. **Schedule a task** — create a `Task` with a time and priority and attach it to the chosen pet.
3. **View today's plan** — call `Scheduler.build_schedule()` to get a sorted, filtered list of due tasks, and inspect `detect_conflicts()` for overlap warnings.

**b. Design changes**

Yes, one significant change: I initially planned for `Scheduler` to own the conflict-detection logic using only exact start-time matching (two tasks conflict if they start at the same minute). During implementation I realised this would miss the common case where one task *starts inside* another task's window.

I added an `end_time()` method to `Task` so the scheduler could compare a task's start time against the previous task's end time. The change required no restructuring — it was additive — but it made the conflict detection meaningfully more accurate.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:
- **Priority** (`high → medium → low`) — tasks that matter more appear first in the plan.
- **Time** (HH:MM) — within the same priority level, tasks are ordered chronologically.
- **Due date** — `build_schedule` only includes tasks whose `due_date ≤ today`, so future tasks and already-advanced recurring tasks are excluded.
- **Frequency** — `once` tasks can be permanently completed; `daily` and `weekly` tasks advance their due date on completion and remain active.

Priority was treated as the primary constraint because a late-but-critical task (a medication, for example) should never be buried behind a low-priority grooming session.

**b. Tradeoffs**

The scheduler flags overlapping tasks as warnings but does not block them. If two tasks overlap, the schedule still renders — the user sees a warning banner at the top.

This is a reasonable tradeoff because a warning-only approach:
1. Avoids blocking valid scenarios (e.g., two pets can be walked simultaneously by different people).
2. Keeps the UI informational rather than restrictive, which is appropriate for a planning assistant rather than a booking system.
3. Is far simpler to implement correctly than a full constraint-satisfaction solver.

The known limitation is that the system only checks for time-window overlaps, not resource conflicts (e.g., a single owner can't physically do two things at once). A future version could add an "owner capacity" constraint.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used in three distinct phases:
- **Design brainstorming** — generating the initial Mermaid UML diagram and checking whether the class responsibilities were well-separated.
- **Algorithmic scaffolding** — asking for idiomatic Python patterns (e.g., `sorted()` with a tuple key, `dataclasses.field(default_factory=...)`) to avoid reinventing standard library features.
- **Test generation** — drafting an initial test suite and then refining edge-case coverage (recurring task state after completion, overlapping vs. adjacent time windows).

The most useful prompt pattern was giving the AI a concrete failing scenario ("if a daily task is marked done, it should not appear as completed but should be due tomorrow — how should `mark_complete` handle this?") rather than asking it to design the whole method from scratch.

**b. Judgment and verification**

The AI initially suggested storing task times as `datetime` objects (with full date + time) rather than plain `"HH:MM"` strings. The suggestion was technically correct and would have made arithmetic easier, but it introduced timezone handling, serialisation complexity, and friction when reading times from a Streamlit text input.

I evaluated the tradeoff and kept `str` for the time field. `end_time()` does the arithmetic manually (converts to total minutes, then back), which is a few extra lines but keeps the rest of the codebase simple. I verified by writing the `test_end_time_crosses_hour` test — if the arithmetic were wrong, that test would catch it.

---

## 4. Testing and Verification

**a. What you tested**

The test suite (`tests/test_pawpal.py`) covers:

| Behaviour | Why it matters |
|---|---|
| `mark_complete` on a `once` task sets `completed = True` | Core state change — everything downstream depends on this |
| `mark_complete` on a `daily` task advances `due_date` by 1, keeps `completed = False` | Recurrence is the trickiest logic in the system |
| `mark_complete` on a `weekly` task advances `due_date` by 7 | Same reason |
| `end_time()` arithmetic, including hour-crossing | Conflict detection relies on this being correct |
| `is_due_today` returns `True` for overdue tasks | Ensures old tasks don't silently disappear |
| Adding a task to a pet increases count | Validates `add_task` / list integrity |
| `sort_by_time` returns tasks in chronological order | Core scheduling guarantee |
| `sort_by_priority` returns high → medium → low | Core scheduling guarantee |
| `filter_by_pet` returns only the right pet's tasks | Filtering correctness |
| `detect_conflicts` catches overlapping windows | Conflict detection correctness |
| Non-overlapping tasks produce no conflicts | True-negative test — equally important |
| `build_schedule` excludes future-dated tasks | Ensures tomorrow's tasks don't pollute today's view |

**b. Confidence**

High confidence for all tested behaviours. The suite has both positive and negative cases for the most critical paths.

Edge cases to test next:
- Tasks that span midnight (e.g., `23:30` + 60 minutes — `end_time()` would return `24:30`, which is not a valid time string; needs a clamp or day rollover).
- Two pets with tasks at identical times (currently detected as a conflict; might want a "same-owner, same-time" vs. "different-pet" distinction).
- An owner with zero pets calling `build_schedule` (currently returns an empty list — correct, but worth a dedicated test).

---

## 5. Reflection

**a. What went well**

The clean separation between `pawpal_system.py` (logic) and `app.py` (UI). Because the Scheduler returns plain Python lists of `(Pet, Task)` tuples, the Streamlit layer never needs to know how sorting or filtering works — it just iterates and renders. This made debugging much easier: I could verify all behaviour in `main.py` before touching the UI at all.

**b. What you would improve**

The time field is the main rough edge. Using `"HH:MM"` strings was a pragmatic simplification, but it means the system can't handle tasks that cross midnight, can't easily compute "how many hours of care are scheduled today," and requires manual parsing in `end_time()`. A proper `datetime.time` field with duration as `timedelta` would be more robust.

I'd also add the ability to edit or delete tasks from the Streamlit UI — currently you can only add them, which is limiting for real use.

**c. Key takeaway**

Design the data model before thinking about the UI. Once `Task`, `Pet`, `Owner`, and `Scheduler` had clear, stable interfaces, the Streamlit layer almost wrote itself — every button just calls a method and calls `st.rerun()`. The investment in getting the class boundaries right up front paid off in how straightforward the integration phase was.

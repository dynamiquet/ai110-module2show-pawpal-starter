"""
PawPal+ CLI demo — verifies backend logic in the terminal.

Run: python main.py
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler


# ── Helpers ──────────────────────────────────────────────────────────────────

def print_tasks(pairs, label: str) -> None:
    """Pretty-print a list of (Pet, Task) pairs under a header."""
    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")
    if not pairs:
        print("  (no tasks)")
        return
    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for pet, task in pairs:
        status = "✅" if task.completed else "⭕"
        freq_tag = f" [{task.frequency}]" if task.frequency != "once" else ""
        print(
            f"  {status} {task.time}–{task.end_time()}  {task.title:<22}"
            f" | {pet.name:<8} | {priority_icon[task.priority]} {task.priority:<6}"
            f"{freq_tag}"
        )
        if task.description:
            print(f"       ↳ {task.description}")


# ── Setup ─────────────────────────────────────────────────────────────────────

def main() -> None:
    owner = Owner("Jordan")

    mochi = Pet("Mochi", "cat")
    buddy = Pet("Buddy", "dog")
    owner.add_pet(mochi)
    owner.add_pet(buddy)

    # Mochi's tasks
    mochi.add_task(Task("Breakfast",       "08:00", 10, "high",   "daily",  "Wet food + fresh water"))
    mochi.add_task(Task("Flea treatment",  "09:00",  5, "high",   "weekly", "Spot-on treatment"))
    mochi.add_task(Task("Playtime",        "18:00", 20, "medium", "daily",  "Feather wand session"))

    # Buddy's tasks — evening walk intentionally overlaps with Mochi playtime
    buddy.add_task(Task("Morning walk",    "07:30", 30, "high",   "daily",  "Off-leash at the park"))
    buddy.add_task(Task("Lunch",           "12:00", 10, "high",   "daily",  "Kibble + water"))
    buddy.add_task(Task("Evening walk",    "18:10", 45, "medium", "daily",  "Neighbourhood loop"))  # overlaps Mochi 18:00

    scheduler = Scheduler(owner)

    # ── Full schedule ─────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"  PawPal+ — Today's Schedule  ({date.today()})")
    print("=" * 50)
    print(f"  Owner: {owner.name}  |  Pets: {', '.join(p.name for p in owner.pets)}")

    print_tasks(scheduler.build_schedule(), "Today's plan (priority → time)")

    # ── Sorted by time ────────────────────────────────────────────────────────
    print_tasks(scheduler.sort_by_time(), "All tasks sorted by time")

    # ── Per-pet filter ────────────────────────────────────────────────────────
    print_tasks(scheduler.filter_by_pet("Mochi"), "Mochi's tasks only")

    # ── Conflict detection ────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("  Conflict check")
    print(f"{'─' * 50}")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for c in conflicts:
            print(f"  ⚠️  {c}")
    else:
        print("  No conflicts detected.")

    # ── Mark a task complete ──────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("  Marking 'Morning walk' complete (daily → due tomorrow)")
    print(f"{'─' * 50}")
    ok = scheduler.mark_task_complete("Buddy", "Morning walk")
    print(f"  mark_task_complete returned: {ok}")
    print_tasks(scheduler.filter_by_pet("Buddy"), "Buddy's tasks after marking done")

    # ── Pending tasks ─────────────────────────────────────────────────────────
    print_tasks(scheduler.filter_by_status(completed=False), "All pending tasks")

    print()


if __name__ == "__main__":
    main()

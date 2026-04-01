"""
Automated tests for PawPal+ core logic.

Run: python -m pytest
"""

import json
import os
import tempfile
import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def make_task(**overrides) -> Task:
    """Return a Task with sensible defaults; override any field via kwargs."""
    defaults = dict(
        title="Test task",
        time="09:00",
        duration_minutes=15,
        priority="medium",
        frequency="once",
        description="",
    )
    defaults.update(overrides)
    return Task(**defaults)


def make_owner_with_pets() -> tuple:
    """Return (owner, cat_pet, dog_pet) pre-wired together."""
    owner = Owner("Jordan")
    cat = Pet("Mochi", "cat")
    dog = Pet("Buddy", "dog")
    owner.add_pet(cat)
    owner.add_pet(dog)
    return owner, cat, dog


# ── Task tests ────────────────────────────────────────────────────────────────

class TestTaskCompletion:
    def test_once_task_marks_completed(self):
        task = make_task(frequency="once")
        task.mark_complete()
        assert task.completed is True

    def test_daily_task_advances_due_date(self):
        today = date.today()
        task = make_task(frequency="daily", due_date=today)
        task.mark_complete()
        assert task.due_date == today + timedelta(days=1)

    def test_daily_task_stays_active_after_completion(self):
        task = make_task(frequency="daily")
        task.mark_complete()
        assert task.completed is False  # daily tasks recur; not permanently done

    def test_weekly_task_advances_due_date(self):
        today = date.today()
        task = make_task(frequency="weekly", due_date=today)
        task.mark_complete()
        assert task.due_date == today + timedelta(weeks=1)

    def test_weekly_task_stays_active(self):
        task = make_task(frequency="weekly")
        task.mark_complete()
        assert task.completed is False


class TestTaskEndTime:
    def test_end_time_basic(self):
        task = make_task(time="08:30", duration_minutes=45)
        assert task.end_time() == "09:15"

    def test_end_time_crosses_hour(self):
        task = make_task(time="11:50", duration_minutes=30)
        assert task.end_time() == "12:20"

    def test_end_time_exact_hour(self):
        task = make_task(time="10:00", duration_minutes=60)
        assert task.end_time() == "11:00"


class TestTaskDueToday:
    def test_due_today(self):
        task = make_task(due_date=date.today())
        assert task.is_due_today() is True

    def test_overdue_is_still_due(self):
        task = make_task(due_date=date.today() - timedelta(days=2))
        assert task.is_due_today() is True

    def test_future_task_not_due(self):
        task = make_task(due_date=date.today() + timedelta(days=1))
        assert task.is_due_today() is False


# ── Pet tests ─────────────────────────────────────────────────────────────────

class TestPet:
    def test_add_task_increases_count(self):
        pet = Pet("Mochi", "cat")
        assert len(pet.tasks) == 0
        pet.add_task(make_task(title="Feed"))
        assert len(pet.tasks) == 1
        pet.add_task(make_task(title="Play"))
        assert len(pet.tasks) == 2

    def test_remove_existing_task(self):
        pet = Pet("Buddy", "dog")
        pet.add_task(make_task(title="Walk"))
        assert pet.remove_task("Walk") is True
        assert len(pet.tasks) == 0

    def test_remove_nonexistent_task_returns_false(self):
        pet = Pet("Buddy", "dog")
        assert pet.remove_task("Nonexistent") is False

    def test_get_tasks_returns_all(self):
        pet = Pet("X", "cat")
        pet.add_task(make_task(title="A"))
        pet.add_task(make_task(title="B"))
        assert len(pet.get_tasks()) == 2


# ── Owner tests ───────────────────────────────────────────────────────────────

class TestOwner:
    def test_add_pet(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "cat"))
        assert len(owner.pets) == 1

    def test_get_pet_found(self):
        owner = Owner("Jordan")
        pet = Pet("Mochi", "cat")
        owner.add_pet(pet)
        assert owner.get_pet("Mochi") is pet

    def test_get_pet_not_found(self):
        owner = Owner("Jordan")
        assert owner.get_pet("Ghost") is None

    def test_get_all_tasks_aggregates_across_pets(self):
        owner, cat, dog = make_owner_with_pets()
        cat.add_task(make_task(title="Feed"))
        cat.add_task(make_task(title="Play"))
        dog.add_task(make_task(title="Walk"))
        assert len(owner.get_all_tasks()) == 3

    def test_get_all_tasks_empty(self):
        owner = Owner("Jordan")
        assert owner.get_all_tasks() == []


# ── Scheduler tests ───────────────────────────────────────────────────────────

class TestSchedulerSorting:
    def test_sort_by_time_ascending(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Late",  time="14:00"))
        cat.add_task(make_task(title="Early", time="07:00"))
        cat.add_task(make_task(title="Mid",   time="10:30"))
        scheduler = Scheduler(owner)
        times = [t.time for _, t in scheduler.sort_by_time()]
        assert times == sorted(times)

    def test_sort_by_priority_order(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Low",    time="08:00", priority="low"))
        cat.add_task(make_task(title="High",   time="09:00", priority="high"))
        cat.add_task(make_task(title="Medium", time="07:00", priority="medium"))
        scheduler = Scheduler(owner)
        priorities = [t.priority for _, t in scheduler.sort_by_priority()]
        assert priorities == ["high", "medium", "low"]


class TestSchedulerFiltering:
    def test_filter_by_pet_returns_correct_tasks(self):
        owner, cat, dog = make_owner_with_pets()
        cat.add_task(make_task(title="Feed"))
        dog.add_task(make_task(title="Walk"))
        scheduler = Scheduler(owner)
        mochi_tasks = scheduler.filter_by_pet("Mochi")
        assert len(mochi_tasks) == 1
        assert mochi_tasks[0][1].title == "Feed"

    def test_filter_by_status_pending(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Done task", frequency="once"))
        cat.add_task(make_task(title="Pending task"))
        cat.tasks[0].mark_complete()
        scheduler = Scheduler(owner)
        pending = scheduler.filter_by_status(completed=False)
        assert all(not t.completed for _, t in pending)

    def test_filter_by_status_completed(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Done", frequency="once"))
        cat.tasks[0].mark_complete()
        scheduler = Scheduler(owner)
        done = scheduler.filter_by_status(completed=True)
        assert len(done) == 1


class TestSchedulerConflicts:
    def test_overlapping_tasks_detected(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Task A", time="09:00", duration_minutes=60))
        cat.add_task(make_task(title="Task B", time="09:30", duration_minutes=30))  # starts inside A
        scheduler = Scheduler(owner)
        assert len(scheduler.detect_conflicts()) >= 1

    def test_non_overlapping_tasks_no_conflict(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Task A", time="09:00", duration_minutes=30))
        cat.add_task(make_task(title="Task B", time="09:30", duration_minutes=30))  # starts exactly at A's end
        scheduler = Scheduler(owner)
        assert scheduler.detect_conflicts() == []

    def test_no_tasks_no_conflict(self):
        owner = Owner("Empty")
        scheduler = Scheduler(owner)
        assert scheduler.detect_conflicts() == []


class TestSchedulerMarkComplete:
    def test_mark_task_complete_success(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Walk", frequency="once"))
        scheduler = Scheduler(owner)
        assert scheduler.mark_task_complete("Mochi", "Walk") is True
        assert cat.tasks[0].completed is True

    def test_mark_task_complete_bad_pet(self):
        owner = Owner("Jordan")
        scheduler = Scheduler(owner)
        assert scheduler.mark_task_complete("Ghost", "Walk") is False

    def test_mark_task_complete_bad_task(self):
        owner, cat, _ = make_owner_with_pets()
        scheduler = Scheduler(owner)
        assert scheduler.mark_task_complete("Mochi", "Nonexistent") is False


class TestBuildSchedule:
    def test_only_due_tasks_included(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Today",    due_date=date.today()))
        cat.add_task(make_task(title="Tomorrow", due_date=date.today() + timedelta(days=1)))
        scheduler = Scheduler(owner)
        schedule = scheduler.build_schedule()
        titles = [t.title for _, t in schedule]
        assert "Today" in titles
        assert "Tomorrow" not in titles


# ── Persistence tests ─────────────────────────────────────────────────────────

class TestPersistence:
    def _make_owner(self) -> Owner:
        owner = Owner("Jordan")
        cat = Pet("Mochi", "cat")
        cat.add_task(make_task(title="Breakfast", time="08:00", frequency="daily"))
        cat.add_task(make_task(title="Meds", time="09:00", frequency="weekly",
                               due_date=date.today() + timedelta(days=3)))
        owner.add_pet(cat)
        return owner

    def test_round_trip_preserves_owner_name(self):
        owner = self._make_owner()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            owner.save_to_json(path)
            loaded = Owner.load_from_json(path)
            assert loaded.name == "Jordan"
        finally:
            os.unlink(path)

    def test_round_trip_preserves_pets_and_tasks(self):
        owner = self._make_owner()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            owner.save_to_json(path)
            loaded = Owner.load_from_json(path)
            assert len(loaded.pets) == 1
            assert loaded.pets[0].name == "Mochi"
            assert len(loaded.pets[0].tasks) == 2
        finally:
            os.unlink(path)

    def test_round_trip_preserves_due_date(self):
        owner = self._make_owner()
        future = date.today() + timedelta(days=3)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            owner.save_to_json(path)
            loaded = Owner.load_from_json(path)
            meds = loaded.pets[0].get_tasks()[1]
            assert meds.due_date == future
        finally:
            os.unlink(path)

    def test_to_dict_structure(self):
        owner = self._make_owner()
        d = owner.to_dict()
        assert "name" in d
        assert "pets" in d
        assert d["pets"][0]["tasks"][0]["due_date"] == date.today().isoformat()

    def test_data_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            assert Owner.data_file_exists(path) is True
        finally:
            os.unlink(path)

    def test_data_file_not_exists(self):
        assert Owner.data_file_exists("/tmp/does_not_exist_pawpal.json") is False


# ── Next available slot tests ─────────────────────────────────────────────────

class TestNextAvailableSlot:
    def test_empty_schedule_returns_earliest(self):
        owner = Owner("Test")
        scheduler = Scheduler(owner)
        assert scheduler.next_available_slot(30, earliest="07:00") == "07:00"

    def test_slot_after_single_task(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="Walk", time="07:00", duration_minutes=30))
        scheduler = Scheduler(owner)
        slot = scheduler.next_available_slot(30, earliest="07:00")
        assert slot == "07:30"

    def test_slot_fits_in_gap_between_tasks(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="A", time="07:00", duration_minutes=30))
        cat.add_task(make_task(title="B", time="08:30", duration_minutes=30))
        scheduler = Scheduler(owner)
        # Gap: 07:30–08:30 (60 min). A 45-min task should fit at 07:30.
        slot = scheduler.next_available_slot(45, earliest="07:00")
        assert slot == "07:30"

    def test_slot_skips_gap_too_small(self):
        owner, cat, _ = make_owner_with_pets()
        cat.add_task(make_task(title="A", time="07:00", duration_minutes=30))
        cat.add_task(make_task(title="B", time="07:45", duration_minutes=30))
        scheduler = Scheduler(owner)
        # Gap 07:30–07:45 = 15 min, too small for 30 min → placed after B at 08:15
        slot = scheduler.next_available_slot(30, earliest="07:00")
        assert slot == "08:15"

"""
PawPal+ — Core logic layer.

Classes: Task, Pet, Owner, Scheduler
"""

import json
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple


@dataclass
class Task:
    """Represents a single pet care activity."""

    title: str
    time: str  # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    frequency: str  # "once" | "daily" | "weekly"
    description: str = ""
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def mark_complete(self) -> None:
        """Mark task complete. Recurring tasks advance their due date instead of being closed."""
        if self.frequency == "daily":
            self.due_date += timedelta(days=1)
            # completed stays False — task recurs tomorrow
        elif self.frequency == "weekly":
            self.due_date += timedelta(weeks=1)
        else:
            self.completed = True

    def is_due_today(self) -> bool:
        """Return True if this task is due today or overdue."""
        return self.due_date <= date.today()

    def end_time(self) -> str:
        """Return the HH:MM end time based on start time + duration."""
        h, m = map(int, self.time.split(":"))
        total_minutes = h * 60 + m + self.duration_minutes
        return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


@dataclass
class Pet:
    """Represents a pet with its own list of care tasks."""

    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """Remove a task by title. Returns True if found and removed."""
        for i, t in enumerate(self.tasks):
            if t.title == title:
                self.tasks.pop(i)
                return True
        return False

    def get_tasks(self) -> List[Task]:
        """Return all tasks for this pet."""
        return self.tasks


class Owner:
    """Represents the pet owner who manages one or more pets."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's roster."""
        self.pets.append(pet)

    def get_pet(self, name: str) -> Optional[Pet]:
        """Look up a pet by name. Returns None if not found."""
        for pet in self.pets:
            if pet.name == name:
                return pet
        return None

    def get_all_tasks(self) -> List[Tuple[Pet, Task]]:
        """Return every (pet, task) pair across all pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    # --- Persistence ---

    def to_dict(self) -> dict:
        """Serialise the owner and all pets/tasks to a plain dictionary."""
        return {
            "name": self.name,
            "pets": [
                {
                    "name": pet.name,
                    "species": pet.species,
                    "tasks": [
                        {
                            "title": t.title,
                            "time": t.time,
                            "duration_minutes": t.duration_minutes,
                            "priority": t.priority,
                            "frequency": t.frequency,
                            "description": t.description,
                            "completed": t.completed,
                            "due_date": t.due_date.isoformat(),
                        }
                        for t in pet.tasks
                    ],
                }
                for pet in self.pets
            ],
        }

    def save_to_json(self, path: str = "data.json") -> None:
        """Persist the owner's full state to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> "Owner":
        """Reconstruct an Owner (with all pets and tasks) from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        owner = cls(data["name"])
        for pet_data in data["pets"]:
            pet = Pet(pet_data["name"], pet_data["species"])
            for td in pet_data["tasks"]:
                pet.add_task(
                    Task(
                        title=td["title"],
                        time=td["time"],
                        duration_minutes=td["duration_minutes"],
                        priority=td["priority"],
                        frequency=td["frequency"],
                        description=td.get("description", ""),
                        completed=td.get("completed", False),
                        due_date=date.fromisoformat(td["due_date"]),
                    )
                )
            owner.add_pet(pet)
        return owner

    @staticmethod
    def data_file_exists(path: str = "data.json") -> bool:
        """Return True if a saved data file exists at the given path."""
        return os.path.isfile(path)


class Scheduler:
    """Organizes, filters, and analyzes an owner's pet care tasks."""

    _PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # --- Sorting ---

    def sort_by_time(self) -> List[Tuple[Pet, Task]]:
        """Return all tasks sorted chronologically by start time."""
        return sorted(self.owner.get_all_tasks(), key=lambda x: x[1].time)

    def sort_by_priority(self) -> List[Tuple[Pet, Task]]:
        """Return tasks sorted by priority (high → medium → low), then by start time."""
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda x: (self._PRIORITY_ORDER[x[1].priority], x[1].time),
        )

    # --- Filtering ---

    def filter_by_pet(self, pet_name: str) -> List[Tuple[Pet, Task]]:
        """Return tasks belonging to a specific pet, sorted by priority then time."""
        return sorted(
            [(p, t) for p, t in self.owner.get_all_tasks() if p.name == pet_name],
            key=lambda x: (self._PRIORITY_ORDER[x[1].priority], x[1].time),
        )

    def filter_by_status(self, completed: bool) -> List[Tuple[Pet, Task]]:
        """Return tasks filtered by completion status."""
        return [(p, t) for p, t in self.owner.get_all_tasks() if t.completed == completed]

    # --- Scheduling ---

    def build_schedule(self) -> List[Tuple[Pet, Task]]:
        """Build today's schedule: only tasks due today, sorted by priority then time."""
        due = [(p, t) for p, t in self.owner.get_all_tasks() if t.is_due_today()]
        return sorted(due, key=lambda x: (self._PRIORITY_ORDER[x[1].priority], x[1].time))

    # --- Conflict detection ---

    def detect_conflicts(self) -> List[str]:
        """
        Detect scheduling conflicts where tasks have overlapping time windows.

        Returns a list of human-readable warning strings. Returns an empty list
        if no conflicts are found. Generates a warning rather than raising an
        exception so the schedule can still be displayed.
        """
        tasks = self.sort_by_time()
        conflicts: List[str] = []
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                pet_i, task_i = tasks[i]
                pet_j, task_j = tasks[j]
                # task_j starts before task_i ends → overlap
                if task_j.time < task_i.end_time():
                    conflicts.append(
                        f"Conflict: '{task_i.title}' ({pet_i.name}, "
                        f"{task_i.time}–{task_i.end_time()}) overlaps with "
                        f"'{task_j.title}' ({pet_j.name}, starts {task_j.time})"
                    )
        return conflicts

    # --- Advanced scheduling ---

    def next_available_slot(self, duration_minutes: int, earliest: str = "07:00") -> str:
        """
        Return the earliest HH:MM start time that fits a new task of the given
        duration without overlapping any existing task.

        Scans the day's occupied windows in chronological order and returns the
        first gap that is wide enough. If no gap exists before the last task
        ends, the slot is placed immediately after the last task.
        """
        occupied = sorted(
            [(t.time, t.end_time()) for _, t in self.sort_by_time()]
        )
        candidate = earliest
        for start, end in occupied:
            if candidate >= end:
                continue  # candidate already falls after this task
            # Compute where candidate would end
            h, m = map(int, candidate.split(":"))
            total = h * 60 + m + duration_minutes
            candidate_end = f"{total // 60:02d}:{total % 60:02d}"
            if candidate_end <= start:
                return candidate  # fits in the gap before this task starts
            # Doesn't fit — skip past this task
            candidate = end
        return candidate

    # --- Task management ---

    def mark_task_complete(self, pet_name: str, task_title: str) -> bool:
        """Mark a task complete by pet name and task title. Returns True on success."""
        pet = self.owner.get_pet(pet_name)
        if pet is None:
            return False
        for task in pet.tasks:
            if task.title == task_title:
                task.mark_complete()
                return True
        return False

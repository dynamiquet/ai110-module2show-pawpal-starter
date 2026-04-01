# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I went with four classes: `Task`, `Pet`, `Owner`, and `Scheduler`.

`Task` holds all the info about one care activity — title, time, duration, priority, frequency, and whether it's done. `Pet` stores the pet's name and species and keeps a list of its tasks. `Owner` just holds a list of pets and has a method to pull all tasks across all of them. `Scheduler` is the main logic class — it sorts, filters, detects conflicts, and builds the daily plan.

The three main things a user can do: add a pet, add a task to that pet, and generate today's schedule.

**b. Design changes**

Originally conflict detection just checked if two tasks had the same start time. That's too simple — if one task runs from 9:00 to 10:00 and another starts at 9:30, that's still a conflict. So I added `end_time()` to `Task` so the scheduler could actually compare windows. Wasn't a big change but made it more accurate.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler sorts by priority first (high → medium → low), then by time. It also only shows tasks due today or overdue — future tasks and recurring tasks that were already completed don't show up. Recurring tasks just advance their due date instead of being permanently marked done.

Priority comes first because you don't want a medication buried under a low-priority grooming task.

**b. Tradeoffs**

If two tasks overlap, the scheduler shows a warning but doesn't block the schedule. I did it this way because sometimes two pets can have tasks at the same time if there's more than one person helping out. Blocking it would be too strict. The tradeoff is the system can't tell when it's actually a real problem vs. when it's fine — it just flags everything and lets the user decide.

---

## 3. AI Collaboration

**a. How you used AI**

Mostly used it for three things: generating the UML diagram to start, helping with specific implementations like the sorting logic and recurring task handling, and generating tests. 

The most useful pattern was asking about one specific thing at a time — like "how should mark_complete work for a daily task" instead of "build the scheduler." The broad prompts gave too much stuff to review.

Keeping separate chat sessions per phase helped because the AI wasn't carrying baggage from earlier decisions when I was trying to just focus on tests.

**b. Judgment and verification**

AI suggested using `datetime` objects for the time field instead of `"HH:MM"` strings. It's technically more correct but would've made everything more complicated — JSON serialization, timezones, converting Streamlit input. I kept strings and just did the math manually in `end_time()`. Wrote a test for it to make sure the arithmetic didn't break on edge cases like hour-crossing.

It also suggested adding a validator to `Task` to reject bad priority strings. Skipped that — the UI already limits the options, so it felt like unnecessary code.

The main thing I learned is you have to stay in charge of what gets built. AI will give you something that works, but it doesn't know what tradeoffs matter for your specific project. That's on you.

---

## 4. Testing and Verification

**a. What you tested**

The main things: task completion (both one-time and recurring), end_time arithmetic, sorting order, filter by pet, conflict detection, and that build_schedule only shows today's tasks. Also added tests for the JSON persistence round-trip and the next-available-slot algorithm once those got added.

The recurring task tests were the most important since that logic is easy to get wrong — the task shouldn't be permanently "done," it should just move to the next day.

**b. Confidence**

Pretty confident in the core stuff — 42 tests all passing. The main thing I'd want to cover next is tasks that go past midnight (like 23:30 + 90 min), because `end_time()` would return something like `25:00` which isn't valid. That's a known gap but not a real use case for pet care so I left it.

---

## 5. Reflection

**a. What went well**

Keeping the logic in `pawpal_system.py` separate from the UI made things a lot easier. I could test everything in the terminal with `main.py` before touching Streamlit. When something broke in the UI it was usually clear pretty fast whether it was a logic issue or a display issue.

**b. What you would improve**

The `"HH:MM"` string for time is kind of a hack. It works but means you can't easily do things like "how many hours of care are scheduled today" without more parsing. Would switch to `datetime.time` if I rebuilt it.

Also there's no way to delete or edit tasks in the UI right now which would be pretty annoying to use for real.

**c. Key takeaway**

Design the data model first before thinking about the UI. The Streamlit part was fast because the classes were already solid — every button just called a method and reran. If I had jumped straight to the UI it would've been a mess.

---

## 6. Prompt Comparison (Challenge 5)

**Task:** `Scheduler.next_available_slot` — finds the first open gap in the schedule that fits a task of a given duration.

**GPT-4o** suggested using `datetime` intervals and returning a full `datetime` object. Correct logic but assumed the whole codebase used `datetime`, which it doesn't.

**Claude** suggested converting `"HH:MM"` to total minutes, scanning gaps, converting back. That matched what `end_time()` already does so it fit right in with no extra wrappers.

Claude's version was better here because it matched the existing code. GPT's would've been fine in a different project. The takeaway is that "correct" depends on context — a suggestion that works in isolation can still be the wrong pick if it clashes with how the rest of the code is written.

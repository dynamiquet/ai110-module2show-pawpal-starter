import streamlit as st
from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Your smart pet care planning assistant")

# ── Session state + persistence ───────────────────────────────────────────────
# On first load, try to restore a previously saved session from data.json.
# Streamlit reruns the whole script on every interaction, so the Owner lives
# in st.session_state to survive across reruns without being reset.
if "owner" not in st.session_state:
    if Owner.data_file_exists(DATA_FILE):
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = None
    else:
        st.session_state.owner = None


def save() -> None:
    """Persist current state to disk after every mutating action."""
    if st.session_state.owner is not None:
        st.session_state.owner.save_to_json(DATA_FILE)


# ── Owner & pet setup ─────────────────────────────────────────────────────────
with st.expander("👤 Owner & Pet Setup", expanded=st.session_state.owner is None):
    owner_name = st.text_input("Owner name", value="Jordan")
    pet_name   = st.text_input("Pet name",   value="Mochi")
    species    = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])

    col_setup, col_reset = st.columns([3, 1])
    with col_setup:
        if st.button("Set up owner & pet"):
            new_owner = Owner(owner_name)
            new_owner.add_pet(Pet(pet_name, species))
            st.session_state.owner = new_owner
            save()
            st.success(f"Welcome, {owner_name}! {pet_name} the {species} is ready.")
    with col_reset:
        if st.button("Reset", help="Clear all saved data and start fresh"):
            st.session_state.owner = None
            import os
            if os.path.isfile(DATA_FILE):
                os.remove(DATA_FILE)
            st.rerun()

if st.session_state.owner is None:
    st.info("Fill in the form above to get started.")
    st.stop()

owner: Owner = st.session_state.owner
scheduler    = Scheduler(owner)

# ── Add another pet ───────────────────────────────────────────────────────────
with st.expander("➕ Add another pet"):
    new_pet_name = st.text_input("New pet's name", key="new_pet_name")
    new_species  = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="new_species")
    if st.button("Add pet"):
        if new_pet_name.strip():
            if owner.get_pet(new_pet_name.strip()) is None:
                owner.add_pet(Pet(new_pet_name.strip(), new_species))
                save()
                st.success(f"Added {new_pet_name}!")
            else:
                st.warning(f"A pet named '{new_pet_name}' already exists.")
        else:
            st.error("Please enter a name for the new pet.")

st.divider()

# ── Add a task ────────────────────────────────────────────────────────────────
st.subheader("➕ Add a Task")

pet_names         = [p.name for p in owner.pets]
selected_pet_name = st.selectbox("For which pet?", pet_names)

col1, col2 = st.columns(2)
with col1:
    task_title = st.text_input("Task title",        value="Morning walk")
    duration   = st.number_input("Duration (min)",  min_value=1, max_value=480, value=20)
    task_desc  = st.text_input("Description (opt)", value="")
with col2:
    priority  = st.selectbox("Priority",  ["high", "medium", "low"])
    frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
    # Smart suggestion: show the next available slot for the chosen duration
    suggested = scheduler.next_available_slot(int(duration))
    task_time = st.text_input("Start time (HH:MM)", value=suggested,
                              help="Auto-suggested: first gap that fits this duration")

if st.button("Add task"):
    pet = owner.get_pet(selected_pet_name)
    if pet is not None:
        pet.add_task(Task(
            title            = task_title,
            time             = task_time,
            duration_minutes = int(duration),
            priority         = priority,
            frequency        = frequency,
            description      = task_desc,
            due_date         = date.today(),
        ))
        save()
        st.success(f"Added '{task_title}' to {selected_pet_name}'s schedule.")

st.divider()

# ── Today's schedule ──────────────────────────────────────────────────────────
st.subheader(f"📅 Today's Schedule — {date.today().strftime('%A, %B %d')}")

# Conflict warnings — shown prominently at the top
conflicts = scheduler.detect_conflicts()
if conflicts:
    for c in conflicts:
        st.warning(f"⚠️ {c}")
else:
    st.success("✅ No scheduling conflicts today.")

# Filters
col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_pet = st.selectbox("Filter by pet", ["All"] + pet_names, key="filter_pet")
with col_f2:
    filter_status = st.radio("Status", ["All", "Pending", "Completed"], horizontal=True)

# Build display list
if filter_pet != "All":
    display_tasks = scheduler.filter_by_pet(filter_pet)
else:
    display_tasks = scheduler.sort_by_priority()

if filter_status == "Pending":
    display_tasks = [(p, t) for p, t in display_tasks if not t.completed]
elif filter_status == "Completed":
    display_tasks = [(p, t) for p, t in display_tasks if t.completed]

# ── Render tasks ──────────────────────────────────────────────────────────────
_PRIORITY_ICON  = {"high": "🔴", "medium": "🟡", "low": "🟢"}
_SPECIES_ICON   = {"dog": "🐶", "cat": "🐱", "rabbit": "🐰", "bird": "🐦", "other": "🐾"}

if not display_tasks:
    st.info("No tasks to show. Add some above!")
else:
    for pet, task in display_tasks:
        status_icon  = "✅" if task.completed else "⭕"
        species_icon = _SPECIES_ICON.get(pet.species, "🐾")

        with st.container(border=True):
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"{status_icon} **{task.time}–{task.end_time()} &nbsp; {task.title}**"
                )
                st.caption(
                    f"{species_icon} {pet.name} &nbsp;·&nbsp; "
                    f"{_PRIORITY_ICON[task.priority]} {task.priority} priority &nbsp;·&nbsp; "
                    f"⏱ {task.duration_minutes} min"
                )
                if task.description:
                    st.caption(f"_{task.description}_")
                if task.frequency != "once":
                    st.caption(f"🔁 {task.frequency.capitalize()} · next: {task.due_date}")
            with col_btn:
                if not task.completed or task.frequency != "once":
                    label = "Done ✓" if not task.completed else "↻"
                    if st.button(label, key=f"done_{pet.name}_{task.title}"):
                        scheduler.mark_task_complete(pet.name, task.title)
                        save()
                        st.rerun()

st.divider()

# ── Stats strip ───────────────────────────────────────────────────────────────
all_tasks = owner.get_all_tasks()
done      = sum(1 for _, t in all_tasks if t.completed)
total     = len(all_tasks)
if total:
    pct = int(done / total * 100)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks today",  len(scheduler.build_schedule()))
    c2.metric("Completed",    f"{done}/{total}")
    c3.metric("Progress",     f"{pct}%")

st.caption("PawPal+ · data auto-saved to data.json · Built with Streamlit")

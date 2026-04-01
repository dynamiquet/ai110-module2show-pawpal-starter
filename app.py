import streamlit as st
from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Your smart pet care planning assistant")

# ── Session state initialisation ──────────────────────────────────────────────
# Streamlit reruns the script on every interaction. Storing the Owner object
# in st.session_state keeps it alive across reruns without resetting.
if "owner" not in st.session_state:
    st.session_state.owner = None

# ── Owner & pet setup ─────────────────────────────────────────────────────────
with st.expander("👤 Owner & Pet Setup", expanded=st.session_state.owner is None):
    owner_name = st.text_input("Owner name", value="Jordan")
    pet_name   = st.text_input("Pet name",   value="Mochi")
    species    = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])

    if st.button("Set up owner & pet"):
        new_owner = Owner(owner_name)
        new_owner.add_pet(Pet(pet_name, species))
        st.session_state.owner = new_owner
        st.success(f"Welcome, {owner_name}! {pet_name} the {species} is ready.")

if st.session_state.owner is None:
    st.info("Fill in the form above to get started.")
    st.stop()

owner: Owner    = st.session_state.owner
scheduler       = Scheduler(owner)

# ── Add another pet ───────────────────────────────────────────────────────────
with st.expander("➕ Add another pet"):
    new_pet_name = st.text_input("New pet's name", key="new_pet_name")
    new_species  = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="new_species")
    if st.button("Add pet"):
        if new_pet_name.strip():
            if owner.get_pet(new_pet_name.strip()) is None:
                owner.add_pet(Pet(new_pet_name.strip(), new_species))
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
    task_title = st.text_input("Task title",       value="Morning walk")
    task_time  = st.text_input("Start time (HH:MM)", value="08:00")
    task_desc  = st.text_input("Description (optional)", value="")
with col2:
    duration  = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20)
    priority  = st.selectbox("Priority",  ["high", "medium", "low"])
    frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])

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
        st.success(f"Added '{task_title}' to {selected_pet_name}'s schedule.")

st.divider()

# ── Today's schedule ──────────────────────────────────────────────────────────
st.subheader(f"📅 Today's Schedule — {date.today().strftime('%A, %B %d')}")

# Conflict banner
conflicts = scheduler.detect_conflicts()
if conflicts:
    with st.container():
        for c in conflicts:
            st.warning(f"⚠️ {c}")

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

# Render tasks
_PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}

if not display_tasks:
    st.info("No tasks to show. Add some above!")
else:
    for pet, task in display_tasks:
        status_icon = "✅" if task.completed else "⭕"
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"{status_icon} **{task.time} — {task.title}** &nbsp; "
                f"({pet.name} · {task.duration_minutes} min · "
                f"{_PRIORITY_ICON[task.priority]} {task.priority})"
            )
            if task.description:
                st.caption(task.description)
            if task.frequency != "once":
                st.caption(f"🔁 {task.frequency.capitalize()} | next due: {task.due_date}")
        with col_btn:
            # Show "Done" for incomplete tasks (and always for recurring ones)
            if not task.completed or task.frequency != "once":
                btn_label = "Done" if not task.completed else "↻"
                if st.button(btn_label, key=f"done_{pet.name}_{task.title}"):
                    scheduler.mark_task_complete(pet.name, task.title)
                    st.rerun()

st.divider()
st.caption("PawPal+ · Built with Streamlit")

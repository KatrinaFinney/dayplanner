import datetime
import os
import pickle
import json
import base64
from typing import Any, List, Dict, Tuple

import streamlit as st
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from plyer import notification


def get_base64_image(image_path: str) -> str:
    """
    Convert an image file to a base64 encoded string.
    
    Args:
        image_path: Path to the image file.
    
    Returns:
        Base64 encoded string of the image.
    """
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return encoded


def authenticate_google_calendar() -> Any:
    """
    Authenticate with Google Calendar using OAuth credentials.
    Returns the authenticated Calendar API service.
    """
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def add_to_calendar(service: Any, task: str, start_time: datetime.datetime, duration: int = 45) -> None:
    """
    Create an event in the Google Calendar.
    
    Args:
        service: Authenticated Google Calendar service.
        task: The task title.
        start_time: The start time for the event.
        duration: Duration of the event in minutes.
    """
    event = {
        'summary': task,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (start_time + datetime.timedelta(minutes=duration)).isoformat(), 'timeZone': 'UTC'},
    }
    service.events().insert(calendarId='primary', body=event).execute()


def send_notification(task: str, time: str) -> None:
    """
    Send a desktop notification for the upcoming task.
    
    Args:
        task: The task title.
        time: The scheduled time as a formatted string.
    """
    notification.notify(
        title="Upcoming Task Reminder",
        message=f"Task: {task} at {time}",
        timeout=10
    )


def save_schedule(schedule: List[Tuple[str, str]], filename: str = "schedule_history.json") -> None:
    """
    Save the daily schedule to a JSON file.
    
    Args:
        schedule: A list of tuples (time_str, task).
        filename: The JSON file name to store schedule history.
    """
    if os.path.exists(filename):
        with open(filename, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append({
        "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "tasks": schedule
    })

    with open(filename, "w") as f:
        json.dump(history, f, indent=4)


def load_schedule_history(filename: str = "schedule_history.json") -> List[Dict]:
    """
    Load the schedule history from a JSON file.
    
    Args:
        filename: The JSON file name where schedule history is stored.
    
    Returns:
        The schedule history as a list of dictionaries.
    """
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []


def brain_dump() -> None:
    """
    Display the Brain Dump section where users can add their tasks.
    Saves the tasks to st.session_state.
    """
    with st.expander("📝 Brain Dump - Add Your Tasks"):
        tasks_input = st.text_area("Enter your tasks (one per line):")
        if st.button("Submit Tasks", use_container_width=True):
            tasks = [task.strip() for task in tasks_input.splitlines() if task.strip()]
            st.session_state["tasks"] = tasks
            st.success("Tasks submitted!")


def prioritize_tasks() -> None:
    """
    Display the task prioritization section.
    Categorizes tasks into 'Urgent', 'Important', and 'Nice-to-Have'
    and saves the results to st.session_state.
    """
    if "tasks" in st.session_state:
        st.subheader("🎯 Prioritize Your Tasks")
        categorized_tasks: Dict[str, List[str]] = {"Urgent": [], "Important": [], "Nice-to-Have": []}
        for task in st.session_state["tasks"]:
            category = st.radio(
                f"Categorize: {task}",
                ["Urgent", "Important", "Nice-to-Have"],
                key=f"{task}_category",
                horizontal=True
            )
            categorized_tasks[category].append(task)
        st.session_state["categorized_tasks"] = categorized_tasks


def create_schedule() -> None:
    """
    Create the daily schedule using the categorized tasks.
    Allows syncing with Google Calendar, sends notifications,
    and saves the schedule to st.session_state.
    """
    if "categorized_tasks" in st.session_state:
        st.subheader("⏳ Create Your Daily Schedule")
        use_calendar = st.checkbox("Sync with Google Calendar")
        service = authenticate_google_calendar() if use_calendar else None
        schedule: List[Tuple[str, str]] = []
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        time_slot = now.replace(hour=8, minute=0)

        for category in ["Urgent", "Important", "Nice-to-Have"]:
            for task in st.session_state["categorized_tasks"][category]:
                duration = st.slider(
                    f"Duration (minutes) for '{task}'",
                    min_value=15,
                    max_value=120,
                    value=45,
                    step=15,
                    key=f"{task}_duration"
                )
                time_str = time_slot.strftime("%I:%M %p")
                schedule.append((time_str, task))
                if use_calendar and service:
                    add_to_calendar(service, task, time_slot, duration)
                reminder_time = time_slot - datetime.timedelta(minutes=5)
                if reminder_time > datetime.datetime.utcnow():
                    send_notification(task, time_str)
                time_slot += datetime.timedelta(minutes=duration)

        st.session_state["schedule"] = schedule
        save_schedule(schedule)
        st.success("✅ Schedule created!")


def review_schedule() -> None:
    """
    Display the optimized schedule and the evening review section.
    Allows users to mark tasks as completed.
    """
    if "schedule" in st.session_state:
        st.subheader("📌 Your Optimized Schedule")
        st.table(st.session_state["schedule"])
        st.subheader("🌙 Evening Review")
        completed_tasks = []
        for time_str, task in st.session_state["schedule"]:
            if st.checkbox(f"✅ Completed: {task} at {time_str}", key=f"{task}_completed"):
                completed_tasks.append(task)
        if st.button("Save Review", use_container_width=True):
            st.success("🎯 Review saved!")


def day_planner() -> None:
    """
    Main function to run the DayPlanner app.
    Sets up the page configuration, displays the title, and calls each section.
    """
    st.set_page_config(page_title="DayPlanner GPT", page_icon="logo.png", layout="wide")

    # Custom CSS for Neon Dark Mode vibe
    st.markdown("""
        <style>
            body, .main {
                background-color: #121212;
                color: #e0e0e0;
            }
            h1, h2, h3 {
                color: #03a9f4; /* Neon Blue */
                text-align: center;
            }
            .stButton button {
                background: linear-gradient(45deg, #39ff14, #bf00ff); /* Neon Green to Neon Purple */
                color: #ffffff;
                font-size: 16px;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                transition: transform 0.2s;
            }
            .stButton button:hover {
                transform: scale(1.05);
            }
            .stCheckbox div {
                font-size: 16px;
            }
            .inline-container {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            .inline-container img {
                height: 50px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Embed the logo image using base64 encoding
    logo_base64 = get_base64_image("logo.png")
    if logo_base64:
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' alt='Logo'>"
    else:
        logo_html = "<div>Logo not found</div>"

    st.markdown(f"""
        <div class='inline-container'>
            {logo_html}
            <h1>DayPlanner GPT</h1>
        </div>
    """, unsafe_allow_html=True)

    # Display sections
    brain_dump()
    prioritize_tasks()
    create_schedule()
    review_schedule()


if __name__ == "__main__":
    day_planner()

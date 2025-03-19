import datetime
import os
import pickle
import json
import streamlit as st
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from plyer import notification

def authenticate_google_calendar():
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

def add_to_calendar(service, task, start_time):
    event = {
        'summary': task,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (start_time + datetime.timedelta(minutes=45)).isoformat(), 'timeZone': 'UTC'},
    }
    service.events().insert(calendarId='primary', body=event).execute()

def send_notification(task, time):
    notification.notify(
        title="Upcoming Task Reminder",
        message=f"Task: {task} at {time}",
        timeout=10
    )

def save_schedule(schedule, filename="schedule_history.json"):
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

def load_schedule_history(filename="schedule_history.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def day_planner():
    st.title("📅 DayPlanner GPT")
    st.subheader("Plan your day efficiently with prioritization and scheduling")
    
    # Brain Dump Section
    tasks_input = st.text_area("Enter your tasks (one per line):")
    if st.button("Submit Tasks"):
        tasks = tasks_input.split("\n")
        tasks = [task.strip() for task in tasks if task.strip()]
        st.session_state["tasks"] = tasks
        st.success("Tasks submitted!")
    
    # Prioritization
    if "tasks" in st.session_state:
        st.subheader("🎯 Prioritize Your Tasks")
        categorized_tasks = {"Urgent": [], "Important": [], "Nice-to-Have": []}
        for task in st.session_state["tasks"]:
            category = st.radio(f"Categorize: {task}", ["Urgent", "Important", "Nice-to-Have"], key=task)
            categorized_tasks[category].append(task)
        st.session_state["categorized_tasks"] = categorized_tasks
    
    # Schedule Creation
    if "categorized_tasks" in st.session_state:
        st.subheader("⏳ Create Your Daily Schedule")
        use_calendar = st.checkbox("Sync with Google Calendar")
        service = authenticate_google_calendar() if use_calendar else None
        schedule = []
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        time_slot = now.replace(hour=8, minute=0)
        for category in ["Urgent", "Important", "Nice-to-Have"]:
            for task in st.session_state["categorized_tasks"][category]:
                duration = st.number_input(f"Duration (minutes) for '{task}'", min_value=15, max_value=120, value=45, step=15, key=f"{task}_duration")
                schedule.append((time_slot.strftime("%I:%M %p"), task))
                if use_calendar:
                    add_to_calendar(service, task, time_slot)
                reminder_time = time_slot - datetime.timedelta(minutes=5)
                if reminder_time > datetime.datetime.utcnow():
                    send_notification(task, time_slot.strftime("%I:%M %p"))
                time_slot += datetime.timedelta(minutes=duration)
        st.session_state["schedule"] = schedule
        save_schedule(schedule)
        st.success("Schedule created!")
    
    # Display Schedule
    if "schedule" in st.session_state:
        st.subheader("📌 Your Optimized Schedule")
        for time, task in st.session_state["schedule"]:
            st.write(f"**{time}** - {task}")
    
    # Evening Review
    if "schedule" in st.session_state:
        st.subheader("🌙 Evening Review")
        completed_tasks = []
        for time, task in st.session_state["schedule"]:
            if st.checkbox(f"Completed: {task} at {time}", key=f"{task}_completed"):
                completed_tasks.append(task)
        if st.button("Save Review"):
            st.success("Review saved!")

if __name__ == "__main__":
    day_planner()
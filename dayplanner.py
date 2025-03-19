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
    st.set_page_config(page_title="DayPlanner GPT", page_icon="logo.png", layout="wide")
    
    st.markdown("""
        <style>
            .main {background-color: #f5f7fa;}
            h1, h2, h3 {color: #2c3e50; text-align: center;}
            .stButton button {background-color: #4CAF50; color: white; font-size: 16px;}
            .stCheckbox div {font-size: 16px;}
            .inline-container {display: flex; align-items: center; justify-content: center; gap: 10px;}
            .inline-container img {height: 50px;}
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 10])
    with col1:
      st.image("logo.png", width=100)
    with col2:
      st.markdown("<h1 style='display: inline-block; vertical-align: middle;'>DayPlanner</h1>", unsafe_allow_html=True)

    
    with st.expander("📝 Brain Dump - Add Your Tasks"):
        tasks_input = st.text_area("Enter your tasks (one per line):")
        if st.button("Submit Tasks", use_container_width=True):
            tasks = tasks_input.split("\n")
            tasks = [task.strip() for task in tasks if task.strip()]
            st.session_state["tasks"] = tasks
            st.success("Tasks submitted!")
    
    if "tasks" in st.session_state:
        st.subheader("🎯 Prioritize Your Tasks")
        categorized_tasks = {"Urgent": [], "Important": [], "Nice-to-Have": []}
        for task in st.session_state["tasks"]:
            category = st.radio(f"Categorize: {task}", ["Urgent", "Important", "Nice-to-Have"], key=task, horizontal=True)
            categorized_tasks[category].append(task)
        st.session_state["categorized_tasks"] = categorized_tasks
    
    if "categorized_tasks" in st.session_state:
        st.subheader("⏳ Create Your Daily Schedule")
        use_calendar = st.checkbox("Sync with Google Calendar")
        service = authenticate_google_calendar() if use_calendar else None
        schedule = []
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        time_slot = now.replace(hour=8, minute=0)
        for category in ["Urgent", "Important", "Nice-to-Have"]:
            for task in st.session_state["categorized_tasks"][category]:
                duration = st.slider(f"Duration (minutes) for '{task}'", min_value=15, max_value=120, value=45, step=15, key=f"{task}_duration")
                schedule.append((time_slot.strftime("%I:%M %p"), task))
                if use_calendar:
                    add_to_calendar(service, task, time_slot)
                reminder_time = time_slot - datetime.timedelta(minutes=5)
                if reminder_time > datetime.datetime.utcnow():
                    send_notification(task, time_slot.strftime("%I:%M %p"))
                time_slot += datetime.timedelta(minutes=duration)
        st.session_state["schedule"] = schedule
        save_schedule(schedule)
        st.success("✅ Schedule created!")
    
    if "schedule" in st.session_state:
        st.subheader("📌 Your Optimized Schedule")
        st.table(st.session_state["schedule"])
    
    if "schedule" in st.session_state:
        st.subheader("🌙 Evening Review")
        completed_tasks = []
        for time, task in st.session_state["schedule"]:
            if st.checkbox(f"✅ Completed: {task} at {time}", key=f"{task}_completed"):
                completed_tasks.append(task)
        if st.button("Save Review", use_container_width=True):
            st.success("🎯 Review saved!")

if __name__ == "__main__":
    day_planner()

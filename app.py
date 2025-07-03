# FocusCam - Godfred Bio | Improved Version with Accurate Timers & Layout

import cv2
import mediapipe as mp
import math
import time
import random
from datetime import datetime
import csv
import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
import json
import pyttsx3

# --- Config ---
SNAPSHOT_FOLDER = "snapshots"
QUOTE_FILE = "data/quotes.json"
LOG_FILE = "logs/focuscam_session_log.csv"
SETTINGS_FILE = "data/settings.json"

os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# --- Settings ---
def load_settings():
    default = {"duration": 30, "goal": "", "username": "User"}
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default, f)
    with open(SETTINGS_FILE) as f:
        return json.load(f)

def save_settings(s):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(s, f, indent=4)

settings = load_settings()

# --- Quotes ---
def load_quotes():
    default_quotes = {
        "motivational": ["Stay focused.", "You're investing in your future."],
        "punishing": ["Discipline matters.", "Each distraction counts."]
    }
    if not os.path.exists(QUOTE_FILE):
        with open(QUOTE_FILE, 'w') as f:
            json.dump(default_quotes, f)
    with open(QUOTE_FILE) as f:
        return json.load(f)

def save_quotes(quotes):
    with open(QUOTE_FILE, 'w') as f:
        json.dump(quotes, f, indent=4)

quotes = load_quotes()

# --- Utils ---
def play_alert_sound():
    try:
        import winsound
        winsound.Beep(1000, 500)
    except:
        pass

def speak(text):
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except:
        pass

def get_quote(focus_percent):
    if focus_percent >= 90:
        return random.choice(quotes["motivational"])
    elif focus_percent >= 70:
        return "Good job! You can do even better!"
    else:
        return random.choice(quotes["punishing"])

def calculate_head_pitch(nose, chin):
    return math.degrees(math.atan2(chin.y - nose.y, 0.1))

def estimate_gaze(left_eye, right_eye):
    gaze = (left_eye.y + right_eye.y) / 2
    return gaze < 0.5

def save_snapshot(frame):
    filename = os.path.join(SNAPSHOT_FOLDER, f"distraction_{int(time.time())}.jpg")
    cv2.imwrite(filename, frame)

def export_raw_csv():
    file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if file:
        with open(LOG_FILE, 'r') as src, open(file, 'w', newline='') as dst:
            dst.writelines(src.readlines())
        messagebox.showinfo("Export Complete", f"Log exported to {file}")

# --- Global Pause Variable ---
paused = False
def toggle_pause():
    global paused
    paused = not paused
    pause_btn.config(text="▶️ Resume Session" if paused else "⏸️ Pause Session")

# --- Focus Session ---
def start_focus_session():
    global paused
    duration = settings["duration"] * 60  # in seconds
    username = settings.get("username", "User")
    goal = settings.get("goal", "").strip()

    cap = cv2.VideoCapture(0)
    face_mesh = mp.solutions.face_mesh.FaceMesh()

    start_time = time.time()
    last_time = time.time()
    focused_seconds = 0
    distracted_seconds = 0
    last_alert = time.time()
    distraction_count = 0

    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if not ret:
            break

        if paused:
            last_time = time.time()
            cv2.putText(frame, "PAUSED", (frame.shape[1]//2 - 70, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            cv2.imshow("FocusCam", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        is_focused = False
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            nose = face.landmark[1]
            chin = face.landmark[152]
            left_eye, right_eye = face.landmark[33], face.landmark[263]
            pitch = calculate_head_pitch(nose, chin)
            gaze = estimate_gaze(left_eye, right_eye)
            is_focused = (-10 <= pitch <= 70) and gaze

        now = time.time()
        elapsed = now - last_time
        last_time = now

        if is_focused:
            focused_seconds += elapsed
        else:
            distracted_seconds += elapsed
            if now - last_alert > 5:
                distraction_count += 1
                play_alert_sound()
                speak(f"{username}, please focus.")
                save_snapshot(frame)
                if distraction_count == 5 and goal:
                    speak(f"Remember your goal: {goal}")
                elif distraction_count == 10:
                    speak(random.choice(quotes["punishing"]))
                last_alert = now

        total_seconds = focused_seconds + distracted_seconds
        focus_percent = int((focused_seconds / total_seconds) * 100) if total_seconds else 0
        remaining = max(0, duration - (now - start_time))
        mins = int(remaining) // 60
        secs = int(remaining) % 60

        cv2.putText(frame, f"{username} | Focus: {focus_percent}%", (frame.shape[1]-270, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0) if is_focused else (0,0,255), 2)
        cv2.putText(frame, f"Time Left: {mins:02}:{secs:02}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        cv2.imshow("FocusCam", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    focus_min = round(focused_seconds / 60, 2)
    distract_min = round(distracted_seconds / 60, 2)
    final_quote = get_quote(focus_percent)
    goal_display = f"\nGoal: {goal}" if goal else ""

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, focus_min, distract_min])

    messagebox.showinfo("Session Complete",
        f"Focus: {focus_min} min\nDistracted: {distract_min} min\nFocus %: {focus_percent}%\n{final_quote}{goal_display}")

# --- Quote Editor ---
def open_quote_editor():
    editor = tk.Toplevel()
    editor.title("Edit Quotes")

    category = tk.StringVar(value="motivational")
    def refresh():
        listbox.delete(0, tk.END)
        for q in quotes[category.get()]:
            listbox.insert(tk.END, q)
    def add():
        q = simpledialog.askstring("Add Quote", "Enter quote:")
        if q:
            quotes[category.get()].append(q)
            save_quotes(quotes)
            refresh()
    def delete():
        sel = listbox.curselection()
        if sel:
            quotes[category.get()].pop(sel[0])
            save_quotes(quotes)
            refresh()

    tk.Radiobutton(editor, text="Motivational", variable=category, value="motivational", command=refresh).pack()
    tk.Radiobutton(editor, text="Punishing", variable=category, value="punishing", command=refresh).pack()

    listbox = tk.Listbox(editor, width=50)
    listbox.pack(padx=10, pady=10)
    tk.Button(editor, text="Add", command=add).pack(side="left", padx=10)
    tk.Button(editor, text="Delete", command=delete).pack(side="left", padx=10)
    refresh()

# --- GUI Init ---
app = tk.Tk()
app.title("FocusCam Study Assistant")
frame = ttk.Frame(app, padding=20)
frame.pack()

ttk.Label(frame, text="Enter Name:").pack()
name_entry = ttk.Entry(frame)
name_entry.insert(0, settings.get("username", "User"))
name_entry.pack()

ttk.Label(frame, text="Duration (minutes):").pack()
duration_entry = ttk.Entry(frame)
duration_entry.insert(0, str(settings.get("duration", 30)))
duration_entry.pack()

ttk.Label(frame, text="Goal for this session:").pack()
goal_entry = ttk.Entry(frame)
goal_entry.insert(0, settings.get("goal", ""))
goal_entry.pack()

def update_settings_and_run():
    settings["username"] = name_entry.get()
    settings["duration"] = int(duration_entry.get())
    settings["goal"] = goal_entry.get()
    save_settings(settings)
    threading.Thread(target=start_focus_session, daemon=True).start()

ttk.Button(frame, text="🎯 Start Focus Session", command=update_settings_and_run).pack(pady=10)
pause_btn = ttk.Button(frame, text="⏸️ Pause Session", command=toggle_pause)
pause_btn.pack(pady=5)
ttk.Button(frame, text="📝 Edit Quotes", command=open_quote_editor).pack(pady=5)
ttk.Button(frame, text="📤 Export CSV", command=export_raw_csv).pack(pady=5)

creator = ttk.Label(frame, text="Made by Godfred Bio | GitHub: godfredsprim | YouTube: GoddAura | WhatsApp: +233599966902", font=("Segoe UI", 9))
creator.pack(pady=10)

app.mainloop()

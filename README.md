# GHOST – AI Voice Assistant (Django Web Application)

A cyberpunk futuristic AI Voice Assistant dashboard built with **Django** and **Vanilla JS / Web Audio & Speech APIs**.

---

## ⚡ Features

- **Cyberpunk Sci-Fi UI**: Animated reactor core SVG, sound synthesizer (Web Audio API), holographic scanline effect, and dynamic audio visualizer waves.
- **Voice Link (Speech-to-Text & Spoken Response)**:
  - English & Tamil speech recognition (`webkitSpeechRecognition`).
  - Text-to-speech feedback via `SpeechSynthesis` with automatic language detection (`ta-IN` / `en-US`).
- **Django SQLite Backend**:
  - `Task`: Check, uncheck, and create tasks.
  - `ScheduleItem`: Track meetings and calendar events.
  - `Reminder`: Time-based alerts and active countdowns.
  - `PhoneMessage`: AI call answering service with voicemail simulation.
  - `DailyPlan`: Auto-sequenced daily scheduling.
- **RESTful Endpoints**:
  - `/api/command/` - Natural language command processing (English & Tamil).
  - `/api/tasks/` - Task management.
  - `/api/reminders/` - Reminders API.
  - `/api/schedule/` - Schedule & bookings.
  - `/api/messages/` - Phone message reception & call simulator.
  - `/api/plan/` - Daily plan generator.
- **Django Admin GUI**: Access `/admin/` to manage records directly.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py makemigrations assistant
python manage.py migrate
```

### 3. (Optional) Create Admin User
```bash
python manage.py createsuperuser
```

### 4. Start the Server
```bash
python manage.py runserver
```
or simply double-click **`run.bat`**.

Then open your browser at:
👉 **`http://127.0.0.1:8000/`**


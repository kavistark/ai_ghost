# GHOST – AI Voice Assistant (Django Web Application)

A cyberpunk futuristic AI Voice Assistant dashboard built with **Django** and **Vanilla JS / Web Audio & Speech APIs**.

---

## ⚡ Features

- **Cyberpunk Sci-Fi UI**: Animated reactor core SVG, sound synthesizer (Web Audio API), holographic scanline effect, and dynamic audio visualizer waves.
- **Dual-Agent Architecture (Gemini + Claude)**:
  - **Gemini (Front-line Voice Agent)**: Handles incoming user voice and text, generating immediate conversational spoken replies in **English** or **Tamil**, answering queries, and confirming dashboard actions.
  - **Claude (Autonomous Task & Memory Agent)**: Handles assigned multi-step tasks, autonomous agent goals, workflow planning, and retains long-term agent memories (`AgentMemory` & `AgentTaskExecution`).
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
  - `/api/command/` - Natural language command processing powered by Gemini / Claude (English & Tamil).
  - `/api/tasks/` - Task management.
  - `/api/reminders/` - Reminders API.
  - `/api/schedule/` - Schedule & bookings.
  - `/api/messages/` - Phone message reception & call simulator.
  - `/api/plan/` - Daily plan generator.
- **Django Admin GUI**: Access `/admin/` to manage records directly.

---

## 🔑 AI Configuration (.env)

API keys and AI settings are stored in `.env`:
```ini
ANTHROPIC_API_KEY=apikey_0134DZBvsKi1aVKoGG4cFDwh
GEMINI_API_KEY=AQ.Ab8RN6Ldz2LqFB_US7s5E3mfX--T2aMrwnJavLwCOdAObH9saQ
AI_PROVIDER=auto              # auto | gemini | claude
GEMINI_MODEL=gemini-3.8-flash
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

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


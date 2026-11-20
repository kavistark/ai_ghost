import json
import re
from datetime import datetime, date
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Task, ScheduleItem, Reminder, PhoneMessage, DailyPlan


def ensure_seed_data():
    """Ensure baseline initial records exist if database is fresh."""
    if not Task.objects.exists():
        Task.objects.create(text='Send invoice to client', completed=False)
        Task.objects.create(text='Prepare demo slides', completed=False)
        Task.objects.create(text='Book train tickets', completed=True)

    if not ScheduleItem.objects.exists():
        today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
        ScheduleItem.objects.create(time='09:30', title='Stand-up call', date=today)
        ScheduleItem.objects.create(time='11:00', title='Doctor appointment', date=today)
        ScheduleItem.objects.create(time='15:00', title='Design review', date=today)
        ScheduleItem.objects.create(time='19:00', title='Gym', date=today)

    if not Reminder.objects.exists():
        Reminder.objects.create(time='18:00', text='Call mom')
        Reminder.objects.create(time='21:00', text='Take medicine')

    if not PhoneMessage.objects.exists():
        PhoneMessage.objects.create(
            caller='Karthik',
            time_label='10:42',
            message='“Move tomorrow’s demo to 4 PM?” Pending your approval.'
        )
        PhoneMessage.objects.create(
            caller='Unknown',
            time_label='09:15',
            message='Courier. Asked to leave it with security.'
        )

    if not DailyPlan.objects.exists():
        default_items = [
            ('09:00', 'Deep work: demo slides', 1),
            ('10:30', 'Leave for doctor', 2),
            ('13:00', 'Lunch, send invoice', 3),
            ('15:00', 'Design review', 4),
            ('18:00', 'Call mom', 5),
            ('19:00', 'Gym', 6),
        ]
        for t, act, ord_idx in default_items:
            DailyPlan.objects.create(time=t, activity=act, order=ord_idx)


def dashboard(request):
    """Renders the main futuristic cyberpunk GHOST UI."""
    ensure_seed_data()
    tasks = [t.to_dict() for t in Task.objects.all()]
    schedule = [s.to_dict() for s in ScheduleItem.objects.all()]
    reminders = [r.to_dict() for r in Reminder.objects.filter(is_active=True)]
    messages = [m.to_dict() for m in PhoneMessage.objects.all()]
    plan = [p.to_dict() for p in DailyPlan.objects.all()]

    context = {
        'tasks_json': json.dumps(tasks),
        'schedule_json': json.dumps(schedule),
        'reminders_json': json.dumps(reminders),
        'messages_json': json.dumps(messages),
        'plan_json': json.dumps(plan),
    }
    return render(request, 'assistant/index.html', context)


# --- RESTful APIs ---

@csrf_exempt
def api_tasks(request):
    ensure_seed_data()
    if request.method == 'GET':
        tasks = [t.to_dict() for t in Task.objects.all()]
        return JsonResponse({'status': 'ok', 'tasks': tasks})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        action = data.get('action', 'add')
        if action == 'toggle':
            task_id = data.get('id')
            completed = data.get('completed')
            task = Task.objects.filter(id=task_id).first()
            if task:
                task.completed = bool(completed)
                task.save()
                return JsonResponse({'status': 'ok', 'task': task.to_dict()})
            return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
        else:
            text = data.get('text', '').strip()
            if not text:
                return JsonResponse({'status': 'error', 'message': 'Task text is required'}, status=400)
            task = Task.objects.create(text=text, completed=False)
            return JsonResponse({'status': 'ok', 'task': task.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_reminders(request):
    ensure_seed_data()
    if request.method == 'GET':
        reminders = [r.to_dict() for r in Reminder.objects.filter(is_active=True)]
        return JsonResponse({'status': 'ok', 'reminders': reminders})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        text = data.get('text', '').strip()
        time_str = data.get('time', '18:00').strip()
        if not text:
            return JsonResponse({'status': 'error', 'message': 'Reminder text required'}, status=400)

        reminder = Reminder.objects.create(text=text, time=time_str)
        return JsonResponse({'status': 'ok', 'reminder': reminder.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_schedule(request):
    ensure_seed_data()
    if request.method == 'GET':
        items = [s.to_dict() for s in ScheduleItem.objects.all()]
        return JsonResponse({'status': 'ok', 'schedule': items})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        title = data.get('title', '').strip()
        time_str = data.get('time', '09:00').strip()
        date_str = data.get('date')

        if not title:
            return JsonResponse({'status': 'error', 'message': 'Schedule title required'}, status=400)

        target_date = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        item = ScheduleItem.objects.create(title=title, time=time_str, date=target_date)
        return JsonResponse({'status': 'ok', 'schedule_item': item.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_messages(request):
    ensure_seed_data()
    if request.method == 'GET':
        msgs = [m.to_dict() for m in PhoneMessage.objects.all()]
        return JsonResponse({'status': 'ok', 'messages': msgs})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        caller = data.get('caller', 'Unknown Caller').strip()
        message = data.get('message', 'Left a voicemail.').strip()
        now_time = datetime.now().strftime('%H:%M')

        msg_obj = PhoneMessage.objects.create(caller=caller, time_label=now_time, message=message)
        return JsonResponse({'status': 'ok', 'message_item': msg_obj.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_plan(request):
    ensure_seed_data()
    if request.method == 'GET':
        plans = [p.to_dict()['text'] for p in DailyPlan.objects.all()]
        return JsonResponse({'status': 'ok', 'plan': plans})

    elif request.method == 'POST':
        plans = [p.to_dict()['text'] for p in DailyPlan.objects.all()]
        return JsonResponse({'status': 'ok', 'plan': plans})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def parse_time_str(s):
    if not s:
        return '09:00'
    m = re.search(r'(\d{1,2})(?::(\d\d))?\s*(am|pm)?', s, re.IGNORECASE)
    if not m:
        return '09:00'
    h = int(m.group(1))
    mins = m.group(2) or '00'
    ap = (m.group(3) or '').lower()
    if ap == 'pm' and h < 12:
        h += 12
    elif ap == 'am' and h == 12:
        h = 0
    return f"{h:02d}:{mins}"


@csrf_exempt
def api_command(request):
    """
    Ghost NLP Brain endpoint:
    Parses natural language commands in English or Tamil, creates/updates
    database objects accordingly, and returns spoken reply + client actions.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'reply': 'Ghost standing by.', 'actions': []})

    clean_text = re.sub(r'^(hey\s+|ok\s+)?ghost[,.!\s]*', '', text, flags=re.IGNORECASE).strip()
    lower = clean_text.lower()
    actions = []
    reply = ""

    # 1. Reminder
    m_rem = re.search(r'remind me to (.+?)(?: at (.+))?$', clean_text, re.IGNORECASE)
    if m_rem:
        rem_text = m_rem.group(1).strip()
        rem_time = parse_time_str(m_rem.group(2))
        Reminder.objects.create(text=rem_text, time=rem_time)
        reply = f"Reminder set for {rem_text} at {rem_time}."
        actions.append({'type': 'add_reminder', 'text': rem_text, 'time': rem_time})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 2. Add Task
    m_task = re.search(r'add (?:a )?task (?:to )?(.+)', clean_text, re.IGNORECASE)
    if m_task:
        task_text = m_task.group(1).strip()
        Task.objects.create(text=task_text, completed=False)
        reply = f"Task added: {task_text}."
        actions.append({'type': 'add_task', 'text': task_text})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 3. Complete Task
    m_done = re.search(r'(?:finish|complete|done with) (.+)', lower)
    if m_done:
        target = m_done.group(1).strip()
        t = Task.objects.filter(text__icontains=target).first()
        if t:
            t.completed = True
            t.save()
            reply = f"Marked task '{t.text}' as done."
            actions.append({'type': 'complete_task', 'text': t.text})
        else:
            reply = f"Couldn't find matching task for '{target}'."
        return JsonResponse({'reply': reply, 'actions': actions})

    # 4. Plan my day
    if 'plan' in lower:
        plans = [p.to_dict()['text'] for p in DailyPlan.objects.all()]
        reply = "Here is your plan for today."
        actions.append({'type': 'create_plan', 'items': plans})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 5. Search
    m_search = re.search(r'search (?:for )?(.+)', lower)
    if m_search:
        q = m_search.group(1).strip()
        reply = f"Searching Google for {q}."
        actions.append({'type': 'search_web', 'query': q})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 6. Jobs
    if 'job' in lower:
        reply = "Searching for AI and engineering roles."
        actions.append({'type': 'search_web', 'query': 'AI engineer jobs India remote'})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 7. Agent
    if 'agent' in lower:
        reply = "Autonomous agent started. I will ask before making any bookings or calls."
        actions.append({'type': 'run_agent', 'goal': 'Find remote AI engineer roles and summarize'})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 8. Call answering toggle
    if any(k in lower for k in ['call', 'phone', 'answer']) and any(k in lower for k in ['off', 'stop', 'pause']):
        reply = "AI call answering is now off."
        actions.append({'type': 'call_service', 'on': False})
        return JsonResponse({'reply': reply, 'actions': actions})

    if any(k in lower for k in ['call', 'phone', 'answer']) and any(k in lower for k in ['on', 'start', 'resume']):
        reply = "AI call answering is now active."
        actions.append({'type': 'call_service', 'on': True})
        return JsonResponse({'reply': reply, 'actions': actions})

    # 9. Next meeting / schedule
    if 'meeting' in lower or 'schedule' in lower:
        next_item = ScheduleItem.objects.first()
        if next_item:
            reply = f"Next up: {next_item.title} at {next_item.time}."
        else:
            reply = "You have no scheduled meetings today."
        return JsonResponse({'reply': reply, 'actions': actions})

    # 10. Messages / calls
    if 'message' in lower or 'missed' in lower:
        count = PhoneMessage.objects.count()
        reply = f"You have {count} messages waiting."
        return JsonResponse({'reply': reply, 'actions': actions})

    # 11. Theme
    if 'light' in lower:
        reply = "Light mode activated."
        actions.append({'type': 'set_theme', 'mode': 'light'})
        return JsonResponse({'reply': reply, 'actions': actions})

    if 'dark' in lower:
        reply = "Dark mode activated."
        actions.append({'type': 'set_theme', 'mode': 'dark'})
        return JsonResponse({'reply': reply, 'actions': actions})

    # Tamil commands
    if 'வணக்கம்' in lower:
        reply = "வணக்கம்! நான் கோஸ்ட். உங்களுக்கு என்ன உதவி வேண்டும்?"
        return JsonResponse({'reply': reply, 'actions': actions})

    if 'நன்றி' in lower:
        reply = "மிக்க மகிழ்ச்சி!"
        return JsonResponse({'reply': reply, 'actions': actions})

    # Default fallback
    reply = f"Command recognized. I can manage tasks, schedule, reminders, calls, and web searches."
    return JsonResponse({'reply': reply, 'actions': actions})

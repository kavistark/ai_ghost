import json
import re
import logging
from datetime import datetime, date, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Task, ScheduleItem, Reminder, PhoneMessage, DailyPlan, AgentMemory, AgentTaskExecution, SearchHistory, SystemSetting
from .ai_service import gemini_voice_reply, claude_execute_agent_task

logger = logging.getLogger(__name__)


def ensure_seed_data():
    """Ensure baseline initial records exist if database is fresh."""
    if not Task.objects.exists():
        Task.objects.create(text='Send invoice to client', completed=False)
        Task.objects.create(text='Prepare demo slides', completed=False)
        Task.objects.create(text='Book train tickets', completed=True)

    today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()

    if not ScheduleItem.objects.exists():
        ScheduleItem.objects.create(time='09:30', title='Stand-up call', date=today)
        ScheduleItem.objects.create(time='11:00', title='Doctor appointment', date=today)
        ScheduleItem.objects.create(time='15:00', title='Design review', date=today)
        ScheduleItem.objects.create(time='19:00', title='Gym', date=today)

    if not Reminder.objects.exists():
        Reminder.objects.create(time='18:00', text='Call mom', date=today)
        Reminder.objects.create(time='21:00', text='Take medicine', date=today)

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

    if not AgentMemory.objects.exists():
        AgentMemory.objects.create(category='preference', content='User prefers remote Python and AI engineering roles.')
        AgentMemory.objects.create(category='contact', content='Karthik is the lead developer on demo slides.')
        AgentMemory.objects.create(category='fact', content='Office standup call takes place at 09:30 AM.')

    if not SearchHistory.objects.exists():
        SearchHistory.objects.create(query='Top remote Python AI jobs', category='jobs', result_summary='Identified 12 verified roles across European & US tech hubs.')
        SearchHistory.objects.create(query='Django 5.0 async ORM features', category='tech', result_summary='Async queries and generated columns overview compiled.')

    if not SystemSetting.objects.filter(key='phone_service_enabled').exists():
        SystemSetting.objects.create(key='phone_service_enabled', value='true')

    SystemSetting.objects.update_or_create(key='security_code_word', defaults={'value': 'codex'})


def dashboard(request):
    """Renders the main futuristic cyberpunk GHOST UI."""
    ensure_seed_data()
    tasks = [t.to_dict() for t in Task.objects.all()]
    schedule = [s.to_dict() for s in ScheduleItem.objects.all()]
    reminders = [r.to_dict() for r in Reminder.objects.filter(is_active=True)]
    messages = [m.to_dict() for m in PhoneMessage.objects.all()]
    plan = [p.to_dict() for p in DailyPlan.objects.all()]
    memories = [m.to_dict() for m in AgentMemory.objects.all()[:10]]
    search_history = [s.to_dict() for s in SearchHistory.objects.all()[:10]]
    settings_dict = {s.key: s.value for s in SystemSetting.objects.all()}
    last_agent_run = AgentTaskExecution.objects.first()

    context = {
        'tasks_json': json.dumps(tasks),
        'schedule_json': json.dumps(schedule),
        'reminders_json': json.dumps(reminders),
        'messages_json': json.dumps(messages),
        'plan_json': json.dumps(plan),
        'memories_json': json.dumps(memories),
        'search_history_json': json.dumps(search_history),
        'settings_json': json.dumps(settings_dict),
        'agent_run_json': json.dumps(last_agent_run.to_dict() if last_agent_run else None)
    }
    return render(request, 'assistant/index.html', context)


# --- RESTful Data APIs ---

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

        elif action == 'delete':
            task_id = data.get('id')
            text_query = data.get('text', '').strip()
            if task_id:
                Task.objects.filter(id=task_id).delete()
            elif text_query:
                Task.objects.filter(text__icontains=text_query).delete()
            return JsonResponse({'status': 'ok', 'message': 'Deleted'})

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

        action = data.get('action', 'add')
        if action == 'delete':
            rem_id = data.get('id')
            text_query = data.get('text', '').strip()
            if rem_id:
                Reminder.objects.filter(id=rem_id).delete()
            elif text_query:
                Reminder.objects.filter(text__icontains=text_query).delete()
            return JsonResponse({'status': 'ok', 'message': 'Deleted'})

        elif action == 'toggle':
            rem_id = data.get('id')
            rem = Reminder.objects.filter(id=rem_id).first()
            if rem:
                rem.is_active = not rem.is_active
                rem.save()
                return JsonResponse({'status': 'ok', 'reminder': rem.to_dict()})
            return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)

        text = data.get('text', '').strip()
        time_str = parse_time_str(data.get('time', '18:00'))
        date_str = data.get('date')
        if not text:
            return JsonResponse({'status': 'error', 'message': 'Reminder text required'}, status=400)

        target_date = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        reminder = Reminder.objects.create(text=text, time=time_str, date=target_date)
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

        action = data.get('action', 'add')
        if action == 'delete':
            item_id = data.get('id')
            if item_id:
                ScheduleItem.objects.filter(id=item_id).delete()
            return JsonResponse({'status': 'ok', 'message': 'Deleted'})

        title = data.get('title', '').strip()
        time_str = parse_time_str(data.get('time', '09:00'))
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
        svc_setting = SystemSetting.objects.filter(key='phone_service_enabled').first()
        svc_on = (svc_setting.value.lower() == 'true') if svc_setting else True
        return JsonResponse({'status': 'ok', 'messages': msgs, 'service_enabled': svc_on})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        action = data.get('action', 'add')
        if action == 'toggle_service':
            state = data.get('enabled')
            svc_setting, _ = SystemSetting.objects.get_or_create(key='phone_service_enabled')
            if state is not None:
                svc_setting.value = 'true' if state else 'false'
            else:
                svc_setting.value = 'false' if svc_setting.value == 'true' else 'true'
            svc_setting.save()
            return JsonResponse({'status': 'ok', 'service_enabled': svc_setting.value == 'true'})

        elif action == 'clear':
            PhoneMessage.objects.all().delete()
            return JsonResponse({'status': 'ok', 'messages': []})

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
        plans = [p.to_dict() for p in DailyPlan.objects.all()]
        return JsonResponse({'status': 'ok', 'plan': plans})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        action = data.get('action', 'create')
        if action == 'create' or action == 'set':
            items = data.get('items', [])
            DailyPlan.objects.all().delete()
            new_objs = []
            for idx, itm in enumerate(items, 1):
                if isinstance(itm, dict):
                    t = itm.get('time', '09:00')
                    act = itm.get('activity') or itm.get('text', '')
                else:
                    parts = str(itm).split(' ', 1)
                    t = parts[0] if len(parts) > 1 and re.match(r'^\d{1,2}:\d{2}', parts[0]) else '09:00'
                    act = parts[1] if len(parts) > 1 and re.match(r'^\d{1,2}:\d{2}', parts[0]) else str(itm)
                new_objs.append(DailyPlan(time=t, activity=act, order=idx))
            DailyPlan.objects.bulk_create(new_objs)
            return JsonResponse({'status': 'ok', 'plan': [p.to_dict() for p in DailyPlan.objects.all()]})

        elif action == 'add':
            t = data.get('time', '09:00')
            act = data.get('activity', '').strip()
            if act:
                cnt = DailyPlan.objects.count()
                p = DailyPlan.objects.create(time=t, activity=act, order=cnt+1)
                return JsonResponse({'status': 'ok', 'item': p.to_dict()})
            return JsonResponse({'status': 'error', 'message': 'Activity required'}, status=400)

        elif action == 'delete':
            p_id = data.get('id')
            if p_id:
                DailyPlan.objects.filter(id=p_id).delete()
            return JsonResponse({'status': 'ok', 'message': 'Deleted'})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_search(request):
    ensure_seed_data()
    if request.method == 'GET':
        history = [s.to_dict() for s in SearchHistory.objects.all()[:15]]
        return JsonResponse({'status': 'ok', 'history': history})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        query = data.get('query', '').strip()
        category = data.get('category', 'web')
        if not query:
            return JsonResponse({'status': 'error', 'message': 'Query required'}, status=400)

        summaries = {
            'info': f"Intelligence extracted for '{query}'. 4 operational vectors cross-checked with mission archives.",
            'sum': f"5-point tactical briefing generated for '{query}'. Key objectives and timeline compiled.",
            'jobs': f"Recon complete: 8 verified roles discovered for '{query}' across remote and defense contracting vectors.",
            'tech': f"Technical breakdown for '{query}' prepared with architecture patterns and execution notes.",
            'web': f"Recon telemetry confirmed for '{query}'. Intel filed in tactical records."
        }
        res_text = summaries.get(category, summaries['web'])
        rec = SearchHistory.objects.create(query=query, category=category, result_summary=res_text)
        return JsonResponse({'status': 'ok', 'record': rec.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_settings(request):
    ensure_seed_data()
    if request.method == 'GET':
        s = {setting.key: setting.value for setting in SystemSetting.objects.all()}
        return JsonResponse({'status': 'ok', 'settings': s})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        for k, v in data.items():
            setting, _ = SystemSetting.objects.get_or_create(key=k)
            setting.value = str(v)
            setting.save()

        s = {setting.key: setting.value for setting in SystemSetting.objects.all()}
        return JsonResponse({'status': 'ok', 'settings': s})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


# --- CLAUDE AGENT & MEMORY APIS ---

@csrf_exempt
def api_agent_run(request):
    ensure_seed_data()
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    goal = data.get('goal', '').strip() or 'Find 5 remote Python jobs and summarize'
    
    memories = [m.to_dict() for m in AgentMemory.objects.all()]
    context = {
        'tasks': [t.to_dict() for t in Task.objects.all()],
        'schedule': [s.to_dict() for s in ScheduleItem.objects.all()],
        'reminders': [r.to_dict() for r in Reminder.objects.filter(is_active=True)],
        'now': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

    agent_output = claude_execute_agent_task(goal, context, memories)

    if not agent_output:
        agent_output = {
            'steps': [
                f'Intel: Target goal locked - {goal}',
                'Recon: Accessing memory and operational records',
                'Extraction: Processing mission deliverables',
                'Standing by for your go-ahead'
            ],
            'status': 'needs_approval',
            'summary': f'Agent completed reconnaissance for {goal}.',
            'new_memories': [],
            'actions': []
        }

    for mem in agent_output.get('new_memories', []):
        cat = mem.get('category', 'general')
        cnt = mem.get('content', '').strip()
        if cnt and not AgentMemory.objects.filter(content__icontains=cnt).exists():
            AgentMemory.objects.create(category=cat, content=cnt, source='claude_agent')

    exec_record = AgentTaskExecution.objects.create(
        goal=goal,
        status=agent_output.get('status', 'needs_approval'),
        steps=agent_output.get('steps', []),
        summary=agent_output.get('summary', '')
    )

    return JsonResponse({
        'status': 'ok',
        'execution': exec_record.to_dict(),
        'actions': agent_output.get('actions', [])
    })


@csrf_exempt
def api_memories(request):
    ensure_seed_data()
    if request.method == 'GET':
        mems = [m.to_dict() for m in AgentMemory.objects.all()]
        return JsonResponse({'status': 'ok', 'memories': mems})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        category = data.get('category', 'general')
        content = data.get('content', '').strip()
        if not content:
            return JsonResponse({'status': 'error', 'message': 'Content required'}, status=400)

        mem = AgentMemory.objects.create(category=category, content=content, source='user')
        return JsonResponse({'status': 'ok', 'memory': mem.to_dict()})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def parse_time_str(s):
    if not s:
        return '09:00'
    m = re.search(r'(\d{1,2})(?::(\d\d))?\s*(am|pm)?', str(s), re.IGNORECASE)
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


def parse_date_str(s):
    if not s:
        return timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
    s = str(s).strip().lower()
    today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
    if s == 'tomorrow':
        return today + timedelta(days=1)
    if s == 'today':
        return today
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return today


def normalize_action(raw_act):
    if not isinstance(raw_act, dict):
        return None
    # Case 1: {'name': '...', 'parameters': {...}}
    if 'name' in raw_act and isinstance(raw_act.get('parameters'), dict):
        act = dict(raw_act['parameters'])
        act['type'] = raw_act['name']
        return act
    # Case 2: {'action': '...', 'parameters': {...}}
    if 'action' in raw_act and isinstance(raw_act.get('parameters'), dict):
        act = dict(raw_act['parameters'])
        act['type'] = raw_act['action']
        return act
    # Case 3: Single key dict like {'add_plan_item': {...}} or {'call_service': True}
    keys = list(raw_act.keys())
    if len(keys) == 1 and keys[0] not in ('type', 'action', 'name', 'reply', 'intent'):
        k = keys[0]
        v = raw_act[k]
        act = {'type': k}
        if isinstance(v, dict):
            act.update(v)
        elif isinstance(v, bool):
            act['on'] = v
        return act
    # Case 4: Standard {'type': '...', ...} or {'action': '...', ...}
    act = dict(raw_act)
    act['type'] = act.get('type') or act.get('action') or act.get('name')
    return act


def sync_actions_to_database(actions):
    """
    Applies any structured actions (from Gemini LLM or Local NLP)
    directly into SQLite database models so every state modification is persisted.
    """
    synced = []
    if not isinstance(actions, list):
        return synced

    for raw_act in actions:
        act = normalize_action(raw_act)
        if not act:
            continue
        act_type = act.get('type') or act.get('action') or act.get('intent')
        if not act_type or not isinstance(act_type, str):
            continue
        act['type'] = act_type

        try:
            # 1. TASKS
            if act_type == 'add_task':
                t_text = act.get('text') or act.get('task') or act.get('name') or act.get('title')
                if t_text:
                    act['text'] = t_text
                    t_obj = Task.objects.create(text=t_text, completed=False)
                    act['id'] = t_obj.id
            elif act_type == 'edit_task':
                old_name = act.get('old') or act.get('old_name') or act.get('target') or ''
                new_text = act.get('text') or act.get('new') or act.get('task') or act.get('name') or ''
                if new_text:
                    act['text'] = new_text
                    t_obj = Task.objects.filter(text__icontains=old_name).first() if old_name else None
                    if t_obj:
                        t_obj.text = new_text
                        t_obj.save()
                        act['id'] = t_obj.id
                    else:
                        t_obj = Task.objects.create(text=new_text, completed=False)
                        act['id'] = t_obj.id
            elif act_type == 'complete_task':
                t_text = act.get('text') or act.get('task') or act.get('name')
                if t_text:
                    act['text'] = t_text
                    t_obj = Task.objects.filter(text__icontains=t_text).first()
                    if t_obj:
                        t_obj.completed = True
                        t_obj.save()
                        act['id'] = t_obj.id
            elif act_type == 'delete_task':
                t_text = act.get('text') or act.get('task') or act.get('name')
                if t_text:
                    act['text'] = t_text
                    Task.objects.filter(text__icontains=t_text).delete()

            # 2. SCHEDULE
            elif act_type == 'add_schedule':
                s_title = act.get('title') or act.get('text') or act.get('name') or act.get('event')
                if s_title:
                    act['title'] = s_title
                    time_str = parse_time_str(act.get('time', '10:00'))
                    date_val = parse_date_str(act.get('date'))
                    s_obj = ScheduleItem.objects.create(title=s_title, time=time_str, date=date_val)
                    act['id'] = s_obj.id
                    act['time'] = time_str
                    act['date'] = date_val.strftime('%Y-%m-%d')
            elif act_type == 'edit_schedule':
                title_q = act.get('title') or act.get('old') or act.get('text') or ''
                s_obj = ScheduleItem.objects.filter(title__icontains=title_q).first() if title_q else None
                if s_obj:
                    if act.get('time'):
                        s_obj.time = parse_time_str(act['time'])
                    if act.get('date'):
                        s_obj.date = parse_date_str(act['date'])
                    if act.get('new_title') or act.get('new'):
                        s_obj.title = act.get('new_title') or act.get('new')
                    s_obj.save()
                    act['id'] = s_obj.id
                    act['title'] = s_obj.title
                    act['time'] = s_obj.time
                    act['date'] = s_obj.date.strftime('%Y-%m-%d')
            elif act_type == 'delete_schedule':
                s_title = act.get('title') or act.get('text')
                if s_title:
                    act['title'] = s_title
                    ScheduleItem.objects.filter(title__icontains=s_title).delete()

            # 3. REMINDERS & CALENDAR
            elif act_type == 'add_reminder':
                r_text = act.get('text') or act.get('reminder') or act.get('message') or act.get('title')
                if r_text:
                    act['text'] = r_text
                    time_str = parse_time_str(act.get('time', '18:00'))
                    date_val = parse_date_str(act.get('date'))
                    r_obj = Reminder.objects.create(text=r_text, time=time_str, date=date_val)
                    act['id'] = r_obj.id
                    act['time'] = time_str
                    act['date'] = date_val.strftime('%Y-%m-%d')
            elif act_type == 'edit_reminder':
                text_q = act.get('text') or act.get('reminder') or ''
                r_obj = Reminder.objects.filter(text__icontains=text_q).first() if text_q else None
                if r_obj:
                    if act.get('time'):
                        r_obj.time = parse_time_str(act['time'])
                    if act.get('date'):
                        r_obj.date = parse_date_str(act['date'])
                    r_obj.save()
                    act['id'] = r_obj.id
                    act['time'] = r_obj.time
                    act['date'] = r_obj.date.strftime('%Y-%m-%d')
            elif act_type == 'complete_reminder':
                r_text = act.get('text') or act.get('reminder')
                if r_text:
                    Reminder.objects.filter(text__icontains=r_text).update(is_active=False)
            elif act_type == 'delete_reminder':
                r_text = act.get('text') or act.get('reminder')
                if r_text:
                    Reminder.objects.filter(text__icontains=r_text).delete()

            # 4. DAILY PLAN
            elif act_type == 'add_plan_item':
                p_act = act.get('activity') or act.get('text') or act.get('item')
                if p_act:
                    act['activity'] = p_act
                    time_str = parse_time_str(act.get('time', '14:00'))
                    cnt = DailyPlan.objects.count()
                    p_obj = DailyPlan.objects.create(time=time_str, activity=p_act, order=cnt+1)
                    act['id'] = p_obj.id
                    act['time'] = time_str
            elif act_type == 'edit_plan_item':
                act_q = act.get('activity') or act.get('text') or ''
                p_obj = DailyPlan.objects.filter(activity__icontains=act_q).first() if act_q else None
                if p_obj:
                    if act.get('time'):
                        p_obj.time = parse_time_str(act['time'])
                    if act.get('new_activity'):
                        p_obj.activity = act['new_activity']
                    p_obj.save()
                    act['id'] = p_obj.id
            elif act_type == 'delete_plan_item':
                act_q = act.get('activity') or act.get('text')
                if act_q:
                    DailyPlan.objects.filter(activity__icontains=act_q).delete()
            elif act_type == 'clear_plan':
                DailyPlan.objects.all().delete()
            elif act_type == 'create_plan' and act.get('items'):
                DailyPlan.objects.all().delete()
                for idx, itm in enumerate(act['items'], 1):
                    if isinstance(itm, str) and len(itm) > 5 and itm[2] == ':':
                        DailyPlan.objects.create(time=itm[:5], activity=itm[6:].strip(), order=idx)
                    else:
                        DailyPlan.objects.create(time='12:00', activity=str(itm), order=idx)

            # 5. AI PHONE SERVICE
            elif act_type == 'call_service':
                svc_setting, _ = SystemSetting.objects.get_or_create(key='phone_service_enabled')
                svc_setting.value = 'true' if act.get('on') else 'false'
                svc_setting.save()
            elif act_type == 'add_phone_message':
                c_name = act.get('caller') or 'Unknown'
                m_body = act.get('message') or 'Incoming transmission'
                t_label = act.get('time_label') or datetime.now().strftime('%H:%M')
                pm = PhoneMessage.objects.create(caller=c_name, time_label=t_label, message=m_body)
                act['id'] = pm.id
                act['caller'] = c_name
                act['message'] = m_body
                act['time_label'] = t_label
            elif act_type == 'clear_phone_messages':
                PhoneMessage.objects.all().delete()

            # 6. INTERNET ASSISTANT
            elif act_type == 'search_web':
                q_text = act.get('query') or act.get('q') or act.get('text')
                if q_text:
                    act['query'] = q_text
                    ans = act.get('answer') or f"Recon intel extracted for '{q_text}'."
                    SearchHistory.objects.create(query=q_text, category='web', result_summary=ans)
                    act['answer'] = ans
            elif act_type == 'clear_search_history':
                SearchHistory.objects.all().delete()

            # 7. AUTONOMOUS AGENT & MEMORY
            elif act_type == 'run_agent':
                goal_text = act.get('goal') or act.get('prompt') or act.get('text')
                if goal_text:
                    act['goal'] = goal_text
                    steps = act.get('steps') or ['Intel: Goal acquired', 'Recon: Scanning network', 'Ready for orders']
                    AgentTaskExecution.objects.create(goal=goal_text, status='needs_approval', steps=steps, summary=f"Mission for {goal_text}")
            elif act_type == 'approve_agent':
                last_t = AgentTaskExecution.objects.order_by('-created_at').first()
                if last_t:
                    last_t.status = 'completed'
                    last_t.save()
            elif act_type == 'add_memory':
                m_content = act.get('content') or act.get('memory') or act.get('text')
                if m_content:
                    act['content'] = m_content
                    AgentMemory.objects.create(category=act.get('category', 'tactical_intel'), content=m_content, source='gemini_nlp')
            elif act_type == 'delete_memory':
                m_content = act.get('content') or act.get('memory') or act.get('text')
                if m_content:
                    AgentMemory.objects.filter(content__icontains=m_content).delete()

        except Exception as ex:
            logger.warning(f"Error syncing action {act_type} to database: {ex}")

        synced.append(act)
    return synced


@csrf_exempt
def api_command(request):
    """
    Lightning-fast, resilient Command Handler:
    1. Instant direct regex parser for common tactical actions (0.005s latency)
    2. Cloud AI reasoning (Gemini Voice & Claude Agent) for open-ended queries
    3. Fail-safe local fallback
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    ensure_seed_data()

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'reply': 'Ghost copy. Standing by.', 'actions': []})

    clean_text = re.sub(r'^(hey\s+|ok\s+)?ghost[,.!\s]*', '', text, flags=re.IGNORECASE).strip()
    lower = clean_text.lower()
    now_dt = datetime.now()

    # --- TIER 1: INSTANT DIRECT TACTICAL ACTIONS & GHOST COD RESPONSES ---

    # Lock / Sleep: "Going dark" / "Lock grid"
    if any(q in lower for q in ['go dark', 'lock grid', 'lock down', 'lockdown', 'standby mode', 'going dark']):
        return JsonResponse({
            'reply': "Bravo Six, going dark. Tactical grid locked. Returning to security checkpoint.",
            'actions': [{'type': 'lock_grid'}]
        })

    # Security Code Word: STRICTLY ONLY "codex" unlocks Ghost
    is_client_locked = bool(data.get('is_locked'))
    is_codeword = bool(re.search(r'\bcodex\b', lower))

    # If client is locked:
    if is_client_locked:
        if is_codeword:
            return JsonResponse({
                'reply': "Code word confirmed. Security clearance granted. Welcome to Task Force 141, operator. Deploying tactical grid.",
                'actions': [{'type': 'unlock_grid'}]
            })
        else:
            return JsonResponse({
                'reply': "Negative, operator. Code word invalid. Access denied. State the security code word to gain clearance.",
                'actions': [{'type': 'access_denied'}]
            })
    elif is_codeword:
        return JsonResponse({
            'reply': "Code word confirmed. Security clearance granted. Welcome to Task Force 141, operator. Deploying tactical grid.",
            'actions': [{'type': 'unlock_grid'}]
        })

    # Build live operational context for Gemini LLM:
    context = {
        'tasks': [t.to_dict() for t in Task.objects.all()[:15]],
        'schedule': [s.to_dict() for s in ScheduleItem.objects.all()[:15]],
        'reminders': [r.to_dict() for r in Reminder.objects.filter(is_active=True)[:15]],
        'plan': [p.to_dict() for p in DailyPlan.objects.all()[:15]],
        'messages': [m.to_dict() for m in PhoneMessage.objects.all()[:10]],
        'memories': [m.to_dict() for m in AgentMemory.objects.all()[:10]],
    }

    # =========================================================================
    # TIER 1: GEMINI LLM NLP (Processes Intent for all 9 Modules or Answers Q&A)
    # =========================================================================
    try:
        gem_res = gemini_voice_reply(clean_text, context)
        if gem_res and isinstance(gem_res, dict) and gem_res.get('reply'):
            actions = gem_res.get('actions', [])
            synced_actions = sync_actions_to_database(actions)
            return JsonResponse({
                'reply': gem_res['reply'],
                'actions': synced_actions
            })
    except Exception as ex_gem:
        logger.debug(f"Gemini LLM NLP error: {ex_gem}")

    # =========================================================================
    # TIER 2: FAIL-SAFE LOCAL TACTICAL PARSER (Sub-millisecond fallback)
    # =========================================================================

    # Identity / Character check
    if any(q in lower for q in ['who are you', 'who is ghost', 'what is your name', 'identify yourself', 'your callsign', 'what is your callsign']) or lower.strip() == 'callsign':
        return JsonResponse({
            'reply': "Lieutenant Simon 'Ghost' Riley. Task Force 141. We get our hands dirty so the world stays clean. What are your orders?",
            'actions': []
        })

    if any(q in lower for q in ['bravo six', 'going dark', 'stay frosty', 'watch your six']):
        return JsonResponse({
            'reply': "Bravo Six, going dark. Stay frosty. Comms remain open.",
            'actions': []
        })

    if any(q in lower for q in ['sitrep', 'status report', 'how are you', 'status']):
        open_c = Task.objects.filter(completed=False).count()
        sched_c = ScheduleItem.objects.count()
        return JsonResponse({
            'reply': f"Sitrep: Systems 100%. {open_c} open tactical objectives, {sched_c} schedule checkpoints logged. Perimeter secure. Standing by.",
            'actions': []
        })

    if any(q in lower for q in ['thank you', 'thanks', 'good job', 'well done']):
        return JsonResponse({
            'reply': "Just doing my job. Keep your head down and stay sharp.",
            'actions': []
        })

    # --- THEME SWITCH ---
    if 'dark mode' in lower or 'theme dark' in lower or 'night vision' in lower:
        return JsonResponse({
            'reply': "Night vision optics engaged. Dark tactical HUD active.",
            'actions': [{'type': 'set_theme', 'mode': 'dark'}]
        })
    if 'light mode' in lower or 'theme light' in lower or 'daylight mode' in lower:
        return JsonResponse({
            'reply': "Daylight optics engaged. Standard light HUD active.",
            'actions': [{'type': 'set_theme', 'mode': 'light'}]
        })

    # =========================================================================
    # 1. TASKS (Add, Complete, Delete, Edit, Query)
    # =========================================================================

    # 1a. Edit Task
    m_edit_task = re.search(r'^(?:edit|update|rename|change)\s+task[:\s]+(.+?)\s+to\s+(.+)', clean_text, re.IGNORECASE)
    if m_edit_task:
        old_name = m_edit_task.group(1).strip()
        new_name = m_edit_task.group(2).strip()
        t_obj = Task.objects.filter(text__icontains=old_name).first()
        if t_obj:
            orig = t_obj.text
            t_obj.text = new_name
            t_obj.save()
            return JsonResponse({
                'reply': f"Task updated from '{orig}' to '{new_name}'. Objective revised in database.",
                'actions': [{'type': 'edit_task', 'id': t_obj.id, 'old': orig, 'text': new_name}]
            })
        else:
            t_obj = Task.objects.create(text=new_name, completed=False)
            return JsonResponse({
                'reply': f"Previous objective '{old_name}' not found. Logged new task '{new_name}'.",
                'actions': [{'type': 'add_task', 'id': t_obj.id, 'text': new_name}]
            })

    # 1b. Delete Task
    m_del_task = re.search(r'^(?:delete|remove|cancel|discard)\s+(?:task[:\s]+|the\s+)?(.+)', clean_text, re.IGNORECASE)
    if m_del_task and not re.search(r'^(?:schedule|reminder|alarm|plan|message|memory)', m_del_task.group(1), re.IGNORECASE):
        target = m_del_task.group(1).strip()
        t_obj = Task.objects.filter(text__icontains=target).first()
        if t_obj:
            t_id = t_obj.id
            txt = t_obj.text
            t_obj.delete()
            return JsonResponse({
                'reply': f"Task deleted: '{txt}'. Objective wiped from database.",
                'actions': [{'type': 'delete_task', 'id': t_id, 'text': txt}]
            })
        return JsonResponse({'reply': f"Negative. No task objective matching '{target}'.", 'actions': []})

    # 1c. Complete Task
    m_done = re.search(r'^(?:finish|complete|done with|check off|neutralize)\s+(?:task[:\s]+)?(.+)', lower)
    if m_done:
        target = m_done.group(1).strip()
        t_obj = Task.objects.filter(text__icontains=target).first()
        if t_obj:
            t_obj.completed = True
            t_obj.save()
            return JsonResponse({
                'reply': f"Objective neutralized: '{t_obj.text}'. Area is clear.",
                'actions': [{'type': 'complete_task', 'id': t_obj.id, 'text': t_obj.text}]
            })
        return JsonResponse({'reply': f"Negative. No active objective matching '{target}'. Check your coordinates.", 'actions': []})

    # 1d. Add Task
    m_task = re.search(r'^(?:add (?:a )?task|create (?:a )?task|new task|todo|task)[:\s]+(?:to\s+)?(.+)', clean_text, re.IGNORECASE)
    if not m_task:
        m_task = re.search(r'^(?:secure|infiltrate|recon|eliminate|deploy|monitor)\s+(.+)', clean_text, re.IGNORECASE)
        task_text = clean_text if m_task else None
    else:
        task_text = m_task.group(1).strip()

    if task_text:
        t_obj = Task.objects.create(text=task_text, completed=False)
        return JsonResponse({
            'reply': f"Target logged: {task_text}. Task Force 141 moving on it.",
            'actions': [{'type': 'add_task', 'id': t_obj.id, 'text': task_text}]
        })

    # =========================================================================
    # 2. SCHEDULE (Add, Edit/Reschedule, Delete, Query)
    # =========================================================================

    # 2a. Reschedule / Edit Schedule
    m_sched_edit = re.search(r'^(?:reschedule|edit schedule|update schedule|change schedule|move meeting)\s+(.+?)\s+to\s+(?:at\s+)?([0-9:]+\s*(?:am|pm)?)(?:\s+on\s+(\S+))?', clean_text, re.IGNORECASE)
    if m_sched_edit:
        title_query = m_sched_edit.group(1).strip()
        new_time = parse_time_str(m_sched_edit.group(2))
        date_str = m_sched_edit.group(3)
        item = ScheduleItem.objects.filter(title__icontains=title_query).first()
        if item:
            item.time = new_time
            if date_str:
                item.date = parse_date_str(date_str)
            item.save()
            return JsonResponse({
                'reply': f"Checkpoint rescheduled: '{item.title}' moved to {item.time} on {item.date.strftime('%b %d')}.",
                'actions': [{'type': 'edit_schedule', 'id': item.id, 'title': item.title, 'time': item.time, 'date': item.date.strftime('%Y-%m-%d')}]
            })
        return JsonResponse({'reply': f"Schedule checkpoint matching '{title_query}' not found.", 'actions': []})

    # 2b. Delete Schedule Checkpoint
    m_sched_del = re.search(r'^(?:delete|remove|cancel)\s+(?:schedule|meeting|checkpoint)[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_sched_del:
        target = m_sched_del.group(1).strip()
        item = ScheduleItem.objects.filter(title__icontains=target).first()
        if item:
            t_id = item.id
            t_title = item.title
            item.delete()
            return JsonResponse({
                'reply': f"Checkpoint removed: '{t_title}'. Mission schedule updated.",
                'actions': [{'type': 'delete_schedule', 'id': t_id, 'title': t_title}]
            })
        return JsonResponse({'reply': f"Schedule item '{target}' not found.", 'actions': []})

    # 2c. Add Schedule Checkpoint
    m_sched_add = re.search(r'^(?:schedule|book meeting with|book|add schedule|checkpoint)[:\s]+(?:for\s+|with\s+)?(.+?)(?:\s+on\s+(\S+))?(?:\s+at\s+([0-9:]+\s*(?:am|pm)?))?$', clean_text, re.IGNORECASE)
    if m_sched_add and not re.search(r'^(?:remind|alarm)', clean_text, re.IGNORECASE):
        s_title = m_sched_add.group(1).strip()
        s_date_str = m_sched_add.group(2)
        s_time = parse_time_str(m_sched_add.group(3) or '10:00')
        target_date = parse_date_str(s_date_str) if s_date_str else (timezone.localdate() if hasattr(timezone, 'localdate') else date.today())
        s_obj = ScheduleItem.objects.create(title=s_title, time=s_time, date=target_date)
        return JsonResponse({
            'reply': f"Checkpoint locked: {s_title} at {s_time} on {target_date.strftime('%b %d')}. Coordinates logged.",
            'actions': [{'type': 'add_schedule', 'id': s_obj.id, 'title': s_title, 'time': s_time, 'date': target_date.strftime('%Y-%m-%d')}]
        })

    # =========================================================================
    # 3. REMINDERS & CALENDAR (Add, Edit, Dismiss/Complete, Delete, Query)
    # =========================================================================

    # 3a. Edit Reminder
    m_rem_edit = re.search(r'^(?:edit|update|change)\s+reminder[:\s]+(.+?)\s+to\s+(.+)', clean_text, re.IGNORECASE)
    if m_rem_edit:
        old_query = m_rem_edit.group(1).strip()
        new_part = m_rem_edit.group(2).strip()
        rem = Reminder.objects.filter(text__icontains=old_query).first()
        if rem:
            m_time = re.search(r'(?:at\s+)?([0-9:]+\s*(?:am|pm)?)', new_part, re.IGNORECASE)
            if m_time and len(new_part.replace(m_time.group(0), '').strip()) == 0:
                rem.time = parse_time_str(m_time.group(1))
            else:
                rem.text = new_part
            rem.save()
            return JsonResponse({
                'reply': f"Reminder updated: '{rem.text}' set for {rem.time}.",
                'actions': [{'type': 'edit_reminder', 'id': rem.id, 'text': rem.text, 'time': rem.time, 'date': rem.date.strftime('%Y-%m-%d')}]
            })
        return JsonResponse({'reply': f"Reminder matching '{old_query}' not found.", 'actions': []})

    # 3b. Complete / Dismiss Reminder
    m_rem_dismiss = re.search(r'^(?:dismiss|complete|turn off|stop)\s+reminder[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_rem_dismiss:
        target = m_rem_dismiss.group(1).strip()
        rem = Reminder.objects.filter(text__icontains=target, is_active=True).first()
        if rem:
            rem.is_active = False
            rem.save()
            return JsonResponse({
                'reply': f"Reminder dismissed: '{rem.text}'. Alert timer deactivated.",
                'actions': [{'type': 'complete_reminder', 'id': rem.id, 'text': rem.text}]
            })
        return JsonResponse({'reply': f"Active reminder matching '{target}' not found.", 'actions': []})

    # 3c. Delete Reminder
    m_rem_del = re.search(r'^(?:delete|remove|cancel)\s+reminder[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_rem_del:
        target = m_rem_del.group(1).strip()
        rem = Reminder.objects.filter(text__icontains=target).first()
        if rem:
            rem_id = rem.id
            rem_txt = rem.text
            rem.delete()
            return JsonResponse({
                'reply': f"Reminder deleted: '{rem_txt}'. Removed from alert grid.",
                'actions': [{'type': 'delete_reminder', 'id': rem_id, 'text': rem_txt}]
            })
        return JsonResponse({'reply': f"Reminder matching '{target}' not found.", 'actions': []})

    # 3d. Add Reminder (with Direct Calendar Date Support)
    m_rem = re.search(r'^(?:remind me|set reminder|calendar add reminder|add reminder|alarm)[:\s]+(?:on\s+(\S+)\s+)?(?:to\s+|for\s+)?(.+?)(?:\s+at\s+([0-9:]+\s*(?:am|pm)?))?$', clean_text, re.IGNORECASE)
    if m_rem:
        d_cand = m_rem.group(1)
        rem_text = (m_rem.group(2) or '').strip()
        rem_time = parse_time_str(m_rem.group(3) or '18:00')
        target_date = parse_date_str(d_cand) if d_cand else (timezone.localdate() if hasattr(timezone, 'localdate') else date.today())
        if rem_text:
            r_obj = Reminder.objects.create(text=rem_text, time=rem_time, date=target_date)
            return JsonResponse({
                'reply': f"Solid copy. Alert armed for '{rem_text}' at {rem_time} on {target_date.strftime('%b %d')}. Watch your six.",
                'actions': [{'type': 'add_reminder', 'id': r_obj.id, 'text': rem_text, 'time': rem_time, 'date': target_date.strftime('%Y-%m-%d')}]
            })

    # =========================================================================
    # 4. DAILY PLAN (Add, Edit, Delete, Clear, Auto-Plan, Query)
    # =========================================================================

    # 4a. Clear Plan
    if any(k in lower for k in ['clear plan', 'clear daily plan', 'reset plan', 'delete all plan', 'wipe plan']):
        DailyPlan.objects.all().delete()
        return JsonResponse({
            'reply': "Daily plan wiped from database. Deck is clear for new directives.",
            'actions': [{'type': 'clear_plan'}]
        })

    # 4b. Delete Plan Item
    m_plan_del = re.search(r'^(?:delete|remove)\s+(?:from\s+)?plan[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_plan_del:
        target = m_plan_del.group(1).strip()
        p_obj = DailyPlan.objects.filter(activity__icontains=target).first()
        if p_obj:
            p_id = p_obj.id
            act = p_obj.activity
            p_obj.delete()
            return JsonResponse({
                'reply': f"Plan objective removed: '{act}'. Schedule adjusted.",
                'actions': [{'type': 'delete_plan_item', 'id': p_id, 'activity': act}]
            })
        return JsonResponse({'reply': f"Plan item matching '{target}' not found.", 'actions': []})

    # 4c. Edit Plan Item
    m_plan_edit = re.search(r'^(?:edit|update|change)\s+plan[:\s]+(.+?)\s+to\s+(.+)', clean_text, re.IGNORECASE)
    if m_plan_edit:
        old_act = m_plan_edit.group(1).strip()
        new_val = m_plan_edit.group(2).strip()
        p_obj = DailyPlan.objects.filter(activity__icontains=old_act).first()
        if p_obj:
            m_t = re.search(r'([0-9:]+\s*(?:am|pm)?)\s+(.+)', new_val, re.IGNORECASE)
            if m_t:
                p_obj.time = parse_time_str(m_t.group(1))
                p_obj.activity = m_t.group(2).strip()
            else:
                p_obj.activity = new_val
            p_obj.save()
            return JsonResponse({
                'reply': f"Plan item updated: {p_obj.time} - {p_obj.activity}.",
                'actions': [{'type': 'edit_plan_item', 'id': p_obj.id, 'time': p_obj.time, 'activity': p_obj.activity}]
            })
        return JsonResponse({'reply': f"Plan item '{old_act}' not found.", 'actions': []})

    # 4d. Add to Plan
    m_p_add = re.search(r'^(?:add to daily plan|daily plan add|add to plan|add plan item|add plan|plan item)[:\s]+(?:([0-9:]+)\s+)?(.+)', clean_text, re.IGNORECASE)
    if m_p_add:
        p_time = parse_time_str(m_p_add.group(1) or '14:00')
        p_act = m_p_add.group(2).strip()
        cnt = DailyPlan.objects.count()
        p_obj = DailyPlan.objects.create(time=p_time, activity=p_act, order=cnt+1)
        return JsonResponse({
            'reply': f"Plan updated: {p_time} - {p_act}. In the crosshairs.",
            'actions': [{'type': 'add_plan_item', 'id': p_obj.id, 'time': p_time, 'activity': p_act, 'text': f"{p_time} {p_act}"}]
        })

    # 4e. Plan My Day / Auto Plan
    if 'plan' in lower and ('day' in lower or 'create' in lower or 'my' in lower or 'auto' in lower):
        if not DailyPlan.objects.exists():
            default_items = [
                ('09:00', 'Mission brief & email sweep', 1),
                ('10:30', 'Tactical deep work session', 2),
                ('13:00', 'Ration break & quick recon', 3),
                ('15:00', 'Client checkpoint call', 4),
                ('18:00', 'Perimeter security inspection', 5),
            ]
            for t, act, ord_idx in default_items:
                DailyPlan.objects.create(time=t, activity=act, order=ord_idx)
        plans = [p.to_dict()['text'] for p in DailyPlan.objects.all()]
        return JsonResponse({
            'reply': "Daily plan deployed from database. Keep your head down and execute.",
            'actions': [{'type': 'create_plan', 'items': plans}]
        })

    # =========================================================================
    # 5. AI PHONE SERVICE (Clear, Simulate, Delete, Toggle, Query)
    # =========================================================================

    # 5a. Clear Voicemails / Messages
    if any(k in lower for k in ['clear messages', 'delete all messages', 'clear voicemails', 'clear inbox', 'purge comms', 'wipe messages']):
        PhoneMessage.objects.all().delete()
        return JsonResponse({
            'reply': "Comms inbox cleared. All voicemail intercepts deleted.",
            'actions': [{'type': 'clear_phone_messages'}]
        })

    # 5b. Simulate Call / Add Message
    m_sim_call = re.search(r'^(?:simulate call|fake call|add message|new voicemail)[:\s]+(?:from\s+(.+?))?(?:\s+saying\s+(.+))?$', clean_text, re.IGNORECASE)
    if m_sim_call:
        c_name = (m_sim_call.group(1) or 'Captain Price').strip()
        msg_body = (m_sim_call.group(2) or 'Mission green light. Bravo Six standing by.').strip()
        time_label = datetime.now().strftime('%H:%M')
        pm = PhoneMessage.objects.create(caller=c_name, time_label=time_label, message=msg_body)
        return JsonResponse({
            'reply': f"Voicemail logged from {c_name}: '{msg_body}'. Intel filed in inbox.",
            'actions': [{'type': 'add_phone_message', 'id': pm.id, 'caller': c_name, 'message': msg_body, 'time_label': time_label}]
        })

    # 5c. Toggle Phone Service On/Off
    if any(k in lower for k in ['turn on phone service', 'enable phone service', 'enable call service', 'start phone service', 'arm phone service']):
        setting, _ = SystemSetting.objects.get_or_create(key='phone_service_enabled')
        setting.value = 'true'
        setting.save()
        return JsonResponse({
            'reply': "AI phone service is armed. Answering incoming calls and logging intel.",
            'actions': [{'type': 'call_service', 'on': True}]
        })
    if any(k in lower for k in ['turn off phone service', 'disable phone service', 'pause phone service', 'stop call service', 'disarm phone service']):
        setting, _ = SystemSetting.objects.get_or_create(key='phone_service_enabled')
        setting.value = 'false'
        setting.save()
        return JsonResponse({
            'reply': "AI phone service disarmed. Calls routed to standard voicemail.",
            'actions': [{'type': 'call_service', 'on': False}]
        })

    # =========================================================================
    # 6. INTERNET ASSISTANT (Search, Clear History)
    # =========================================================================

    # 6a. Clear Search History
    if any(k in lower for k in ['clear search history', 'delete recon logs', 'clear recon logs', 'clear web history', 'wipe search']):
        SearchHistory.objects.all().delete()
        return JsonResponse({
            'reply': "Recon search logs purged from mission database.",
            'actions': [{'type': 'clear_search_history'}]
        })

    # 6b. Search Web / Intel
    m_search = re.search(r'^(?:search(?: web)?|google|lookup|find info on|find intel on|research|ask intel|recon)[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_search:
        query = m_search.group(1).strip()
        ans = f"Recon telemetry for '{query}': Intel logged to mission database."
        SearchHistory.objects.create(query=query, category='web', result_summary=ans)
        return JsonResponse({
            'reply': f"Recon initiated for '{query}'. Extracting intel.",
            'actions': [{'type': 'search_web', 'query': query, 'answer': ans}]
        })

    # =========================================================================
    # 7. AUTONOMOUS AGENT & MEMORY (Approve, Run, Remember, Forget, Query)
    # =========================================================================

    # 7a. Approve Agent Directive
    if any(k in lower for k in ['approve agent', 'authorize agent', 'confirm mission', 'approve directive', 'authorize directive']):
        last_task = AgentTaskExecution.objects.order_by('-created_at').first()
        if last_task:
            last_task.status = 'completed'
            last_task.save()
        return JsonResponse({
            'reply': "Agent directive authorized. Task Force 141 mission execution underway.",
            'actions': [{'type': 'approve_agent'}]
        })

    # 7b. Run Autonomous Agent
    m_agent_trig = re.search(r'^(?:run agent|launch agent|start agent|assign mission)[:\s]*(.*)', clean_text, re.IGNORECASE)
    if m_agent_trig:
        agent_g = m_agent_trig.group(1).strip() or "Find 5 remote Python jobs and summarize"
        steps = [
            f'Intel: Target goal locked - {agent_g}',
            'Recon: Accessing Task Force 141 archives',
            'Extraction: Generating mission deliverables',
            'Standing by for operator authorization'
        ]
        AgentTaskExecution.objects.create(goal=agent_g, status='needs_approval', steps=steps, summary=f"Mission planned for {agent_g}")
        return JsonResponse({
            'reply': f"Recon directive assigned to Claude agent: '{agent_g}'. Coordinates locked.",
            'actions': [{'type': 'run_agent', 'goal': agent_g, 'steps': steps}]
        })

    # 7c. Forget / Delete Memory
    m_forget = re.search(r'^(?:forget that|forget|delete memory|remove memory)[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_forget:
        target = m_forget.group(1).strip()
        cnt, _ = AgentMemory.objects.filter(content__icontains=target).delete()
        return JsonResponse({
            'reply': f"Tactical intel '{target}' purged from memory vault. {cnt} record(s) wiped.",
            'actions': [{'type': 'delete_memory', 'content': target}]
        })

    # 7d. Query Memories
    if any(k in lower for k in ['what do you remember', 'show memories', 'intel vault', 'list memories', 'recall intel']):
        mems = list(AgentMemory.objects.all().values_list('content', flat=True)[:4])
        reply = f"Intel Vault records: {'; '.join(mems)}." if mems else "Intel vault is clean. No active memories logged."
        return JsonResponse({'reply': reply, 'actions': []})

    # 7e. Remember Intel
    m_mem = re.search(r'^(?:remember that|remember to remember|remember|log memory|save intel|store note)[:\s]+(.+)', clean_text, re.IGNORECASE)
    if m_mem and 'remind' not in lower:
        mem_fact = m_mem.group(1).strip()
        AgentMemory.objects.create(category='tactical_intel', content=mem_fact, source='voice_agent')
        return JsonResponse({
            'reply': f"Tactical intel committed to memory vault: '{mem_fact}'. Won't be forgotten.",
            'actions': [{'type': 'add_memory', 'content': mem_fact, 'category': 'tactical_intel'}]
        })

    # =========================================================================
    # 8. GENERAL STATUS QUERIES & COMMS
    # =========================================================================

    # 8a. Tasks Query
    if any(k in lower for k in ['what are my tasks', 'show tasks', 'list tasks', 'open tasks', 'my tasks', 'tasks']):
        open_tasks = list(Task.objects.filter(completed=False).values_list('text', flat=True))
        reply = f"Sitrep: You've got {len(open_tasks)} active targets: {', '.join(open_tasks[:4])}." if open_tasks else "All objectives clear. Area is secure."
        return JsonResponse({'reply': reply, 'actions': []})

    # 8b. Schedule / Meetings Query
    if any(k in lower for k in ['what is on my schedule', 'next meeting', 'what meetings do i have', 'schedule', 'op schedule', 'calendar']):
        items = list(ScheduleItem.objects.all())
        rems = list(Reminder.objects.filter(is_active=True))
        reply = f"Op schedule: Next checkpoint is {items[0].title} at {items[0].time} ({len(items)} events, {len(rems)} reminders logged). Stay sharp." if items else f"Calendar clear. {len(rems)} active reminders armed."
        return JsonResponse({'reply': reply, 'actions': []})

    # 8c. Messages Query
    if any(k in lower for k in ['who called', 'missed calls', 'any messages', 'any calls', 'voicemails', 'messages']):
        msgs = list(PhoneMessage.objects.all()[:3])
        reply = f"Comms intercept: {len(msgs)} messages on wire: {', '.join([f'{m.caller} ({m.time_label})' for m in msgs])}." if msgs else "Comms quiet. No missed calls."
        return JsonResponse({'reply': reply, 'actions': []})

    # 8d. Tamil Comms
    if any(w in lower for w in ['வணக்கம்', 'காலை வணக்கம்', 'வணக்கமுங்க']):
        return JsonResponse({'reply': 'வணக்கம். லெப்டினன்ட் கோஸ்ட் தயார் நிலையில் உள்ளேன். என்ன உத்தரவு?', 'actions': []})
    if 'வேலை' in lower or 'டாஸ்க்' in lower:
        open_tasks = list(Task.objects.filter(completed=False).values_list('text', flat=True))
        reply = f"செயலில் உள்ள பணிகள்: {', '.join(open_tasks[:3])}. கண்காணிப்பில் உள்ளேன்." if open_tasks else "எல்லா பணிகளும் முடிந்தது. புதிய உத்தரவுக்காக காத்திருக்கிறேன்."
        return JsonResponse({'reply': reply, 'actions': []})

    return JsonResponse({
        'reply': f"Ghost copy on '{clean_text}'. Standing by for task orders. Eyes open.",
        'actions': []
    })

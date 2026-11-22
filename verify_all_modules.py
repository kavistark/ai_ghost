import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:8000'

def req(path, method='GET', data=None):
    url = BASE + path
    headers = {'Content-Type': 'application/json'}
    body = json.dumps(data).encode('utf-8') if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=20) as res:
        raw = res.read().decode('utf-8')
        if 'api/' in path:
            return res.status, json.loads(raw)
        return res.status, raw

print("\n" + "="*70)
print("     TASK FORCE 141 - VERIFICATION OF ALL 9 MODULES + GEMINI NLP")
print("="*70)

tests = []

# 1. Check UI HTML does not contain "Hands-Free: ON" button or "Django Admin"
try:
    st, html = req('/')
    has_hf = 'Hands-Free: ON' in html
    has_admin = 'Django Admin' in html
    tests.append(('UI Header: Hands-Free button removed', not has_hf, f'Present: {has_hf}'))
    tests.append(('UI Header: Django Admin link removed', not has_admin, f'Present: {has_admin}'))
except Exception as e:
    tests.append(('UI Header Check', False, str(e)))

# 2. General Q&A (Gemini LLM in Ghost Character Persona)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Ghost, what is quantum computing?'})
    reply = res.get('reply', '')
    actions = res.get('actions', [])
    tests.append(('Gemini Q&A: In-character response', bool(reply) and len(reply) > 10, reply[:60] + '...'))
    tests.append(('Gemini Q&A: Empty actions array for Q&A', actions == [], f'Actions: {len(actions)}'))
except Exception as e:
    tests.append(('Gemini Q&A Test', False, str(e)))

# 3. Tasks Module (Add task via NLP)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Ghost add task Secure the satellite uplink'})
    reply = res.get('reply', '')
    actions = res.get('actions', [])
    has_task_act = any(a.get('type') == 'add_task' for a in actions)
    tests.append(('Module 1 Tasks: Add task via NLP', has_task_act, f'Reply: {reply[:50]}...'))
except Exception as e:
    tests.append(('Module 1 Tasks', False, str(e)))

# 4. Schedule Module (Add schedule via NLP)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Schedule team briefing tomorrow at 10:00 am'})
    reply = res.get('reply', '')
    actions = res.get('actions', [])
    has_sch_act = any(a.get('type') == 'add_schedule' for a in actions)
    tests.append(('Module 2 Schedule: Add schedule via NLP', has_sch_act, f'Reply: {reply[:50]}...'))
except Exception as e:
    tests.append(('Module 2 Schedule', False, str(e)))

# 5. Reminders & Calendar (Add date reminder via NLP)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Remind me on 2026-12-05 at 15:00 to calibrate tactical drone'})
    reply = res.get('reply', '')
    actions = res.get('actions', [])
    has_rem_act = any(a.get('type') == 'add_reminder' for a in actions)
    tests.append(('Module 3 Reminders & Calendar: Add reminder with date', has_rem_act, f'Reply: {reply[:50]}...'))
except Exception as e:
    tests.append(('Module 3 Reminders & Calendar', False, str(e)))

# 6. Daily Plan Module
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Add to daily plan 16:00 Perimeter sweep'})
    actions = res.get('actions', [])
    has_plan_act = any(a.get('type') == 'add_plan_item' for a in actions)
    tests.append(('Module 4 Daily Plan: Add plan item', has_plan_act, f'Actions: {actions}'))
except Exception as e:
    tests.append(('Module 4 Daily Plan', False, str(e)))

# 7. Ghost Core (Lock / Theme)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Bravo Six, go dark'})
    actions = res.get('actions', [])
    has_lock_act = any(a.get('type') == 'lock_grid' for a in actions)
    tests.append(('Module 5 Ghost Core: Tactical lock', has_lock_act, res.get('reply', '')))
except Exception as e:
    tests.append(('Module 5 Ghost Core', False, str(e)))

# 8. Internet Assistant (Search)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Search web for stealth drone coordinates'})
    actions = res.get('actions', [])
    has_search_act = any(a.get('type') == 'search_web' for a in actions)
    tests.append(('Module 6 Internet Assistant: Search query', has_search_act, res.get('reply', '')[:50]))
except Exception as e:
    tests.append(('Module 6 Internet Assistant', False, str(e)))

# 9. AI Phone Service (Toggle service)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Turn on AI phone service'})
    actions = res.get('actions', [])
    has_phone_act = any(a.get('type') == 'call_service' for a in actions)
    tests.append(('Module 7 AI Phone Service: Call service switch', has_phone_act, res.get('reply', '')[:50]))
except Exception as e:
    tests.append(('Module 7 AI Phone Service', False, str(e)))

# 10. Autonomous Agent & Memory (Remember memory)
try:
    st, res = req('/api/command/', method='POST', data={'text': 'Remember that extraction point is sector 4'})
    actions = res.get('actions', [])
    has_mem_act = any(a.get('type') == 'add_memory' for a in actions)
    tests.append(('Module 8 Autonomous Agent: Log tactical memory', has_mem_act, res.get('reply', '')[:50]))
except Exception as e:
    tests.append(('Module 8 Autonomous Agent', False, str(e)))

print()
all_passed = True
for name, passed, detail in tests:
    status = '[PASS]' if passed else '[FAIL]'
    if not passed:
        all_passed = False
    print(f" {status} {name:<46} : {detail}")

print("="*70)
print(" RESULT: " + ("ALL VERIFICATIONS PASSED" if all_passed else "SOME VERIFICATIONS FAILED"))
print("="*70 + "\n")

sys.exit(0 if all_passed else 1)


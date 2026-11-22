import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:8000'
results = []

def req(path, method='GET', data=None):
    url = BASE + path
    headers = {'Content-Type': 'application/json'}
    body = json.dumps(data).encode('utf-8') if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r) as res:
        raw = res.read().decode('utf-8')
        if 'api/' in path:
            return res.status, json.loads(raw)
        return res.status, raw

print("\n" + "="*65)
print("       GHOST AI VOICE ASSISTANT - LIVE TEST SUITE")
print("="*65)

def run_live_tests():
    try:
        # 1. Dashboard
        st, _ = req('/')
        results.append(('Dashboard UI (GET /)', st == 200, f'Status {st} OK'))

        # 2. Tasks API
        st, d = req('/api/tasks/')
        results.append(('Tasks API (GET /api/tasks/)', st == 200 and d.get('status') == 'ok', f'{len(d.get("tasks", []))} tasks active'))

        # 3. Add Task
        st, d = req('/api/tasks/', method='POST', data={'action': 'add', 'text': 'Live Test Verification Task'})
        task_id = d.get('task', {}).get('id')
        results.append(('Add Task (POST /api/tasks/)', st == 200 and bool(task_id), f'Created task ID #{task_id}'))

        # 4. Toggle Task
        st, d = req('/api/tasks/', method='POST', data={'action': 'toggle', 'id': task_id, 'completed': True})
        results.append(('Toggle Task (POST /api/tasks/)', st == 200 and d.get('task', {}).get('completed') is True, 'Marked as completed'))

        # 5. Reminders API
        st, d = req('/api/reminders/', method='POST', data={'text': 'Test medicine reminder', 'time': '20:30'})
        results.append(('Add Reminder (POST /api/reminders/)', st == 200 and 'reminder' in d, f'Reminder set at {d.get("reminder", {}).get("time")}'))

        # 6. Schedule API
        st, d = req('/api/schedule/', method='POST', data={'title': 'Live Client Sync', 'time': '16:00'})
        results.append(('Schedule Booking (POST /api/schedule/)', st == 200 and 'schedule_item' in d, 'Meeting booked on calendar'))

        # 7. Simulate Phone Call
        st, d = req('/api/messages/', method='POST', data={'caller': 'Anand (CEO)', 'message': 'Deployment verified, looks great!'})
        results.append(('Phone Message Simulator (POST /api/messages/)', st == 200 and 'message_item' in d, 'Voicemail logged to inbox'))

        # 8. Command NLP & Memory Recording
        st, d = req('/api/command/', method='POST', data={'text': 'remember that Anand is CEO and prefers evening meetings'})
        results.append(('Agent Memory Voice Command (POST /api/command/)', st == 200 and 'reply' in d, d.get('reply')))

        # 9. Voice Command Status Query
        st, d = req('/api/command/', method='POST', data={'text': 'what are my tasks'})
        reply_txt = d.get('reply', '').lower()
        results.append(('Voice Status Query (POST /api/command/)', st == 200 and any(w in reply_txt for w in ['target', 'task', 'objective']), d.get('reply')))

        # 10. Claude Autonomous Agent Execution
        st, d = req('/api/agent/run/', method='POST', data={'goal': 'Find 3 remote senior Python roles in Bengaluru'})
        steps_count = len(d.get('execution', {}).get('steps', []))
        results.append(('Claude Agent Runner (POST /api/agent/run/)', st == 200 and 'execution' in d, f'{steps_count} execution steps generated'))

        # 11. Retrieve Agent Memories
        st, d = req('/api/agent/memories/')
        m_count = len(d.get('memories', []))
        results.append(('Agent Memories Vault (GET /api/agent/memories/)', st == 200 and m_count > 0, f'{m_count} memories securely stored'))

        # 12. Calendar Date Reminder Integration
        st, d = req('/api/reminders/', method='POST', data={'text': 'Perimeter patrol checkpoint', 'time': '11:15', 'date': '2026-12-05'})
        results.append(('Calendar Date Reminder (POST /api/reminders/)', st == 200 and d.get('reminder', {}).get('date') == '2026-12-05', 'Saved to 2026-12-05 in SQLite'))

        # 13. Daily Plan API
        st, d = req('/api/plan/', method='POST', data={'action': 'add', 'time': '16:30', 'activity': 'Weapons calibration'})
        results.append(('Daily Plan API (POST /api/plan/)', st == 200 and 'item' in d, 'Plan item appended to database'))

        # 14. Recon Search API
        st, d = req('/api/search/', method='POST', data={'query': 'FastAPI vs Django async', 'category': 'tech'})
        results.append(('Recon Search API (POST /api/search/)', st == 200 and 'record' in d, 'Search telemetry saved to SQLite'))

        # 15. System Settings API
        st, d = req('/api/settings/')
        results.append(('System Settings API (GET /api/settings/)', st == 200 and 'settings' in d, 'Settings loaded from database'))

        all_pass = True
        for name, passed, detail in results:
            mark = '[PASS]' if passed else '[FAIL]'
            if not passed:
                all_pass = False
            print(f" {mark} {name:<45} : {detail}")

        print("="*65)
        print(" SUMMARY: " + (f"ALL {len(results)} TESTS PASSED SUCCESSFULLY (100% OK)" if all_pass else "SOME TESTS FAILED"))
        print("="*65 + "\n")

        sys.exit(0 if all_pass else 1)

    except Exception as e:
        print(f"Test error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_live_tests()

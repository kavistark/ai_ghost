import json
from unittest.mock import patch
from django.test import TestCase, Client
from .models import Task, ScheduleItem, Reminder, PhoneMessage, DailyPlan, AgentMemory, AgentTaskExecution

class GhostAssistantTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GHOST')
        self.assertContains(response, 'Ghost core')

    def test_api_tasks_crud(self):
        # 1. GET tasks
        res = self.client.get('/api/tasks/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')

        # 2. Add task
        res_post = self.client.post(
            '/api/tasks/',
            data=json.dumps({'action': 'add', 'text': 'Build Django backend'}),
            content_type='application/json'
        )
        self.assertEqual(res_post.status_code, 200)
        task_data = res_post.json()['task']
        self.assertEqual(task_data['text'], 'Build Django backend')
        self.assertIn('id', task_data)

        # 3. Toggle task
        res_toggle = self.client.post(
            '/api/tasks/',
            data=json.dumps({'action': 'toggle', 'id': task_data['id'], 'completed': True}),
            content_type='application/json'
        )
        self.assertEqual(res_toggle.status_code, 200)
        self.assertTrue(res_toggle.json()['task']['completed'])

        # 4. Delete task
        res_del = self.client.post(
            '/api/tasks/',
            data=json.dumps({'action': 'delete', 'id': task_data['id']}),
            content_type='application/json'
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(Task.objects.filter(id=task_data['id']).exists())

    @patch('assistant.views.claude_execute_agent_task', return_value={
        'steps': ['Step 1: Analyzed', 'Step 2: Scanned', 'Waiting for approval'],
        'status': 'needs_approval',
        'summary': 'Scanned 12 positions',
        'new_memories': [{'category': 'preference', 'content': 'Bengaluru location focus'}],
        'actions': []
    })
    def test_agent_and_memory_apis(self, mock_claude):
        # 1. Test Memory API
        res_mem = self.client.post(
            '/api/agent/memories/',
            data=json.dumps({'category': 'preference', 'content': 'User prefers dark mode'}),
            content_type='application/json'
        )
        self.assertEqual(res_mem.status_code, 200)
        self.assertTrue(AgentMemory.objects.filter(content__icontains='dark mode').exists())

        # 2. Test Agent Run API
        res_agent = self.client.post(
            '/api/agent/run/',
            data=json.dumps({'goal': 'Scan AI developer positions in Bengaluru'}),
            content_type='application/json'
        )
        self.assertEqual(res_agent.status_code, 200)
        data = res_agent.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('execution', data)
        self.assertTrue(AgentTaskExecution.objects.filter(goal__icontains='Bengaluru').exists())

    @patch('assistant.views.gemini_voice_reply', return_value=None)
    @patch('assistant.views.claude_execute_agent_task', return_value=None)
    def test_local_nlp_commands(self, mock_claude, mock_gemini):
        # Add task via voice command
        res = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'Ghost add task Deploy to production'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('reply', data)
        self.assertTrue(Task.objects.filter(text='Deploy to production').exists())

        # Complete task via voice command
        res_done = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'done with Deploy to production'}),
            content_type='application/json'
        )
        self.assertEqual(res_done.status_code, 200)
        self.assertTrue(Task.objects.get(text='Deploy to production').completed)

        # Add reminder via voice command
        res_rem = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'remind me to call client at 4:30 pm'}),
            content_type='application/json'
        )
        self.assertEqual(res_rem.status_code, 200)
        self.assertTrue(Reminder.objects.filter(text__icontains='call client').exists())

        # Remember memory command
        res_mem = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'remember that my doctor is Dr. Priya'}),
            content_type='application/json'
        )
        self.assertEqual(res_mem.status_code, 200)
        self.assertTrue(AgentMemory.objects.filter(content__icontains='Dr. Priya').exists())

        # Query tasks status
        res_tasks = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'what are my tasks'}),
            content_type='application/json'
        )
        self.assertEqual(res_tasks.status_code, 200)
        reply_lower = res_tasks.json()['reply'].lower()
        self.assertTrue('targets' in reply_lower or 'objectives' in reply_lower or 'tasks' in reply_lower)

        # Query meetings status
        res_sched = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'what is on my schedule'}),
            content_type='application/json'
        )
        self.assertEqual(res_sched.status_code, 200)
        self.assertIn('stand-up', res_sched.json()['reply'].lower())

    def test_calendar_reminders_and_schedule(self):
        # 1. Add Reminder with specific date
        res_rem = self.client.post(
            '/api/reminders/',
            data=json.dumps({'text': 'Infiltrate warehouse', 'time': '14:30', 'date': '2026-12-01'}),
            content_type='application/json'
        )
        self.assertEqual(res_rem.status_code, 200)
        r_data = res_rem.json()['reminder']
        self.assertEqual(r_data['text'], 'Infiltrate warehouse')
        self.assertEqual(r_data['date'], '2026-12-01')
        self.assertTrue(Reminder.objects.filter(text='Infiltrate warehouse', date='2026-12-01').exists())

        # 2. Add Schedule item with specific date
        res_sch = self.client.post(
            '/api/schedule/',
            data=json.dumps({'title': 'Briefing with Captain Price', 'time': '16:00', 'date': '2026-12-01'}),
            content_type='application/json'
        )
        self.assertEqual(res_sch.status_code, 200)
        s_data = res_sch.json()['schedule_item']
        self.assertEqual(s_data['title'], 'Briefing with Captain Price')
        self.assertEqual(s_data['date'], '2026-12-01')

    def test_daily_plan_and_search_and_settings(self):
        # 1. Add Daily Plan Item
        res_plan = self.client.post(
            '/api/plan/',
            data=json.dumps({'action': 'add', 'time': '15:30', 'activity': 'Perimeter sweep'}),
            content_type='application/json'
        )
        self.assertEqual(res_plan.status_code, 200)
        self.assertTrue(DailyPlan.objects.filter(activity='Perimeter sweep').exists())

        # 2. Search History API
        res_search = self.client.post(
            '/api/search/',
            data=json.dumps({'query': 'Python AI frameworks', 'category': 'tech'}),
            content_type='application/json'
        )
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(res_search.json()['status'], 'ok')

        # 3. Phone Service toggle
        res_msg = self.client.post(
            '/api/messages/',
            data=json.dumps({'action': 'toggle_service', 'enabled': False}),
            content_type='application/json'
        )
        self.assertEqual(res_msg.status_code, 200)
        self.assertFalse(res_msg.json()['service_enabled'])

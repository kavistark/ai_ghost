import json
from django.test import TestCase, Client
from .models import Task, ScheduleItem, Reminder, PhoneMessage, DailyPlan

class GhostAssistantTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GHOST')
        self.assertContains(response, 'Ghost core')

    def test_api_tasks_get_and_post(self):
        # GET tasks
        res = self.client.get('/api/tasks/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')

        # Add task
        res_post = self.client.post(
            '/api/tasks/',
            data=json.dumps({'action': 'add', 'text': 'Build Django backend'}),
            content_type='application/json'
        )
        self.assertEqual(res_post.status_code, 200)
        task_data = res_post.json()['task']
        self.assertEqual(task_data['text'], 'Build Django backend')

        # Toggle task
        res_toggle = self.client.post(
            '/api/tasks/',
            data=json.dumps({'action': 'toggle', 'id': task_data['id'], 'completed': True}),
            content_type='application/json'
        )
        self.assertEqual(res_toggle.status_code, 200)
        self.assertTrue(res_toggle.json()['task']['completed'])

    def test_api_command_nlp(self):
        # Test adding task via voice command
        res = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'Ghost add task Deploy to production'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('reply', data)
        self.assertTrue(Task.objects.filter(text='Deploy to production').exists())

        # Test reminder via voice command
        res2 = self.client.post(
            '/api/command/',
            data=json.dumps({'text': 'remind me to call client at 4:30 pm'}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(Reminder.objects.filter(text__icontains='call client').exists())

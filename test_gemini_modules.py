import os
import sys
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghost_core.settings')
django.setup()

from django.test import RequestFactory
from assistant.views import api_command

rf = RequestFactory()

test_commands = [
    ('Schedule', 'schedule team briefing tomorrow at 15:00'),
    ('Tasks', 'add task scout enemy perimeter'),
    ('Reminders', 'remind me to check satellite uplink at 17:30'),
    ('Daily Plan', 'add plan 16:00 tactical debriefing'),
    ('Internet Assistant', 'search web for latest UAV reconnaissance specs'),
    ('AI Phone Service', 'turn on AI phone service'),
    ('Autonomous Agent', 'autonomous agent recon forward operating base'),
    ('General Q&A', 'what is the time now')
]

print("=== TESTING ALL 7 MODULES + Q&A THROUGH GEMINI NLP ===")
for mod, cmd in test_commands:
    req = rf.post('/api/command/', data=json.dumps({'text': cmd, 'is_locked': False}), content_type='application/json')
    resp = api_command(req)
    res_data = json.loads(resp.content.decode('utf-8'))
    print(f"[{mod}] Input: {cmd}")
    print(f"  Ghost Spoken Reply: {res_data.get('reply')}")
    print(f"  Actions synced to DB: {res_data.get('actions')}")
    print("-" * 55)


from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/tasks/', views.api_tasks, name='api_tasks'),
    path('api/reminders/', views.api_reminders, name='api_reminders'),
    path('api/schedule/', views.api_schedule, name='api_schedule'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/phone/call/start/', views.api_phone_call_start, name='api_phone_call_start'),
    path('api/phone/call/talk/', views.api_phone_call_talk, name='api_phone_call_talk'),
    path('api/phone/call/end/', views.api_phone_call_end, name='api_phone_call_end'),
    path('api/phone/sms/', views.api_phone_sms, name='api_phone_sms'),
    path('api/phone/webhook/', views.api_phone_webhook, name='api_phone_webhook'),
    path('api/phone/webhook/gather/', views.api_phone_webhook_gather, name='api_phone_webhook_gather'),
    path('api/plan/', views.api_plan, name='api_plan'),
    path('api/command/', views.api_command, name='api_command'),
    path('api/agent/run/', views.api_agent_run, name='api_agent_run'),
    path('api/agent/memories/', views.api_memories, name='api_memories'),
    path('api/camera/stream/', views.api_camera_stream, name='api_camera_stream'),
    path('api/camera/analyze/', views.api_camera_analyze, name='api_camera_analyze'),
    path('api/camera/logs/', views.api_camera_logs, name='api_camera_logs'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/settings/', views.api_settings, name='api_settings'),
]

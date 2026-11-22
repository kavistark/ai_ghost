from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/tasks/', views.api_tasks, name='api_tasks'),
    path('api/reminders/', views.api_reminders, name='api_reminders'),
    path('api/schedule/', views.api_schedule, name='api_schedule'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/plan/', views.api_plan, name='api_plan'),
    path('api/command/', views.api_command, name='api_command'),
    path('api/agent/run/', views.api_agent_run, name='api_agent_run'),
    path('api/agent/memories/', views.api_memories, name='api_memories'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/settings/', views.api_settings, name='api_settings'),
]

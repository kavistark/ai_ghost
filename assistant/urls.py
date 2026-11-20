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
]


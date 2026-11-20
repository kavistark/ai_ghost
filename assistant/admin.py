from django.contrib import admin
from .models import Task, ScheduleItem, Reminder, PhoneMessage, DailyPlan

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('text', 'completed', 'created_at')
    list_filter = ('completed', 'created_at')
    search_fields = ('text',)

@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    list_display = ('time', 'title', 'date')
    list_filter = ('date',)
    search_fields = ('title',)

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('time', 'text', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('text',)

@admin.register(PhoneMessage)
class PhoneMessageAdmin(admin.ModelAdmin):
    list_display = ('caller', 'time_label', 'message', 'is_pending', 'created_at')
    list_filter = ('is_pending', 'created_at')
    search_fields = ('caller', 'message')

@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = ('order', 'time', 'activity')
    ordering = ('order',)

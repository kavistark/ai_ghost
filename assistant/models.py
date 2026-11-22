from django.db import models
from django.utils import timezone

class Task(models.Model):
    text = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{'[x]' if self.completed else '[ ]'} {self.text}"

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'completed': self.completed
        }


class ScheduleItem(models.Model):
    time = models.CharField(max_length=10) # e.g. "09:30"
    title = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.time} - {self.title}"

    def to_dict(self):
        return {
            'id': self.id,
            'time': self.time,
            'title': self.title,
            'date': self.date.strftime('%Y-%m-%d')
        }


class Reminder(models.Model):
    time = models.CharField(max_length=10) # e.g. "18:00"
    text = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.date} {self.time} - {self.text}"

    def to_dict(self):
        return {
            'id': self.id,
            'time': self.time,
            'text': self.text,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'is_active': self.is_active
        }


class PhoneMessage(models.Model):
    caller = models.CharField(max_length=100)
    time_label = models.CharField(max_length=20)
    message = models.TextField()
    is_pending = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.caller} ({self.time_label}): {self.message[:30]}"

    def to_dict(self):
        return {
            'id': self.id,
            'caller': self.caller,
            'time': self.time_label,
            'message': self.message,
            'is_pending': self.is_pending
        }


class DailyPlan(models.Model):
    time = models.CharField(max_length=10) # e.g. "09:00"
    activity = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'time']

    def __str__(self):
        return f"{self.time} {self.activity}"

    def to_dict(self):
        return {
            'id': self.id,
            'time': self.time,
            'activity': self.activity,
            'text': f"{self.time} {self.activity}"
        }


class AgentMemory(models.Model):
    """
    Claude Autonomous Agent Long-Term Memory:
    Retains user preferences, contacts, factual context, and learned tasks.
    """
    category = models.CharField(max_length=50, default='general') # 'preference', 'fact', 'contact', 'workflow'
    content = models.TextField()
    source = models.CharField(max_length=100, default='conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.category}] {self.content[:40]}"

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class AgentTaskExecution(models.Model):
    """
    Claude Autonomous Agent Task Execution Ledger:
    Tracks complex multi-step goals assigned to the agent.
    """
    goal = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='in_progress') # 'in_progress', 'needs_approval', 'completed'
    steps = models.JSONField(default=list)
    summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.goal} ({self.status})"

    def to_dict(self):
        return {
            'id': self.id,
            'goal': self.goal,
            'status': self.status,
            'steps': self.steps,
            'summary': self.summary,
            'created_at': self.created_at.strftime('%H:%M')
        }


class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default='web')
    result_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.category}: {self.query}"

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'category': self.category,
            'result': self.result_summary,
            'time': self.created_at.strftime('%H:%M')
        }


class SystemSetting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}={self.value}"

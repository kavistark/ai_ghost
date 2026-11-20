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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"{self.time} - {self.text}"

    def to_dict(self):
        return {
            'id': self.id,
            'time': self.time,
            'text': self.text,
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

from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.academics.models import Subject, Batch


class LiveClass(models.Model):
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live Now'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='live_classes', null=True, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_classes',
        limit_choices_to={'role': 'TEACHER'}
    )
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_classes')
    title = models.CharField(max_length=200, blank=True, default="", help_text="Topic or Chapter name")
    description = models.TextField(blank=True)
    meet_link = models.URLField(max_length=500, help_text="Google Meet link e.g. https://meet.google.com/abc-defg-hij")
    scheduled_start = models.DateTimeField(default=timezone.now)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    is_recurring = models.BooleanField(default=False, help_text="Weekly recurring schedule")
    recurring_day = models.IntegerField(null=True, blank=True, choices=(
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Live Classes'
        ordering = ['-scheduled_start']

    def __str__(self):
        std_name = f" ({self.subject.standard.name})" if self.subject.standard else ""
        return f"{self.title} - {self.subject.name}{std_name} ({self.get_status_display()})"

    def start_class(self):
        now = timezone.now()
        self.actual_start_time = now
        self.status = 'LIVE'
        self.save(update_fields=['actual_start_time', 'status'])
        return self

    def end_class(self):
        now = timezone.now()
        self.actual_end_time = now
        self.status = 'COMPLETED'
        self.save(update_fields=['actual_end_time', 'status'])
        return self

    @property
    def duration_minutes(self):
        if self.actual_start_time and self.actual_end_time:
            diff = self.actual_end_time - self.actual_start_time
            return round(diff.total_seconds() / 60, 1)
        elif self.actual_start_time and self.status == 'LIVE':
            diff = timezone.now() - self.actual_start_time
            return round(diff.total_seconds() / 60, 1)
        return None

    @property
    def attendee_count(self):
        return self.attendances.count()


class ClassAttendance(models.Model):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_attendances',
        limit_choices_to={'role': 'STUDENT'}
    )
    joined_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Class Attendances'
        unique_together = ('live_class', 'student')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.student.username} joined {self.live_class.title} at {self.joined_at.strftime('%H:%M:%S')}"

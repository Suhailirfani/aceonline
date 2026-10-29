from django.db import models
from django.conf import settings


class Standard(models.Model):
    """
    Academic Classes / Standards from 1st Standard up to Postgraduate (e.g. 1st, 2nd... 10th, Plus Two, B.Com, M.Com).
    Admin can create, reorder, and configure subjects under each standard.
    """
    CATEGORY_CHOICES = (
        ('PRIMARY', 'Primary (1st - 5th)'),
        ('UPPER_PRIMARY', 'Upper Primary (6th - 8th)'),
        ('HIGH_SCHOOL', 'High School (9th - 10th)'),
        ('HIGHER_SECONDARY', 'Higher Secondary (Plus One & Plus Two)'),
        ('UNDERGRADUATE', 'Undergraduate (UG / Degree)'),
        ('POSTGRADUATE', 'Postgraduate (PG)'),
        ('OTHER', 'Special / Competitive'),
    )

    name = models.CharField(max_length=100, unique=True, help_text="e.g. 1st Standard, 10th Standard, Plus Two Science, B.Com, M.Com")
    code = models.CharField(max_length=30, unique=True, help_text="Short identifier e.g. STD-1, STD-10, PLUS-TWO, MCOM")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='HIGH_SCHOOL')
    order = models.PositiveIntegerField(default=1, help_text="Order index for dropdown display")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Standard / Class'
        verbose_name_plural = 'Standards / Classes'

    def __str__(self):
        return self.name

    @property
    def active_subjects_count(self):
        return self.subjects.count()

    @property
    def pending_on_demand_count(self):
        return self.on_demand_subjects.filter(status='PENDING').count()


class Subject(models.Model):
    """
    Subjects tied to a specific Standard (e.g., Environmental Studies for 1st Standard, Accounting for M.Com).
    """
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='subjects', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_subjects',
        limit_choices_to={'role': 'TEACHER'}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['standard__order', 'name']

    def __str__(self):
        if self.standard:
            return f"{self.name} - {self.standard.name}"
        return f"{self.name} ({self.code})"

    @property
    def teacher_display(self):
        if self.teacher:
            return self.teacher.get_full_name() or self.teacher.username
        return "Unassigned"

    @property
    def enrolled_count(self):
        return self.enrolled_students.count()


class OnDemandSubject(models.Model):
    """
    Requested custom/other subjects submitted by students or admins during registration.
    Admin reviews and can approve them into official subjects for that standard with 1 click.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved & Added to Subjects'),
        ('REJECTED', 'Rejected / Not Offered'),
    )

    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='on_demand_subjects')
    subject_name = models.CharField(max_length=150, help_text="Name of the wanted on-demand subject")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='on_demand_requests'
    )
    student_name = models.CharField(max_length=150, blank=True, help_text="Student name at registration")
    student_contact = models.CharField(max_length=100, blank=True, help_text="Email or phone")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='on_demand_source')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'On-Demand Subject Request'
        verbose_name_plural = 'On-Demand Subject Requests'

    def __str__(self):
        return f"{self.subject_name} ({self.standard.name}) - {self.get_status_display()}"


class Batch(models.Model):
    name = models.CharField(max_length=150, help_text="e.g. Grade 10 - Mathematics Morning Batch")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='batches')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_batches',
        limit_choices_to={'role': 'TEACHER'}
    )
    schedule_info = models.CharField(max_length=200, blank=True, help_text="e.g. Mon, Wed, Fri 5:00 PM - 6:30 PM")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Batches'
        ordering = ['-created_at']

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username if self.teacher else "Unassigned"
        return f"{self.name} - {self.subject.name} ({teacher_name})"

    @property
    def teacher_display(self):
        if self.teacher:
            return self.teacher.get_full_name() or self.teacher.username
        return "Unassigned"

    @property
    def student_count(self):
        return self.enrollments.filter(is_active=True).count()


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'STUDENT'}
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'batch')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.username} enrolled in {self.batch.name}"

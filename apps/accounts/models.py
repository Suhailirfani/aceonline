from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return super().create_superuser(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    phone = models.CharField(max_length=20, blank=True, null=True)

    objects = CustomUserManager()

    @property
    def is_teacher(self):
        return self.role == 'TEACHER' and not self.is_superuser

    @property
    def is_student(self):
        return self.role == 'STUDENT' and not (self.is_superuser or self.is_staff)

    @property
    def taught_subjects(self):
        if hasattr(self, 'assigned_subjects'):
            return self.assigned_subjects.all()
        return []

    @property
    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser or self.is_staff

    def save(self, *args, **kwargs):
        # Ensure superusers and staff are automatically assigned ADMIN role
        if self.is_superuser and self.role != 'ADMIN':
            self.role = 'ADMIN'
        super().save(*args, **kwargs)

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        return f"{display_name} ({self.get_role_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    standard = models.ForeignKey('academics.Standard', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    grade_level = models.CharField(max_length=100, blank=True, help_text="e.g. 1st Standard, 10th Standard, M.Com")
    enrolled_subjects = models.ManyToManyField('academics.Subject', blank=True, related_name='enrolled_students')
    parent_name = models.CharField(max_length=150, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        class_name = self.standard.name if self.standard else self.grade_level
        return f"Student: {self.user.username} - {class_name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='teacher_profile')
    qualification = models.CharField(max_length=200, blank=True)
    subject_specialization = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Teacher: {self.user.username} ({self.subject_specialization})"

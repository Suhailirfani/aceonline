from django.db import models
from django.conf import settings
from apps.academics.models import Batch, Subject


class Exam(models.Model):
    title = models.CharField(max_length=200, help_text="e.g. Mid-term Assessment 2026")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    exam_date = models.DateField()
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100.00)
    passing_marks = models.DecimalField(max_digits=6, decimal_places=2, default=40.00)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_exams'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-exam_date', '-created_at']

    def __str__(self):
        std_name = f" ({self.subject.standard.name})" if self.subject.standard else ""
        return f"{self.title} - {self.subject.name}{std_name}"

    @property
    def total_students(self):
        return self.results.count()

    @property
    def average_score(self):
        evaluated = self.results.filter(is_absent=False, marks_obtained__isnull=False)
        if evaluated.exists():
            total = sum(r.marks_obtained for r in evaluated)
            return round(float(total) / evaluated.count(), 2)
        return 0.0

    @property
    def highest_score(self):
        evaluated = self.results.filter(is_absent=False, marks_obtained__isnull=False)
        if evaluated.exists():
            return max(r.marks_obtained for r in evaluated)
        return 0.0


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_results',
        limit_choices_to={'role': 'STUDENT'}
    )
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_absent = models.BooleanField(default=False)
    remarks = models.CharField(max_length=255, blank=True, help_text="Teacher's evaluation feedback")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['student__username']

    def __str__(self):
        status_str = "Absent" if self.is_absent else f"{self.marks_obtained}/{self.exam.total_marks}"
        return f"{self.student.username} - {self.exam.title}: {status_str}"

    @property
    def percentage(self):
        if self.is_absent or self.marks_obtained is None or self.exam.total_marks == 0:
            return 0.0
        return round((float(self.marks_obtained) / float(self.exam.total_marks)) * 100, 2)

    @property
    def is_passed(self):
        if self.is_absent or self.marks_obtained is None:
            return False
        return self.marks_obtained >= self.exam.passing_marks

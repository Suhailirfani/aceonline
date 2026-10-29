from django.contrib import admin
from .models import Exam, ExamResult


class ExamResultInline(admin.TabularInline):
    model = ExamResult
    extra = 0
    autocomplete_fields = ['student']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'subject', 'exam_date', 'total_marks', 'passing_marks', 'average_score', 'created_by')
    list_filter = ('batch', 'subject', 'exam_date')
    search_fields = ('title', 'batch__name', 'subject__name')
    inlines = [ExamResultInline]


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'marks_obtained', 'is_absent', 'percentage', 'is_passed', 'updated_at')
    list_filter = ('exam__batch', 'is_absent')
    search_fields = ('student__username', 'exam__title')

from django.contrib import admin
from .models import Subject, Batch, Enrollment


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'teacher', 'schedule_info', 'student_count', 'is_active', 'created_at')
    list_filter = ('subject', 'teacher', 'is_active')
    search_fields = ('name', 'subject__name', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    inlines = [EnrollmentInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch', 'is_active', 'enrolled_at')
    list_filter = ('batch', 'is_active')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'batch__name')

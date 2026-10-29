from django.contrib import admin
from .models import LiveClass, ClassAttendance


class ClassAttendanceInline(admin.TabularInline):
    model = ClassAttendance
    extra = 0
    readonly_fields = ('student', 'joined_at', 'ip_address')


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'teacher', 'status', 'scheduled_start', 'actual_start_time', 'actual_end_time', 'attendee_count')
    list_filter = ('status', 'batch', 'teacher')
    search_fields = ('title', 'batch__name', 'teacher__username')
    inlines = [ClassAttendanceInline]


@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'live_class', 'joined_at', 'ip_address')
    list_filter = ('live_class__batch', 'joined_at')
    search_fields = ('student__username', 'live_class__title')

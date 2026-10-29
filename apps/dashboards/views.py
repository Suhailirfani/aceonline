from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from apps.academics.models import Standard, Subject, OnDemandSubject
from apps.classrooms.models import LiveClass, ClassAttendance
from apps.exams.models import Exam, ExamResult

User = get_user_model()


@login_required
def admin_dashboard(request):
    if not request.user.is_admin_user:
        return redirect('dashboard_redirect')

    total_students = User.objects.filter(role='STUDENT').count()
    total_teachers = User.objects.filter(role='TEACHER').count()
    total_standards = Standard.objects.count()
    total_subjects = Subject.objects.count()
    pending_on_demand_count = OnDemandSubject.objects.filter(status='PENDING').count()
    
    live_classes_now = LiveClass.objects.filter(status='LIVE').select_related('subject', 'subject__standard', 'teacher')
    recent_classes = LiveClass.objects.all().select_related('subject', 'subject__standard', 'teacher')[:8]
    recent_exams = Exam.objects.all().select_related('subject', 'subject__standard')[:5]
    recent_students = User.objects.filter(role='STUDENT').select_related('student_profile', 'student_profile__standard').order_by('-date_joined')[:6]

    return render(request, 'dashboards/admin_dashboard.html', {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_standards': total_standards,
        'total_subjects': total_subjects,
        'pending_on_demand_count': pending_on_demand_count,
        'live_classes_now': live_classes_now,
        'recent_classes': recent_classes,
        'recent_exams': recent_exams,
        'recent_students': recent_students,
    })


@login_required
def teacher_dashboard(request):
    if not (request.user.is_teacher or request.user.is_admin_user):
        return redirect('dashboard_redirect')

    user = request.user
    my_subjects = Subject.objects.filter(teacher=user).select_related('standard')
    
    # Students enrolled in subjects taught by this teacher
    total_students = User.objects.filter(student_profile__enrolled_subjects__in=my_subjects).distinct().count()
    
    # Active live classes right now
    live_classes_now = LiveClass.objects.filter(teacher=user, status='LIVE').select_related('subject', 'subject__standard')
    
    # Scheduled and upcoming classes
    upcoming_classes = LiveClass.objects.filter(
        teacher=user,
        status__in=['SCHEDULED', 'LIVE']
    ).select_related('subject', 'subject__standard').order_by('scheduled_start')[:6]
    
    recent_completed_classes = LiveClass.objects.filter(
        teacher=user,
        status='COMPLETED'
    ).select_related('subject', 'subject__standard').order_by('-actual_end_time')[:5]

    my_exams = Exam.objects.filter(Q(created_by=user) | Q(subject__teacher=user)).select_related('subject', 'subject__standard')[:5]

    return render(request, 'dashboards/teacher_dashboard.html', {
        'my_subjects': my_subjects,
        'total_students': total_students,
        'live_classes_now': live_classes_now,
        'upcoming_classes': upcoming_classes,
        'recent_completed_classes': recent_completed_classes,
        'my_exams': my_exams,
    })


@login_required
def student_dashboard(request):
    if not request.user.is_student and not request.user.is_admin_user:
        return redirect('dashboard_redirect')

    user = request.user
    profile = getattr(user, 'student_profile', None)
    student_standard = profile.standard if profile else None
    enrolled_subjects = profile.enrolled_subjects.select_related('standard').all() if profile else []
    subject_ids = [s.id for s in enrolled_subjects]

    # Check for LIVE classes in student's subjects right now
    live_classes_now = LiveClass.objects.filter(
        subject_id__in=subject_ids,
        status='LIVE'
    ).select_related('subject', 'subject__standard', 'teacher')

    upcoming_classes = LiveClass.objects.filter(
        subject_id__in=subject_ids,
        status='SCHEDULED'
    ).select_related('subject', 'subject__standard', 'teacher').order_by('scheduled_start')[:5]

    # Attendance stats
    total_classes_conducted = LiveClass.objects.filter(subject_id__in=subject_ids, status__in=['LIVE', 'COMPLETED']).count()
    attended_count = ClassAttendance.objects.filter(student=user).count()
    if total_classes_conducted > 0:
        attendance_pct = min(100.0, round((attended_count / total_classes_conducted * 100), 1))
    else:
        attendance_pct = 100.0

    recent_attendances = ClassAttendance.objects.filter(student=user).select_related('live_class', 'live_class__subject', 'live_class__subject__standard').order_by('-joined_at')[:6]
    recent_exam_results = ExamResult.objects.filter(student=user).select_related('exam', 'exam__subject', 'exam__subject__standard').order_by('-exam__exam_date')[:5]

    return render(request, 'dashboards/student_dashboard.html', {
        'student_standard': student_standard,
        'enrolled_subjects': enrolled_subjects,
        'live_classes_now': live_classes_now,
        'upcoming_classes': upcoming_classes,
        'total_classes_conducted': total_classes_conducted,
        'attended_count': attended_count,
        'attendance_pct': attendance_pct,
        'recent_attendances': recent_attendances,
        'recent_exam_results': recent_exam_results,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta, date
from django.utils.dateparse import parse_date
from .models import LiveClass, ClassAttendance
from .forms import LiveClassForm
from apps.academics.models import Batch, Enrollment


@login_required
def class_list(request):
    user = request.user
    if user.is_admin_user:
        classes = LiveClass.objects.all().select_related('subject', 'subject__standard', 'teacher')
    elif user.is_teacher:
        classes = LiveClass.objects.filter(teacher=user).select_related('subject', 'subject__standard')
    else:
        # Student: get classes for subjects they are enrolled in
        enrolled_subjects = user.student_profile.enrolled_subjects.all() if hasattr(user, 'student_profile') else []
        classes = LiveClass.objects.filter(subject__in=enrolled_subjects).select_related('subject', 'subject__standard', 'teacher')

    form = LiveClassForm(user=user) if (user.is_teacher or user.is_admin_user) else None

    if request.method == 'POST' and (user.is_teacher or user.is_admin_user):
        form = LiveClassForm(user, request.POST)
        if form.is_valid():
            live_class = form.save(commit=False)
            if not live_class.title and live_class.subject:
                live_class.title = f"{live_class.subject.name} Class"
            if user.is_teacher:
                if live_class.subject.teacher != user:
                    messages.error(request, "Permission denied: You can only schedule classes for your assigned subjects.")
                    return redirect('classrooms:class_list')
                live_class.teacher = user
            else:
                # Admin scheduling: check form-selected teacher, subject's teacher, or fallback active teacher
                chosen_teacher = form.cleaned_data.get('teacher')
                if chosen_teacher:
                    live_class.teacher = chosen_teacher
                elif live_class.subject and live_class.subject.teacher:
                    live_class.teacher = live_class.subject.teacher
                else:
                    from apps.accounts.models import CustomUser
                    fallback_teacher = CustomUser.objects.filter(role='TEACHER', is_active=True).first()
                    live_class.teacher = fallback_teacher or user
            live_class.save()
            
            # If recurring is chosen (from form or request.POST)
            is_rec = form.cleaned_data.get('is_recurring') or (request.POST.get('is_recurring') in ['on', 'true', '1'])
            if is_rec:
                live_class.is_recurring = True
                live_class.recurring_day = live_class.scheduled_start.weekday()
                live_class.save(update_fields=['is_recurring', 'recurring_day'])
                
                weeks = form.cleaned_data.get('repeat_weeks') or int(request.POST.get('repeat_weeks') or 4)
                for w in range(1, weeks):
                    next_time = live_class.scheduled_start + timedelta(weeks=w)
                    LiveClass.objects.create(
                        subject=live_class.subject,
                        teacher=live_class.teacher,
                        batch=live_class.batch,
                        title=live_class.title,
                        description=live_class.description,
                        meet_link=live_class.meet_link,
                        scheduled_start=next_time,
                        status='SCHEDULED',
                        is_recurring=True,
                        recurring_day=next_time.weekday(),
                    )
                messages.success(request, f"Recurring Live Class '{live_class.title}' scheduled for {weeks} weeks successfully!")
            else:
                messages.success(request, f"Live Class '{live_class.title}' scheduled successfully!")
            return redirect('classrooms:class_list')

    # Date filter: default to today in local timezone (or 'all' if selected)
    today_local = timezone.localdate()
    selected_date_str = request.GET.get('date', '').strip()
    show_all = request.GET.get('all', '').strip() == '1'

    selected_date = None
    if show_all:
        selected_date = None
    elif selected_date_str:
        parsed = parse_date(selected_date_str)
        if parsed:
            selected_date = parsed
        else:
            selected_date = today_local
    else:
        selected_date = today_local

    if selected_date:
        classes = classes.filter(scheduled_start__date=selected_date)

    classes = classes.order_by('scheduled_start')

    # Also extract student's attended class IDs for badge display
    attended_class_ids = set()
    if user.is_student:
        attended_class_ids = set(ClassAttendance.objects.filter(student=user).values_list('live_class_id', flat=True))

    return render(request, 'classrooms/class_list.html', {
        'classes': classes,
        'form': form,
        'attended_class_ids': attended_class_ids,
        'selected_date': selected_date.isoformat() if selected_date else '',
        'selected_date_display': selected_date.strftime('%A, %B %d, %Y') if selected_date else 'All Dates',
        'is_today': selected_date == today_local if selected_date else False,
        'today_str': today_local.isoformat(),
        'show_all': show_all,
    })


@login_required
def class_detail(request, pk):
    user = request.user
    live_class = get_object_or_404(LiveClass.objects.select_related('subject', 'subject__standard', 'teacher'), pk=pk)
    attendances = live_class.attendances.select_related('student').all()
    user_has_attended = False
    if user.is_student:
        user_has_attended = live_class.attendances.filter(student=user).exists()

    return render(request, 'classrooms/class_detail.html', {
        'class': live_class,
        'attendances': attendances,
        'user_has_attended': user_has_attended,
    })


# ----------------------------------------------------
# AJAX ENDPOINTS
# ----------------------------------------------------

@login_required
@require_POST
def ajax_start_class(request, pk):
    """Teacher starts the live class (records actual start time)."""
    live_class = get_object_or_404(LiveClass, pk=pk)
    if not (request.user == live_class.teacher or request.user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    live_class.start_class()
    return JsonResponse({
        'success': True,
        'status': live_class.status,
        'status_display': live_class.get_status_display(),
        'actual_start_time': live_class.actual_start_time.strftime('%I:%M %p, %d %b %Y'),
        'message': f"Class '{live_class.title}' is now LIVE! Started at {live_class.actual_start_time.strftime('%I:%M %p')}."
    })


@login_required
@require_POST
def ajax_end_class(request, pk):
    """Teacher ends the live class (records actual end time)."""
    live_class = get_object_or_404(LiveClass, pk=pk)
    if not (request.user == live_class.teacher or request.user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    live_class.end_class()
    return JsonResponse({
        'success': True,
        'status': live_class.status,
        'status_display': live_class.get_status_display(),
        'actual_end_time': live_class.actual_end_time.strftime('%I:%M %p, %d %b %Y'),
        'duration_minutes': live_class.duration_minutes,
        'message': f"Class concluded. Total duration: {live_class.duration_minutes or 0} minutes."
    })


@login_required
@require_POST
def ajax_join_class(request, pk):
    """
    Student clicks to join Google Meet.
    Attendance is automatically marked upon entry, and Google Meet link is returned.
    """
    live_class = get_object_or_404(LiveClass, pk=pk)
    user = request.user

    # Verify student is enrolled in the subject
    if user.is_student:
        is_enrolled = hasattr(user, 'student_profile') and (
            user.student_profile.enrolled_subjects.filter(id=live_class.subject_id).exists()
            or (live_class.subject and user.student_profile.standard == live_class.subject.standard)
        )
        if not is_enrolled:
            return JsonResponse({'success': False, 'error': 'You are not enrolled in this subject.'}, status=403)

    # Capture IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    attendance, created = ClassAttendance.objects.get_or_create(
        live_class=live_class,
        student=user,
        defaults={'joined_at': timezone.now(), 'ip_address': ip}
    )

    return JsonResponse({
        'success': True,
        'meet_link': live_class.meet_link,
        'already_attended': not created,
        'joined_at': attendance.joined_at.strftime('%I:%M %p'),
        'attendee_count': live_class.attendee_count,
        'message': 'Attendance registered successfully! Opening Google Meet...'
    })


@login_required
def ajax_get_attendees(request, pk):
    """Teacher views real-time attendance stream without page refresh."""
    live_class = get_object_or_404(LiveClass, pk=pk)
    if not (request.user == live_class.teacher or request.user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    attendances = live_class.attendances.select_related('student').all()
    attendee_data = [
        {
            'username': att.student.username,
            'full_name': att.student.get_full_name() or att.student.username,
            'joined_at': att.joined_at.strftime('%I:%M:%S %p'),
            'email': att.student.email or 'N/A'
        }
        for att in attendances
    ]

    return JsonResponse({
        'success': True,
        'count': len(attendee_data),
        'attendees': attendee_data
    })

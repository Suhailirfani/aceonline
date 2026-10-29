from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from apps.academics.models import Standard
from .forms import (
    LoginForm,
    StudentRegistrationForm,
    TeacherRegistrationForm,
    TeacherAdminCreateForm,
    TeacherAdminUpdateForm,
    AdminStudentCreateForm,
)

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == 'STUDENT' and hasattr(user, 'student_profile') and not user.student_profile.is_approved:
                messages.warning(
                    request, 
                    "Your enrollment application has been received and is awaiting admin approval. You will receive portal access once your application is approved."
                )
                return redirect('login')
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


def register_student(request):
    if request.user.is_authenticated and not request.user.is_admin_user:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(post_data=request.POST)
            if request.user.is_authenticated and request.user.is_admin_user:
                messages.success(request, f"Enrollment application for '{user.get_full_name() or user.username}' registered successfully!")
                return redirect('accounts:student_list')
            messages.success(
                request, 
                f"Thank you, {user.get_full_name() or user.username}! Your admission application has been submitted successfully. The administration team will review and approve your application shortly."
            )
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors in the registration form.")
    else:
        form = StudentRegistrationForm()

    standards = Standard.objects.filter(is_active=True)

    # If admin is viewing the registration page, also provide the new student applications and on-demand subjects
    pending_applications = []
    pending_on_demand_subjects = []
    if request.user.is_authenticated and request.user.is_admin_user:
        from apps.academics.models import OnDemandSubject
        pending_applications = User.objects.filter(
            role='STUDENT',
            student_profile__is_approved=False
        ).select_related('student_profile', 'student_profile__standard').prefetch_related(
            'student_profile__enrolled_subjects',
            'on_demand_requests'
        ).order_by('-date_joined')

        pending_on_demand_subjects = OnDemandSubject.objects.filter(
            status='PENDING'
        ).select_related('standard', 'requested_by').order_by('-created_at')

    return render(request, 'accounts/register_student.html', {
        'form': form,
        'standards': standards,
        'pending_applications': pending_applications,
        'pending_on_demand_subjects': pending_on_demand_subjects,
    })


def register_teacher(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Teacher account created successfully! You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeacherRegistrationForm()

    return render(request, 'accounts/register_teacher.html', {'form': form})


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_admin_user:
        return redirect('dashboards:admin_dashboard')
    elif user.is_teacher:
        return redirect('dashboards:teacher_dashboard')
    elif user.is_student:
        return redirect('dashboards:student_dashboard')
    else:
        return redirect('dashboards:student_dashboard')


def landing_page(request):
    from apps.academics.models import Standard, Subject
    from apps.classrooms.models import LiveClass

    total_students = User.objects.filter(role='STUDENT').count()
    total_teachers = User.objects.filter(role='TEACHER').count()
    total_standards = Standard.objects.count()
    total_subjects = Subject.objects.count()
    active_live_classes = LiveClass.objects.filter(status='LIVE').count()

    return render(request, 'landing.html', {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_standards': total_standards,
        'total_subjects': total_subjects,
        'active_live_classes': active_live_classes,
    })


# ==============================================================================
# TEACHER CRUD (ADMIN FACULTY MANAGEMENT)
# ==============================================================================

@login_required
def teacher_list(request):
    """Lists all teachers with search, active status filter, and assigned cohorts."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')

    teachers = User.objects.filter(role='TEACHER').select_related('teacher_profile').prefetch_related('assigned_subjects', 'assigned_subjects__standard')

    if q:
        teachers = teachers.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(teacher_profile__subject_specialization__icontains=q) |
            Q(teacher_profile__qualification__icontains=q)
        )

    if status == 'active':
        teachers = teachers.filter(is_active=True)
    elif status == 'inactive':
        teachers = teachers.filter(is_active=False)

    teachers = teachers.order_by('-date_joined')

    all_teachers_count = User.objects.filter(role='TEACHER').count()
    active_teachers_count = User.objects.filter(role='TEACHER', is_active=True).count()
    inactive_teachers_count = all_teachers_count - active_teachers_count

    return render(request, 'accounts/teacher_list.html', {
        'teachers': teachers,
        'q': q,
        'status': status,
        'all_teachers_count': all_teachers_count,
        'active_teachers_count': active_teachers_count,
        'inactive_teachers_count': inactive_teachers_count,
    })


@login_required
def teacher_create(request):
    """Admin registers a new certified teacher."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = TeacherAdminCreateForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            messages.success(request, f"Teacher '{teacher.get_full_name() or teacher.username}' registered successfully!")
            return redirect('accounts:teacher_list')
        else:
            messages.error(request, "Please resolve the form errors below.")
    else:
        form = TeacherAdminCreateForm()

    return render(request, 'accounts/teacher_form.html', {
        'form': form,
        'page_title': 'Register New Teacher',
        'btn_text': 'Create Teacher Account',
    })


@login_required
def teacher_edit(request, pk):
    """Admin modifies an existing teacher's credentials, qualifications, or bio."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    teacher = get_object_or_404(User, pk=pk, role='TEACHER')

    if request.method == 'POST':
        form = TeacherAdminUpdateForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, f"Teacher profile for '{teacher.get_full_name() or teacher.username}' updated successfully!")
            return redirect('accounts:teacher_list')
        else:
            messages.error(request, "Please resolve the form errors below.")
    else:
        form = TeacherAdminUpdateForm(instance=teacher)

    return render(request, 'accounts/teacher_form.html', {
        'form': form,
        'teacher': teacher,
        'page_title': f"Edit Teacher: {teacher.get_full_name() or teacher.username}",
        'btn_text': 'Save Changes',
    })


@login_required
def teacher_toggle_status(request, pk):
    """Quickly toggles a teacher between active and inactive status."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    teacher = get_object_or_404(User, pk=pk, role='TEACHER')
    teacher.is_active = not teacher.is_active
    teacher.save()
    status_label = "activated" if teacher.is_active else "deactivated"
    messages.success(request, f"Teacher '{teacher.username}' has been {status_label}.")
    return redirect('accounts:teacher_list')


@login_required
def teacher_delete(request, pk):
    """Admin removes a teacher account, safely handling cohort assignments."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    teacher = get_object_or_404(User, pk=pk, role='TEACHER')

    if request.method == 'POST':
        teacher_name = teacher.get_full_name() or teacher.username
        # Safely unassign subjects so subjects are not broken
        teacher.assigned_subjects.update(teacher=None)
        teacher.delete()
        messages.success(request, f"Teacher '{teacher_name}' was removed successfully.")
        return redirect('accounts:teacher_list')

    subjects = teacher.assigned_subjects.all()
    return render(request, 'accounts/teacher_confirm_delete.html', {
        'teacher': teacher,
        'subjects': subjects,
    })


# ==============================================================================
# STUDENT MANAGEMENT (ADMIN DIRECTORY & REGISTRATION)
# ==============================================================================

@login_required
def student_list(request):
    """Admin view of enrolled students and pending new applications."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    q = request.GET.get('q', '').strip()
    standard_id = request.GET.get('standard', '')

    base_qs = User.objects.filter(role='STUDENT').select_related(
        'student_profile', 'student_profile__standard'
    ).prefetch_related('student_profile__enrolled_subjects', 'on_demand_requests')

    if q:
        base_qs = base_qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(student_profile__grade_level__icontains=q)
        )

    if standard_id and standard_id.isdigit():
        base_qs = base_qs.filter(student_profile__standard_id=standard_id)

    pending_applications = base_qs.filter(student_profile__is_approved=False).order_by('-date_joined')
    approved_students = base_qs.filter(student_profile__is_approved=True).order_by('-date_joined')

    standards = Standard.objects.filter(is_active=True)

    return render(request, 'accounts/student_list.html', {
        'pending_applications': pending_applications,
        'students': approved_students,
        'all_students_count': base_qs.count(),
        'standards': standards,
        'selected_standard': int(standard_id) if standard_id.isdigit() else None,
        'q': q,
    })


@login_required
def student_approve(request, pk):
    """Admin approves student application, including them in respective class and enrolled subjects."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    student = get_object_or_404(User, pk=pk, role='STUDENT')
    profile = getattr(student, 'student_profile', None)

    if profile:
        profile.is_approved = True
        profile.save()

    student.is_active = True
    student.save()

    std_name = profile.standard.name if (profile and profile.standard) else 'their class'
    enrolled_count = profile.enrolled_subjects.count() if profile else 0
    messages.success(
        request, 
        f"Application approved! {student.get_full_name() or student.username} is now admitted and included in {std_name} with {enrolled_count} enrolled subject(s)."
    )

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('accounts:student_list')


@login_required
def student_reject(request, pk):
    """Admin rejects/removes an unapproved student application."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    student = get_object_or_404(User, pk=pk, role='STUDENT')
    name = student.get_full_name() or student.username
    student.delete()
    messages.info(request, f"Application for '{name}' was removed.")

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('accounts:student_list')


@login_required
def student_create(request):
    """Admin registers a student directly with standard and subject choices."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = AdminStudentCreateForm(request.POST)
        if form.is_valid():
            student = form.save(post_data=request.POST)
            messages.success(request, f"Student '{student.get_full_name() or student.username}' created and enrolled successfully!")
            return redirect('accounts:student_list')
        else:
            messages.error(request, "Please resolve the form errors below.")
    else:
        form = AdminStudentCreateForm()

    standards = Standard.objects.filter(is_active=True)
    return render(request, 'accounts/student_create.html', {
        'form': form,
        'standards': standards,
    })




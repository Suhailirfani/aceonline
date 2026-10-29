from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from .models import Standard, Subject, OnDemandSubject, Batch, Enrollment
from .forms import StandardForm, SubjectForm, BatchForm, EnrollmentForm


# ==============================================================================
# API: DYNAMIC SUBJECTS BY STANDARD (FOR STUDENT REGISTRATION & ENROLLMENT)
# ==============================================================================

def api_standard_subjects(request, standard_id):
    """
    Returns JSON list of subjects belonging to a chosen Standard / Class.
    Used dynamically via AJAX on student registration and enrollment forms.
    """
    try:
        std = Standard.objects.get(id=standard_id, is_active=True)
        subjects_data = list(std.subjects.all().values('id', 'name', 'code', 'description'))
        return JsonResponse({
            'success': True,
            'standard': {'id': std.id, 'name': std.name, 'code': std.code},
            'subjects': subjects_data
        })
    except Standard.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Standard not found', 'subjects': []}, status=404)


# ==============================================================================
# STANDARDS / CLASSES MANAGEMENT (ADMIN CRUD)
# ==============================================================================

@login_required
def standard_list(request):
    """
    Admin management view for Standards (Classes from 1st to PG e.g. M.Com).
    """
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    standards = Standard.objects.all().prefetch_related('subjects', 'on_demand_subjects')
    form = StandardForm()

    if request.method == 'POST':
        form = StandardForm(request.POST)
        if form.is_valid():
            std = form.save()
            messages.success(request, f"Standard / Class '{std.name}' created successfully!")
            return redirect('academics:standard_list')
        else:
            messages.error(request, "Please resolve the form errors below.")

    return render(request, 'academics/standard_list.html', {
        'standards': standards,
        'form': form,
    })


@login_required
def standard_edit(request, pk):
    """Admin updates an existing Standard / Class definition."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    standard = get_object_or_404(Standard, pk=pk)

    if request.method == 'POST':
        form = StandardForm(request.POST, instance=standard)
        if form.is_valid():
            form.save()
            messages.success(request, f"Standard '{standard.name}' updated successfully!")
            return redirect('academics:standard_list')
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = StandardForm(instance=standard)

    return render(request, 'academics/standard_form.html', {
        'form': form,
        'standard': standard,
        'page_title': f"Edit Standard: {standard.name}",
    })


@login_required
def standard_delete(request, pk):
    """Admin deletes a Standard / Class."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    standard = get_object_or_404(Standard, pk=pk)

    if request.method == 'POST':
        name = standard.name
        standard.delete()
        messages.success(request, f"Standard '{name}' deleted successfully.")
        return redirect('academics:standard_list')

    return render(request, 'academics/standard_confirm_delete.html', {
        'standard': standard,
    })


# ==============================================================================
# SUBJECTS MANAGEMENT (TIED TO STANDARDS)
# ==============================================================================

@login_required
def subject_list(request):
    """
    Lists subjects grouped by Standard / Class with collapsible accordion headers.
    """
    from django.db.models import Prefetch, Q

    standard_id = request.GET.get('standard', '').strip()
    search_query = request.GET.get('q', '').strip()

    subject_qs = Subject.objects.select_related('standard', 'teacher')
    if search_query:
        subject_qs = subject_qs.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(teacher__username__icontains=search_query) |
            Q(teacher__first_name__icontains=search_query) |
            Q(teacher__last_name__icontains=search_query)
        )

    all_standards = Standard.objects.filter(is_active=True).order_by('order', 'name')
    standards_qs = all_standards.prefetch_related(
        Prefetch(
            'subjects',
            queryset=subject_qs.order_by('name')
        )
    )

    if standard_id and standard_id.isdigit():
        standards_qs = standards_qs.filter(id=int(standard_id))

    # General / unattached subjects (if any)
    general_subjects = []
    if not (standard_id and standard_id.isdigit()):
        general_subjects = list(subject_qs.filter(standard__isnull=True).order_by('name'))

    total_subjects_count = Subject.objects.count()

    form = SubjectForm()
    if request.method == 'POST' and (request.user.is_admin_user or request.user.is_teacher):
        form = SubjectForm(request.POST)
        if form.is_valid():
            sub = form.save()
            messages.success(request, f"Subject '{sub.name}' created for {sub.standard.name if sub.standard else 'General'}!")
            return redirect('academics:subject_list')
        else:
            messages.error(request, "Please correct errors in the subject registration form.")

    return render(request, 'academics/subject_list.html', {
        'standards': standards_qs,
        'all_standards': all_standards,
        'general_subjects': general_subjects,
        'total_subjects_count': total_subjects_count,
        'selected_standard': int(standard_id) if standard_id and standard_id.isdigit() else None,
        'search_query': search_query,
        'form': form,
    })


# ==============================================================================
# ON-DEMAND SUBJECTS MANAGEMENT (STUDENT REQUESTS)
# ==============================================================================

@login_required
def on_demand_list(request):
    """
    Admin dashboard view of all requested on-demand subjects submitted by students during registration.
    """
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    status_filter = request.GET.get('status', 'all')
    standard_filter = request.GET.get('standard', '')

    requests_qs = OnDemandSubject.objects.select_related('standard', 'requested_by', 'created_subject')

    if status_filter != 'all':
        requests_qs = requests_qs.filter(status=status_filter)

    if standard_filter and standard_filter.isdigit():
        requests_qs = requests_qs.filter(standard_id=standard_filter)

    standards = Standard.objects.filter(is_active=True)
    pending_count = OnDemandSubject.objects.filter(status='PENDING').count()
    approved_count = OnDemandSubject.objects.filter(status='APPROVED').count()

    return render(request, 'academics/on_demand_list.html', {
        'on_demand_requests': requests_qs,
        'standards': standards,
        'status_filter': status_filter,
        'standard_filter': int(standard_filter) if standard_filter.isdigit() else None,
        'pending_count': pending_count,
        'approved_count': approved_count,
    })


@login_required
def on_demand_approve(request, pk):
    """
    Admin approves an on-demand subject request:
    1. Creates official Subject under that Standard
    2. Marks request as APPROVED
    3. Auto-enrolls the student who requested it
    """
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    req_obj = get_object_or_404(OnDemandSubject, pk=pk)

    if request.method == 'POST':
        subject_name = request.POST.get('subject_name', req_obj.subject_name).strip()
        custom_code = request.POST.get('subject_code', '').strip()

        # Generate unique code if not provided
        if not custom_code:
            base_slug = slugify(f"{req_obj.standard.code}-{subject_name}")[:25].upper()
            custom_code = base_slug
            idx = 1
            while Subject.objects.filter(code=custom_code).exists():
                custom_code = f"{base_slug}-{idx}"
                idx += 1

        description = request.POST.get('description', f"Official syllabus for {subject_name} ({req_obj.standard.name})").strip()

        # Create or fetch subject
        subject, created = Subject.objects.get_or_create(
            standard=req_obj.standard,
            name=subject_name,
            defaults={
                'code': custom_code,
                'description': description,
            }
        )

        req_obj.created_subject = subject
        req_obj.status = 'APPROVED'
        req_obj.admin_notes = request.POST.get('admin_notes', 'Approved by administrator.')
        req_obj.save()

        # Auto-enroll student if user account exists
        if req_obj.requested_by and hasattr(req_obj.requested_by, 'student_profile'):
            profile = req_obj.requested_by.student_profile
            profile.enrolled_subjects.add(subject)

        messages.success(request, f"On-Demand Subject '{subject_name}' approved and added to {req_obj.standard.name}!")
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('academics:on_demand_list')

    return render(request, 'academics/on_demand_approve.html', {
        'req_obj': req_obj,
    })


@login_required
def on_demand_reject(request, pk):
    """Admin rejects an on-demand subject request."""
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to administrators.")
        return redirect('dashboard_redirect')

    req_obj = get_object_or_404(OnDemandSubject, pk=pk)

    if request.method == 'POST':
        req_obj.status = 'REJECTED'
        req_obj.admin_notes = request.POST.get('admin_notes', 'Not currently supported.').strip()
        req_obj.save()
        messages.info(request, f"Request for '{req_obj.subject_name}' marked as rejected.")
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('academics:on_demand_list')

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('academics:on_demand_list')


# ==============================================================================
# BATCHES & ENROLLMENT
# ==============================================================================

@login_required
def batch_list(request):
    """Batches replaced by Standards & Subjects. Redirect to subject roster."""
    return redirect('academics:subject_list')


@login_required
def batch_detail(request, pk):
    """Batches replaced by Standards & Subjects. Redirect to subject roster."""
    return redirect('academics:subject_list')

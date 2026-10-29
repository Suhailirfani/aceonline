import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Exam, ExamResult
from .forms import ExamForm

User = get_user_model()


@login_required
def exam_list(request):
    user = request.user
    if user.is_admin_user:
        exams = Exam.objects.all().select_related('subject', 'subject__standard', 'created_by')
    elif user.is_teacher:
        exams = Exam.objects.filter(Q(created_by=user) | Q(subject__teacher=user)).select_related('subject', 'subject__standard')
    else:
        enrolled_subjects = user.student_profile.enrolled_subjects.all() if hasattr(user, 'student_profile') else []
        exams = Exam.objects.filter(subject__in=enrolled_subjects).select_related('subject', 'subject__standard')

    form = ExamForm(user=user) if (user.is_teacher or user.is_admin_user) else None

    if request.method == 'POST' and (user.is_teacher or user.is_admin_user):
        form = ExamForm(user, request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = user
            exam.save()

            # Pre-populate ExamResult rows for all students enrolled in this subject
            enrolled_student_ids = User.objects.filter(
                student_profile__enrolled_subjects=exam.subject
            ).values_list('id', flat=True)

            results_to_create = [
                ExamResult(exam=exam, student_id=student_id)
                for student_id in enrolled_student_ids
            ]
            ExamResult.objects.bulk_create(results_to_create, ignore_conflicts=True)

            messages.success(request, f"Exam '{exam.title}' created and {len(results_to_create)} student mark entries initialized!")
            return redirect('exams:marks_entry', pk=exam.pk)

    return render(request, 'exams/exam_list.html', {
        'exams': exams,
        'form': form,
    })


@login_required
def marks_entry(request, pk):
    """Marks entry page for teachers/admins with live AJAX auto-save."""
    user = request.user
    exam = get_object_or_404(Exam.objects.select_related('subject', 'subject__standard', 'created_by'), pk=pk)

    if not (user.is_admin_user or (exam.subject and user == exam.subject.teacher) or user == exam.created_by):
        messages.error(request, "Permission denied. You can only evaluate exams for your assigned subjects.")
        return redirect('exams:exam_list')

    # Ensure all enrolled students have an ExamResult row
    enrolled_student_ids = User.objects.filter(
        student_profile__enrolled_subjects=exam.subject
    ).values_list('id', flat=True)
    existing_result_student_ids = set(exam.results.values_list('student_id', flat=True))
    missing_students = [s_id for s_id in enrolled_student_ids if s_id not in existing_result_student_ids]
    if missing_students:
        ExamResult.objects.bulk_create([ExamResult(exam=exam, student_id=s) for s in missing_students], ignore_conflicts=True)

    results = exam.results.select_related('student', 'student__student_profile').all()

    return render(request, 'exams/marks_entry.html', {
        'exam': exam,
        'results': results,
    })


@login_required
@require_POST
def ajax_save_mark(request, pk):
    """
    AJAX endpoint for instant mark entry saving.
    Payload: { student_id, marks_obtained, is_absent, remarks }
    """
    exam = get_object_or_404(Exam, pk=pk)
    user = request.user

    if not (user.is_admin_user or (exam.subject and user == exam.subject.teacher) or user == exam.created_by):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        marks_raw = data.get('marks_obtained')
        is_absent = bool(data.get('is_absent', False))
        remarks = data.get('remarks', '').strip()

        result = ExamResult.objects.get(exam=exam, student_id=student_id)

        if is_absent:
            result.is_absent = True
            result.marks_obtained = None
        else:
            result.is_absent = False
            if marks_raw is not None and str(marks_raw).strip() != '':
                marks_val = Decimal(str(marks_raw).strip())
                if marks_val < 0:
                    return JsonResponse({'success': False, 'error': 'Marks cannot be negative.'}, status=400)
                if marks_val > exam.total_marks:
                    return JsonResponse({'success': False, 'error': f'Marks cannot exceed total marks ({exam.total_marks}).'}, status=400)
                result.marks_obtained = marks_val
            else:
                result.marks_obtained = None

        result.remarks = remarks
        result.save()

        return JsonResponse({
            'success': True,
            'student_id': student_id,
            'is_absent': result.is_absent,
            'marks_obtained': float(result.marks_obtained) if result.marks_obtained is not None else None,
            'percentage': result.percentage,
            'is_passed': result.is_passed,
            'exam_average': exam.average_score,
            'exam_highest': float(exam.highest_score),
            'message': 'Mark saved successfully.'
        })

    except ExamResult.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student result record not found.'}, status=404)
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid number format for marks.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def student_my_results(request):
    """Student view for all their exam results."""
    user = request.user
    if not user.is_student:
        return redirect('dashboard_redirect')

    results = ExamResult.objects.filter(student=user).select_related('exam', 'exam__subject', 'exam__batch').order_by('-exam__exam_date')
    return render(request, 'exams/student_results.html', {
        'results': results,
    })

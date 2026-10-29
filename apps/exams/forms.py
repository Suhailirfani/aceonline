from django import forms
from django.utils import timezone
from django.db.models import Q
from .models import Exam
from apps.academics.models import Subject


class SubjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        std_str = f" ({obj.standard.name})" if obj.standard else ""
        return f"{obj.name}{std_str}"


class ExamForm(forms.ModelForm):
    exam_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        initial=lambda: timezone.now().date()
    )
    subject = SubjectChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Select Subject & Standard --",
        required=True
    )

    class Meta:
        model = Exam
        fields = ('subject', 'title', 'exam_date', 'total_marks', 'passing_marks', 'description')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Term 1 Assessment - Calculus'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '1'}),
            'passing_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Topics covered, instructions'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_teacher:
            qs = Subject.objects.filter(Q(teacher=user) | Q(teacher__isnull=True)).select_related('standard')
            if not qs.exists():
                qs = Subject.objects.select_related('standard').all()
            self.fields['subject'].queryset = qs
        elif user.is_admin_user:
            self.fields['subject'].queryset = Subject.objects.select_related('standard').all()

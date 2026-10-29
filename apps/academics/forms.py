from django import forms
from django.contrib.auth import get_user_model
from .models import Standard, Subject, OnDemandSubject, Batch, Enrollment

User = get_user_model()


class StandardForm(forms.ModelForm):
    class Meta:
        model = Standard
        fields = ('name', 'code', 'category', 'order', 'description', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1st Standard, 10th Standard, M.Com'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. STD-1, STD-10, MCOM'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Academic level details'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ('standard', 'name', 'code', 'teacher', 'description')
        widgets = {
            'standard': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Environmental Studies, Advanced Accounting'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. EVS-1, MCOM-101'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Course syllabus and topics (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['standard'].queryset = Standard.objects.filter(is_active=True)
        self.fields['teacher'].queryset = User.objects.filter(role='TEACHER', is_active=True)
        self.fields['teacher'].required = False
        self.fields['teacher'].empty_label = "-- Unassigned / Assign Later --"


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ('name', 'subject', 'teacher', 'schedule_info', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Grade 10 - Weekend Batch'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'schedule_info': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Mon & Wed 6:00 PM'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(role='TEACHER', is_active=True)
        self.fields['subject'].queryset = Subject.objects.select_related('standard').all()


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ('student', 'batch')
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'batch': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role='STUDENT', is_active=True)

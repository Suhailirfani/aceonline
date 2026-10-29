from django import forms
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import LiveClass
from apps.academics.models import Subject

User = get_user_model()


class SubjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        std_str = f" ({obj.standard.name})" if obj.standard else ""
        return f"{obj.name}{std_str}"


class LiveClassForm(forms.ModelForm):
    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        initial=lambda: timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')
    )
    subject = SubjectChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Select Subject & Standard --",
        required=True
    )

    repeat_weeks = forms.IntegerField(
        required=False,
        initial=4,
        min_value=1,
        max_value=24,
        label="Number of Weeks to Repeat",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 4 (weeks)'})
    )

    class Meta:
        model = LiveClass
        fields = ('subject', 'teacher', 'meet_link', 'scheduled_start', 'is_recurring', 'description')
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'meet_link': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://meet.google.com/xyz-abcd-efg'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Class topics, prerequisites, or preparation notes'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_teacher:
            # Teacher can ONLY pick subjects assigned directly to them
            qs = Subject.objects.filter(teacher=user).select_related('standard')
            self.fields['subject'].queryset = qs
            if not qs.exists():
                self.fields['subject'].empty_label = "-- No subjects assigned to you yet --"
            if 'teacher' in self.fields:
                del self.fields['teacher']
        elif user.is_admin_user:
            self.fields['subject'].queryset = Subject.objects.select_related('standard').all()
            if 'teacher' in self.fields:
                self.fields['teacher'].queryset = User.objects.filter(role='TEACHER', is_active=True)
                self.fields['teacher'].empty_label = "-- Auto-assign Subject Faculty --"
                self.fields['teacher'].required = False

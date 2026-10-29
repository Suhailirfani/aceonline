from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import StudentProfile, TeacherProfile

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'


from apps.academics.models import Standard, Subject, OnDemandSubject


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}))
    
    standard = forms.ModelChoiceField(
        queryset=Standard.objects.filter(is_active=True),
        empty_label="-- Select Your Class / Standard --",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'standard-select', 'onchange': 'loadStandardSubjects(this.value)'})
    )
    parent_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Parent / Guardian Name'}))
    parent_phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Parent Phone Number'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Residential Address'}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'
        self.fields['password1'].help_text = 'Minimum 5 characters.'
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Enter password (min 5 characters)',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].help_text = 'Confirm password.'
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        if password2 and len(password2) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password2

    def save(self, commit=True, post_data=None):
        user = super().save(commit=False)
        user.role = 'STUDENT'
        if commit:
            user.save()
            std = self.cleaned_data.get('standard')
            profile = StudentProfile.objects.create(
                user=user,
                standard=std,
                grade_level=std.name if std else '',
                parent_name=self.cleaned_data.get('parent_name', ''),
                parent_phone=self.cleaned_data.get('parent_phone', ''),
                address=self.cleaned_data.get('address', ''),
                is_approved=False  # Requires Admin Approval
            )

            # Process selected official subjects
            if post_data:
                subject_ids = post_data.getlist('subjects')
                if subject_ids:
                    subjects = Subject.objects.filter(id__in=subject_ids)
                    profile.enrolled_subjects.set(subjects)

                # Process on-demand requested other subjects
                other_subjects = post_data.getlist('other_subjects')
                student_full_name = user.get_full_name() or user.username
                student_contact = user.email or user.phone or ''
                for raw_name in other_subjects:
                    name_clean = raw_name.strip()
                    if name_clean and std:
                        OnDemandSubject.objects.create(
                            standard=std,
                            subject_name=name_clean,
                            requested_by=user,
                            student_name=student_full_name,
                            student_contact=student_contact,
                            status='PENDING'
                        )
        return user


class AdminStudentCreateForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}))
    
    standard = forms.ModelChoiceField(
        queryset=Standard.objects.filter(is_active=True),
        empty_label="-- Select Class / Standard --",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'standard-select', 'onchange': 'loadStandardSubjects(this.value)'})
    )
    parent_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Parent / Guardian Name'}))
    parent_phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Parent Phone Number'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Residential Address'}), required=False)
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'is_active' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'
        self.fields['password1'].help_text = 'Minimum 5 characters.'
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Enter password (min 5 characters)',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].help_text = 'Confirm password.'
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        if password2 and len(password2) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password2

    def save(self, commit=True, post_data=None):
        user = super().save(commit=False)
        user.role = 'STUDENT'
        user.is_active = self.cleaned_data.get('is_active', True)
        if commit:
            user.save()
            std = self.cleaned_data.get('standard')
            profile = StudentProfile.objects.create(
                user=user,
                standard=std,
                grade_level=std.name if std else '',
                parent_name=self.cleaned_data.get('parent_name', ''),
                parent_phone=self.cleaned_data.get('parent_phone', ''),
                address=self.cleaned_data.get('address', ''),
                is_approved=True
            )
            if post_data:
                subject_ids = post_data.getlist('subjects')
                if subject_ids:
                    profile.enrolled_subjects.set(Subject.objects.filter(id__in=subject_ids))

                other_subjects = post_data.getlist('other_subjects')
                for raw_name in other_subjects:
                    name_clean = raw_name.strip()
                    if name_clean and std:
                        OnDemandSubject.objects.create(
                            standard=std,
                            subject_name=name_clean,
                            requested_by=user,
                            student_name=user.get_full_name() or user.username,
                            student_contact=user.email or user.phone or '',
                            status='PENDING'
                        )
        return user


class TeacherRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}))
    
    qualification = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. M.Sc Mathematics, B.Ed'}))
    subject_specialization = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pure Mathematics, Physics'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Teaching experience and background'}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'TEACHER'
        if commit:
            user.save()
            TeacherProfile.objects.create(
                user=user,
                qualification=self.cleaned_data.get('qualification', ''),
                subject_specialization=self.cleaned_data.get('subject_specialization', ''),
                bio=self.cleaned_data.get('bio', ''),
                is_approved=True
            )
        return user


class TeacherAdminCreateForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}))
    
    qualification = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. M.Sc Mathematics, B.Ed'}))
    subject_specialization = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pure Mathematics, Physics'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Teaching experience and background'}), required=False)
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'is_active' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'
        self.fields['password1'].help_text = 'Minimum 5 characters.'
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Enter password (min 5 characters)',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].help_text = 'Confirm password.'
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        if password2 and len(password2) < 5:
            raise forms.ValidationError('Password must be at least 5 characters.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'TEACHER'
        user.is_active = self.cleaned_data.get('is_active', True)
        if commit:
            user.save()
            TeacherProfile.objects.update_or_create(
                user=user,
                defaults={
                    'qualification': self.cleaned_data.get('qualification', ''),
                    'subject_specialization': self.cleaned_data.get('subject_specialization', ''),
                    'bio': self.cleaned_data.get('bio', ''),
                    'is_approved': True,
                }
            )
        return user


class TeacherAdminUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}))
    
    qualification = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. M.Sc Mathematics, B.Ed'}))
    subject_specialization = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pure Mathematics, Physics'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Teaching experience and background'}), required=False)
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank to retain current password'}),
        help_text="Only enter a password if you wish to reset it for this teacher."
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'teacher_profile'):
            profile = self.instance.teacher_profile
            self.fields['qualification'].initial = profile.qualification
            self.fields['subject_specialization'].initial = profile.subject_specialization
            self.fields['bio'].initial = profile.bio
        for name, field in self.fields.items():
            if name != 'is_active' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pw = self.cleaned_data.get('new_password')
        if new_pw:
            user.set_password(new_pw)
        if commit:
            user.save()
            TeacherProfile.objects.update_or_create(
                user=user,
                defaults={
                    'qualification': self.cleaned_data.get('qualification', ''),
                    'subject_specialization': self.cleaned_data.get('subject_specialization', ''),
                    'bio': self.cleaned_data.get('bio', ''),
                    'is_approved': True,
                }
            )
        return user


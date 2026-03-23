from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Assignment, StudySession, Subject


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(required=True, widget=forms.PasswordInput)
    password2 = forms.CharField(required=True, widget=forms.PasswordInput)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email is already registered. Please log in.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1") or ""
        password2 = cleaned_data.get("password2") or ""
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        if password1:
            validate_password(password1)
        return cleaned_data

    def save(self) -> User:
        if not self.is_valid():
            raise ValueError("RegisterForm must be valid before calling save().")
        email = self.cleaned_data["email"]
        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"],
            first_name=(self.cleaned_data.get("first_name") or "").strip(),
            last_name=(self.cleaned_data.get("last_name") or "").strip(),
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user: User | None = None

    def clean(self):
        cleaned_data = super().clean()
        email = (cleaned_data.get("email") or "").strip().lower()
        password = cleaned_data.get("password") or ""
        if email and password:
            self.user = authenticate(self.request, username=email, password=password)
        if self.user is None:
            raise ValidationError("Invalid email or password.")
        return cleaned_data


class OnboardingForm(forms.Form):
    subjects = forms.CharField(required=True, help_text="Comma-separated subjects")
    assignment_title = forms.CharField(required=False, max_length=200)
    assignment_subject = forms.CharField(required=False, max_length=100)
    assignment_deadline = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    estimated_hours = forms.FloatField(required=False, min_value=0.25)

    def clean_subjects(self):
        raw = (self.cleaned_data.get("subjects") or "").strip()
        names = [s.strip() for s in raw.split(",") if s.strip()]
        if not names:
            raise ValidationError("Please enter at least one subject.")
        return names

    def clean(self):
        cleaned_data = super().clean()
        title = (cleaned_data.get("assignment_title") or "").strip()
        subject = (cleaned_data.get("assignment_subject") or "").strip()
        deadline = cleaned_data.get("assignment_deadline")

        if any([title, subject, deadline]):
            if not (title and subject and deadline):
                raise ValidationError("To add an assignment, please provide title, subject, and deadline.")
            if cleaned_data.get("estimated_hours") in (None, ""):
                cleaned_data["estimated_hours"] = 2.0
        return cleaned_data


class AddSubjectForm(forms.Form):
    subject_name = forms.CharField(required=True, max_length=100)

    def clean_subject_name(self):
        name = (self.cleaned_data.get("subject_name") or "").strip()
        if not name:
            raise ValidationError("Subject name is required.")
        return name


class AddAssignmentForm(forms.Form):
    title = forms.CharField(required=True, max_length=200)
    subject_id = forms.ModelChoiceField(queryset=Subject.objects.none(), required=True)
    deadline = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date"}))
    estimated_hours = forms.FloatField(required=True, min_value=0.25)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject_id"].queryset = Subject.objects.filter(user=user).order_by("name")


class LogSessionForm(forms.Form):
    subject_id = forms.ModelChoiceField(queryset=Subject.objects.none(), required=True)
    duration = forms.FloatField(required=True, min_value=0.25)
    focus_level = forms.IntegerField(required=True, min_value=0, max_value=100)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject_id"].queryset = Subject.objects.filter(user=user).order_by("name")


class MarkDoneForm(forms.Form):
    assignment_id = forms.ModelChoiceField(queryset=Assignment.objects.none(), required=True)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignment_id"].queryset = Assignment.objects.filter(user=user, is_completed=False)


class SubjectModelForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Mathematics", "autocomplete": "off"}
            ),
        }

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        if self.instance and self.instance.pk:
            self.fields["name"].initial = self.instance.name

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise ValidationError("Subject name is required.")
        qs = Subject.objects.filter(user=self._user, name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("You already have a subject with this name.")
        return name

    def save(self, commit=True):
        self.instance.user = self._user
        return super().save(commit=commit)


class AssignmentModelForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["subject", "title", "deadline", "estimated_hours", "is_completed"]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Unit 3 Worksheet"}),
            "estimated_hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "is_completed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields["subject"].queryset = Subject.objects.filter(user=user).order_by("name")

    def save(self, commit=True):
        self.instance.user = self._user
        return super().save(commit=commit)


class StudySessionModelForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ["subject", "assignment", "duration", "focus_level"]
        widgets = {
            "subject": forms.Select(attrs={"class": "form-select"}),
            "assignment": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
            "focus_level": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
        }

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields["subject"].queryset = Subject.objects.filter(user=user).order_by("name")
        self.fields["assignment"].queryset = Assignment.objects.filter(user=user).order_by("-deadline", "title")
        self.fields["assignment"].required = False

    def clean_focus_level(self):
        focus_level = self.cleaned_data.get("focus_level")
        if focus_level is None:
            return focus_level
        if focus_level < 0 or focus_level > 100:
            raise ValidationError("Focus level must be between 0 and 100.")
        return focus_level

    def clean_duration(self):
        duration = self.cleaned_data.get("duration")
        if duration is None:
            return duration
        if duration <= 0:
            raise ValidationError("Duration must be greater than 0.")
        return duration

    def save(self, commit=True):
        self.instance.user = self._user
        return super().save(commit=commit)

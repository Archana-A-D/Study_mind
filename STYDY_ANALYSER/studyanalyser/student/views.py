from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings as django_settings
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Avg
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import StudySession, Subject, Assignment
from .chat_local import build_user_context, try_answer_locally
from .forms import (
    AddAssignmentForm,
    AddSubjectForm,
    AssignmentModelForm,
    LoginForm,
    LogSessionForm,
    MarkDoneForm,
    OnboardingForm,
    RegisterForm,
    StudySessionModelForm,
    SubjectModelForm,
)
from .gemini_client import get_response

def index(request):
    return render(request, 'student/index.html')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('onboarding')
        return render(request, 'student/register.html', {'form': form})

    return render(request, 'student/register.html', {'form': RegisterForm()})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST, request=request)
        if form.is_valid() and form.user is not None:
            user = form.user
            auth_login(request, user)
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
            if not Subject.objects.filter(user=user).exists():
                return redirect('onboarding')
            return redirect('user_dashboard')
        return render(request, 'student/login.html', {'form': form})

    return render(request, 'student/login.html', {'form': LoginForm()})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required(login_url='login')
def onboarding_view(request):
    if request.method == 'POST':
        form = OnboardingForm(request.POST)
        if form.is_valid():
            for name in form.cleaned_data["subjects"]:
                Subject.objects.get_or_create(user=request.user, name=name)

            title = (form.cleaned_data.get("assignment_title") or "").strip()
            subject_name = (form.cleaned_data.get("assignment_subject") or "").strip()
            deadline = form.cleaned_data.get("assignment_deadline")
            estimated_hours = form.cleaned_data.get("estimated_hours")
            if title and subject_name and deadline:
                subj, _ = Subject.objects.get_or_create(user=request.user, name=subject_name)
                Assignment.objects.create(
                    user=request.user,
                    subject=subj,
                    title=title,
                    deadline=deadline,
                    estimated_hours=float(estimated_hours or 2.0),
                )

            messages.success(request, 'Onboarding complete! Welcome to your personal study analyzer.')
            return redirect('user_dashboard')

        return render(request, 'student/onboarding.html', {'form': form})

    return render(request, 'student/onboarding.html', {'form': OnboardingForm()})

def generate_study_plan(user):
    timeline = []
    alerts = []
    
    now_date = timezone.now().date()
    urgent_assignments = list(Assignment.objects.filter(
        user=user, 
        is_completed=False,
        deadline__lte=now_date + timezone.timedelta(days=3)
    ).order_by('deadline')[:2])
    
    urgent_subject_ids = [a.subject_id for a in urgent_assignments]
    
    sessions = StudySession.objects.filter(user=user)
    stats_dict = {}
    if sessions.exists():
        for stat in sessions.filter(subject__isnull=False).values('subject_id').annotate(avg_focus=Avg('focus_level')):
            stats_dict[stat['subject_id']] = stat['avg_focus']
            
    subjects = Subject.objects.filter(user=user)
    
    subjects_to_schedule = []
    for subj in subjects:
        if subj.id not in urgent_subject_ids:
            subjects_to_schedule.append((subj, stats_dict.get(subj.id, 50)))
            
    subjects_to_schedule.sort(key=lambda x: x[1]) # Sort by lowest focus
    
    colors = [('#EE5D50', '#FEECEB'), ('#FFB547', '#FFF4E5'), ('#4318FF', '#F4F7FE'), ('#05CD99', '#E6F8ED'), ('#020220', '#EAEAEA'), ('#7B61FF', '#F4F2FF')]
    time_slots = ['09:00 AM - 11:00 AM', '11:30 AM - 01:30 PM', '02:30 PM - 04:30 PM', '05:00 PM - 07:00 PM', '07:30 PM - 09:30 PM', '09:30 PM - 10:30 PM']
    
    for a in urgent_assignments:
        alerts.append(f"⚠️ {a.title} ({a.subject.name}) is due on {a.deadline}! We've prioritized it in your schedule.")
        c, bg = colors.pop(0) if colors else ('#4318FF', '#F4F7FE')
        t = time_slots.pop(0) if time_slots else 'Late Night'
        
        logged_hours = StudySession.objects.filter(assignment=a).aggregate(Sum('duration'))['duration__sum'] or 0
        remaining = max(0, a.estimated_hours - logged_hours)
        
        timeline.append({
            'color': c, 'bg_color': bg,
            'time': t,
            'title': f"Urgent: {a.title}",
            'reason': f"Due on {a.deadline}. You have ~{remaining} estimated hours left to complete this.",
            'assignment_id': a.id
        })
        
    for subj, avg_focus in subjects_to_schedule:
        if not time_slots: break 
        
        c, bg = colors.pop(0) if colors else ('#4318FF', '#F4F7FE')
        t = time_slots.pop(0)
        
        if avg_focus < 50:
            title = f"Deep Work: {subj.name}"
            reason = f"Based on lower past focus ({int(avg_focus)}%). Let's dedicate some deep work."
        elif avg_focus >= 80:
            title = f"Review: {subj.name}"
            reason = f"You are doing great here ({int(avg_focus)}%). A quick review to stay sharp."
        else:
            title = f"Standard Study: {subj.name}"
            reason = f"Steady progress ({int(avg_focus)}%). Keep the momentum going!"
            
        timeline.append({
            'color': c, 'bg_color': bg,
            'time': t,
            'title': title,
            'reason': reason
        })
        
    if not timeline:
        insight = "Welcome! Add subjects or assignments to generate a personalized timetable."
    elif urgent_assignments:
        insight = "AI Insight: We have prioritized your upcoming deadlines to ensure you stay on track."
    else:
        insight = "AI Insight: You have no immediate deadlines. Generating an optimal schedule exploring all your subjects based on historical focus metrics."
        
    return {'insight': insight, 'timeline': timeline, 'alerts': alerts}

@login_required(login_url='login')
def user_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'log_session')
        
        if action == 'mark_done':
            form = MarkDoneForm(request.POST, user=request.user)
            if form.is_valid():
                a = form.cleaned_data["assignment_id"]
                a.is_completed = True
                a.save(update_fields=["is_completed"])
                messages.success(request, f"Awesome! You completed {a.title}.")
            else:
                messages.error(request, "Could not mark assignment as done.")
            return redirect('/user_dashboard/#schedule')
            
        elif action == 'log_session':
            form = LogSessionForm(request.POST, user=request.user)
            if form.is_valid():
                subj = form.cleaned_data["subject_id"]
                StudySession.objects.create(
                    user=request.user,
                    subject=subj,
                    duration=form.cleaned_data["duration"],
                    focus_level=form.cleaned_data["focus_level"],
                )
                messages.success(request, 'Study session logged successfully!')
            else:
                messages.error(request, "Please enter valid session details.")
            return redirect('/user_dashboard/')
            
        elif action == 'generate_new_plan':
            messages.success(request, 'Plan regenerated successfully based on your latest activity and upcoming deadlines.')
            return redirect('/user_dashboard/#schedule')

        elif action == 'add_subject':
            form = AddSubjectForm(request.POST)
            if form.is_valid():
                subject_name = form.cleaned_data["subject_name"]
                Subject.objects.get_or_create(user=request.user, name=subject_name)
                messages.success(request, f"Successfully added new subject: {subject_name}")
            else:
                messages.error(request, "Please enter a valid subject name.")
            return redirect('/user_dashboard/#settings')
            
        elif action == 'add_assignment':
            form = AddAssignmentForm(request.POST, user=request.user)
            if form.is_valid():
                Assignment.objects.create(
                    user=request.user,
                    subject=form.cleaned_data["subject_id"],
                    title=form.cleaned_data["title"].strip(),
                    deadline=form.cleaned_data["deadline"],
                    estimated_hours=form.cleaned_data["estimated_hours"],
                )
                messages.success(
                    request,
                    f"Successfully added assignment '{form.cleaned_data['title']}'. Check your updated Schedule!",
                )
            else:
                messages.error(request, "Please enter valid assignment details.")
            return redirect('/user_dashboard/#schedule')
            
    sessions = StudySession.objects.filter(user=request.user).order_by('-created_at')
    
    total_hours = sessions.aggregate(Sum('duration'))['duration__sum'] or 0
    avg_focus = sessions.aggregate(Avg('focus_level'))['focus_level__avg'] or 0
    session_dates = list(
        sessions.values_list("created_at__date", flat=True).distinct().order_by("-created_at__date")
    )
    streak = 0
    if session_dates:
        today = timezone.localdate()
        expected = today if session_dates[0] == today else (today - timezone.timedelta(days=1))
        if session_dates[0] in (today, today - timezone.timedelta(days=1)):
            for d in session_dates:
                if d == expected:
                    streak += 1
                    expected = expected - timezone.timedelta(days=1)
                elif d < expected:
                    break
    
    subjects = Subject.objects.filter(user=request.user)
    ai_plan = generate_study_plan(request.user)
    
    context = {
        'sessions': sessions[:10],
        'total_hours': round(total_hours, 1),
        'avg_focus': round(avg_focus),
        'streak': streak,
        'ai_plan': ai_plan,
        'subjects': subjects
    }
    return render(request, 'student/user_dashboard.html', context)

@login_required(login_url='login')
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('user_dashboard')
        
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    total_users = users.count()
    sessions_qs = StudySession.objects.select_related("user", "subject", "assignment").order_by("-created_at")
    total_sessions = sessions_qs.count()
    active_today = StudySession.objects.filter(created_at__date=timezone.now().date()).values('user').distinct().count()

    platform_settings = {
        "DEBUG": django_settings.DEBUG,
        "TIME_ZONE": django_settings.TIME_ZONE,
        "DATABASE_ENGINE": django_settings.DATABASES.get("default", {}).get("ENGINE"),
        "ALLOWED_HOSTS": ", ".join(django_settings.ALLOWED_HOSTS),
    }
    
    context = {
        'total_users': total_users,
        'active_today': active_today,
        'total_sessions': total_sessions,
        'recent_users': users[:10],
        'users': users[:200],
        'sessions': sessions_qs[:200],
        'platform_settings': platform_settings,
    }
    return render(request, 'student/admin_dashboard.html', context)


@require_POST
@login_required(login_url="login")
def chat_api(request):
    user_prompt = (request.POST.get("prompt") or "").strip()
    if not user_prompt:
        return JsonResponse({"error": "No prompt provided"}, status=400)

    history = request.session.get("chat_history", [])
    if not isinstance(history, list):
        history = []

    # Keep the session small and fast.
    history = history[-20:]

    local = try_answer_locally(user_prompt, request.user)
    if local.handled:
        if local.clear_history:
            request.session["chat_history"] = []
            request.session.modified = True
        return JsonResponse({"response": local.response})

    try:
        system_prompt = build_user_context(request.user)
        response_text = get_response(user_prompt, history, system_prompt=system_prompt)
        history.append({"role": "user", "parts": [{"text": user_prompt}]})
        history.append({"role": "model", "parts": [{"text": response_text}]})
        request.session["chat_history"] = history[-20:]
        request.session.modified = True
        return JsonResponse({"response": response_text})
    except Exception as e:
        return JsonResponse({"response": f"Error: {str(e)}"}, status=200)


@login_required(login_url="login")
def manage_subjects(request):
    if request.method == "POST":
        form = SubjectModelForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject saved.")
            return redirect("manage_subjects")
        messages.error(request, "Please correct the errors below.")
    else:
        form = SubjectModelForm(user=request.user)

    subjects = Subject.objects.filter(user=request.user).order_by("name")
    return render(request, "student/manage/subjects.html", {"form": form, "subjects": subjects})


@login_required(login_url="login")
def edit_subject(request, subject_id: int):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    if request.method == "POST":
        form = SubjectModelForm(request.POST, instance=subject, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject updated.")
            return redirect("manage_subjects")
        messages.error(request, "Please correct the errors below.")
    else:
        form = SubjectModelForm(instance=subject, user=request.user)
    return render(request, "student/manage/subject_edit.html", {"form": form, "subject": subject})


@login_required(login_url="login")
def delete_subject(request, subject_id: int):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted.")
        return redirect("manage_subjects")
    return render(request, "student/manage/subject_delete.html", {"subject": subject})


@login_required(login_url="login")
def manage_assignments(request):
    if request.method == "POST":
        form = AssignmentModelForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment saved.")
            return redirect("manage_assignments")
        messages.error(request, "Please correct the errors below.")
    else:
        form = AssignmentModelForm(user=request.user)

    assignments = (
        Assignment.objects.filter(user=request.user)
        .select_related("subject")
        .order_by("is_completed", "deadline", "created_at")
    )
    return render(
        request,
        "student/manage/assignments.html",
        {"form": form, "assignments": assignments},
    )


@login_required(login_url="login")
def edit_assignment(request, assignment_id: int):
    assignment = get_object_or_404(Assignment, id=assignment_id, user=request.user)
    if request.method == "POST":
        form = AssignmentModelForm(request.POST, instance=assignment, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated.")
            return redirect("manage_assignments")
        messages.error(request, "Please correct the errors below.")
    else:
        form = AssignmentModelForm(instance=assignment, user=request.user)
    return render(
        request,
        "student/manage/assignment_edit.html",
        {"form": form, "assignment": assignment},
    )


@login_required(login_url="login")
def delete_assignment(request, assignment_id: int):
    assignment = get_object_or_404(Assignment, id=assignment_id, user=request.user)
    if request.method == "POST":
        assignment.delete()
        messages.success(request, "Assignment deleted.")
        return redirect("manage_assignments")
    return render(
        request,
        "student/manage/assignment_delete.html",
        {"assignment": assignment},
    )


@login_required(login_url="login")
def manage_sessions(request):
    if request.method == "POST":
        form = StudySessionModelForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Study session saved.")
            return redirect("manage_sessions")
        messages.error(request, "Please correct the errors below.")
    else:
        form = StudySessionModelForm(user=request.user)

    sessions = (
        StudySession.objects.filter(user=request.user)
        .select_related("subject", "assignment")
        .order_by("-created_at")
    )
    return render(request, "student/manage/sessions.html", {"form": form, "sessions": sessions})


@login_required(login_url="login")
def delete_session(request, session_id: int):
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    if request.method == "POST":
        session.delete()
        messages.success(request, "Study session deleted.")
        return redirect("manage_sessions")
    return render(request, "student/manage/session_delete.html", {"session": session})

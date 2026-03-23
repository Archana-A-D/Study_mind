from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db.models import Avg, Sum
from django.utils import timezone

from .models import Assignment, StudySession, Subject


@dataclass(frozen=True)
class LocalChatResult:
    handled: bool
    response: str = ""
    clear_history: bool = False


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _compute_streak(session_dates: list) -> int:
    streak = 0
    if not session_dates:
        return 0

    today = timezone.localdate()
    expected = today if session_dates[0] == today else (today - timezone.timedelta(days=1))
    if session_dates[0] not in (today, today - timezone.timedelta(days=1)):
        return 0

    for d in session_dates:
        if d == expected:
            streak += 1
            expected = expected - timezone.timedelta(days=1)
        elif d < expected:
            break
    return streak


def try_answer_locally(prompt: str, user: User) -> LocalChatResult:
    q = _normalize(prompt)
    if not q:
        return LocalChatResult(handled=True, response="Please type a question.")

    if q in {"/reset", "reset", "reset chat", "clear chat", "clear history"} or "reset chat" in q or "clear chat" in q:
        return LocalChatResult(handled=True, response="Chat history cleared.", clear_history=True)

    if ("assignment" in q or "assignments" in q) and (
        ("how many" in q and ("left" in q or "pending" in q or "remaining" in q or "incomplete" in q))
        or ("count" in q and ("pending" in q or "left" in q or "remaining" in q))
    ):
        pending = Assignment.objects.filter(user=user, is_completed=False).count()
        return LocalChatResult(handled=True, response=f"You have {pending} pending assignment(s).")

    if ("assignment" in q or "assignments" in q) and any(w in q for w in ["list", "show", "display"]) and any(
        w in q for w in ["pending", "left", "remaining", "incomplete", "not completed"]
    ):
        pending_qs = (
            Assignment.objects.filter(user=user, is_completed=False)
            .select_related("subject")
            .order_by("deadline", "created_at")
        )
        items = list(pending_qs[:10])
        if not items:
            return LocalChatResult(handled=True, response="You have no pending assignments.")
        lines = ["Here are your pending assignments (up to 10):"]
        for a in items:
            lines.append(f"- {a.title} ({a.subject.name}) due {a.deadline:%Y-%m-%d}")
        if pending_qs.count() > len(items):
            lines.append("…and more.")
        return LocalChatResult(handled=True, response="\n".join(lines))

    if ("assignment" in q or "deadline" in q) and any(w in q for w in ["next", "closest", "soonest", "upcoming"]):
        a = (
            Assignment.objects.filter(user=user, is_completed=False)
            .select_related("subject")
            .order_by("deadline", "created_at")
            .first()
        )
        if not a:
            return LocalChatResult(handled=True, response="You have no pending assignments, so no upcoming deadlines.")
        return LocalChatResult(
            handled=True,
            response=f"Next deadline: {a.title} ({a.subject.name}) due {a.deadline:%Y-%m-%d}.",
        )

    if ("subject" in q or "subjects" in q) and ("how many" in q or "count" in q):
        n = Subject.objects.filter(user=user).count()
        return LocalChatResult(handled=True, response=f"You have {n} subject(s).")

    if ("total" in q and "hour" in q) or "hours studied" in q or "how many hours" in q:
        total_hours = (
            StudySession.objects.filter(user=user).aggregate(total=Sum("duration")).get("total") or 0
        )
        return LocalChatResult(handled=True, response=f"Total study time logged: {round(float(total_hours), 1)} hours.")

    if "average focus" in q or ("avg" in q and "focus" in q):
        avg_focus = StudySession.objects.filter(user=user).aggregate(avg=Avg("focus_level")).get("avg")
        if avg_focus is None:
            return LocalChatResult(handled=True, response="No sessions yet, so average focus is not available.")
        return LocalChatResult(handled=True, response=f"Average focus: {round(float(avg_focus))}%.")

    if "streak" in q:
        sessions = StudySession.objects.filter(user=user).order_by("-created_at")
        session_dates = list(
            sessions.values_list("created_at__date", flat=True).distinct().order_by("-created_at__date")
        )
        streak = _compute_streak(session_dates)
        return LocalChatResult(handled=True, response=f"Current streak: {streak} day(s).")

    return LocalChatResult(handled=False)


def build_user_context(user: User) -> str:
    pending = Assignment.objects.filter(user=user, is_completed=False).count()
    total_hours = StudySession.objects.filter(user=user).aggregate(total=Sum("duration")).get("total") or 0
    avg_focus = StudySession.objects.filter(user=user).aggregate(avg=Avg("focus_level")).get("avg")
    avg_focus_text = "-" if avg_focus is None else f"{round(float(avg_focus))}%"

    upcoming = (
        Assignment.objects.filter(user=user, is_completed=False)
        .select_related("subject")
        .order_by("deadline", "created_at")
        .first()
    )
    if upcoming:
        upcoming_text = f"{upcoming.title} ({upcoming.subject.name}) due {upcoming.deadline:%Y-%m-%d}"
    else:
        upcoming_text = "-"

    return (
        "You are StudyMind Chat for this web app. "
        "Answer clearly and briefly. "
        "If the user asks about their data, use these facts:\n"
        f"- Pending assignments: {pending}\n"
        f"- Upcoming deadline: {upcoming_text}\n"
        f"- Total study hours: {round(float(total_hours), 1)}\n"
        f"- Average focus: {avg_focus_text}\n"
    )


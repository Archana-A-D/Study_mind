from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Assignment, StudySession, Subject


class AuthFlowTests(TestCase):
    def test_register_login_logout(self):
        c = Client()
        register_url = reverse("register")
        resp = c.post(
            register_url,
            {
                "first_name": "A",
                "last_name": "B",
                "email": "a@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(username="a@example.com").exists())

        c.get(reverse("logout"), follow=True)
        login_url = reverse("login")
        resp = c.post(login_url, {"email": "a@example.com", "password": "StrongPass123!"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.wsgi_request.user.is_authenticated)


class ManagePagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u@example.com", email="u@example.com", password="StrongPass123!"
        )
        self.client.force_login(self.user)

    def test_subject_unique_per_user(self):
        Subject.objects.create(user=self.user, name="Math")
        resp = self.client.post(reverse("manage_subjects"), {"name": "Math"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Subject.objects.filter(user=self.user, name__iexact="Math").count(), 1)

    def test_assignment_crud_pages_load(self):
        subj = Subject.objects.create(user=self.user, name="Physics")
        resp = self.client.get(reverse("manage_assignments"))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("manage_assignments"),
            {
                "subject": subj.id,
                "title": "HW 1",
                "deadline": (date.today() + timedelta(days=7)).isoformat(),
                "estimated_hours": "2.5",
                "is_completed": "",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        a = Assignment.objects.get(user=self.user, title="HW 1")

        resp = self.client.get(reverse("edit_assignment", args=[a.id]))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("edit_assignment", args=[a.id]),
            {
                "subject": subj.id,
                "title": "HW 1 updated",
                "deadline": (date.today() + timedelta(days=8)).isoformat(),
                "estimated_hours": "3.0",
                "is_completed": "on",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.title, "HW 1 updated")
        self.assertTrue(a.is_completed)

    def test_sessions_crud_pages_load(self):
        subj = Subject.objects.create(user=self.user, name="Chem")
        resp = self.client.get(reverse("manage_sessions"))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("manage_sessions"),
            {"subject": subj.id, "assignment": "", "duration": "1.5", "focus_level": "85"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(StudySession.objects.filter(user=self.user).count(), 1)

    def test_dashboard_streak_counts_consecutive_days(self):
        subj = Subject.objects.create(user=self.user, name="Bio")
        StudySession.objects.create(user=self.user, subject=subj, duration=1.0, focus_level=80)
        StudySession.objects.create(user=self.user, subject=subj, duration=1.0, focus_level=80)
        yesterday = timezone.now() - timezone.timedelta(days=1)
        old = StudySession.objects.create(user=self.user, subject=subj, duration=1.0, focus_level=80)
        StudySession.objects.filter(pk=old.pk).update(created_at=yesterday)

        resp = self.client.get(reverse("user_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("streak", resp.context)
        self.assertGreaterEqual(resp.context["streak"], 1)

    def test_chat_api_answers_assignment_count_locally(self):
        subj = Subject.objects.create(user=self.user, name="Math")
        Assignment.objects.create(
            user=self.user,
            subject=subj,
            title="A1",
            deadline=date.today() + timedelta(days=3),
            estimated_hours=2.0,
            is_completed=False,
        )
        Assignment.objects.create(
            user=self.user,
            subject=subj,
            title="A2",
            deadline=date.today() + timedelta(days=5),
            estimated_hours=1.5,
            is_completed=False,
        )

        resp = self.client.post(reverse("chat_api"), {"prompt": "How many assignments left?"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("2", resp.json().get("response", ""))

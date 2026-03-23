from django.urls import path
from .views import index, register, login_view, logout_view
from .views import user_dashboard, admin_dashboard, onboarding_view
from .views import chat_api
from .views import (
    manage_subjects,
    edit_subject,
    delete_subject,
    manage_assignments,
    edit_assignment,
    delete_assignment,
    manage_sessions,
    delete_session,
)

urlpatterns = [
    path('', index, name='index'),
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('onboarding/', onboarding_view, name='onboarding'),
    path('user_dashboard/', user_dashboard, name='user_dashboard'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path("api/chat/", chat_api, name="chat_api"),

    path("manage/subjects/", manage_subjects, name="manage_subjects"),
    path("manage/subjects/<int:subject_id>/edit/", edit_subject, name="edit_subject"),
    path("manage/subjects/<int:subject_id>/delete/", delete_subject, name="delete_subject"),

    path("manage/assignments/", manage_assignments, name="manage_assignments"),
    path("manage/assignments/<int:assignment_id>/edit/", edit_assignment, name="edit_assignment"),
    path("manage/assignments/<int:assignment_id>/delete/", delete_assignment, name="delete_assignment"),

    path("manage/sessions/", manage_sessions, name="manage_sessions"),
    path("manage/sessions/<int:session_id>/delete/", delete_session, name="delete_session"),
]

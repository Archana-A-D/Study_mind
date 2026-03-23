from django.contrib import admin

from .models import Assignment, StudySession, Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    list_filter = ("user",)
    search_fields = ("name", "user__username", "user__email")
    ordering = ("name",)
    raw_id_fields = ("user",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "user",
        "deadline",
        "estimated_hours",
        "is_completed",
        "created_at",
    )
    list_filter = ("is_completed", "deadline", "subject", "user")
    search_fields = ("title", "subject__name", "user__username", "user__email")
    ordering = ("-deadline", "-created_at")
    date_hierarchy = "deadline"
    raw_id_fields = ("user",)


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "subject_or_legacy", "assignment", "duration", "focus_level", "created_at")
    list_filter = ("subject", "assignment", "user", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "subject__name",
        "legacy_subject",
        "assignment__title",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    raw_id_fields = ("user",)

    @admin.display(description="Subject")
    def subject_or_legacy(self, obj: StudySession):
        if obj.subject_id:
            return obj.subject.name
        return obj.legacy_subject or "-"

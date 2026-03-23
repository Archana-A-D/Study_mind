from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

# Create your models here.
class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_subject_user_name"),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class Assignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    deadline = models.DateField()
    estimated_hours = models.FloatField(default=1.0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "deadline"]),
            models.Index(fields=["user", "is_completed", "deadline"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True, blank=True)
    # Keeping a string fallback just in case old data exists before migration
    legacy_subject = models.CharField(max_length=100, null=True, blank=True)
    duration = models.FloatField(help_text="Duration in hours")
    focus_level = models.IntegerField(help_text="Focus level percentage (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(duration__gt=0), name="chk_studysession_duration_gt0"),
            models.CheckConstraint(
                condition=Q(focus_level__gte=0) & Q(focus_level__lte=100),
                name="chk_focus_0_100",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        sub_name = self.subject.name if self.subject else self.legacy_subject
        return f"{self.user.username} - {sub_name} ({self.duration}h)"

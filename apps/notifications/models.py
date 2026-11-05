from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Kind(models.TextChoices):
        CONSULTATION_ASSIGNED = "CONSULTATION_ASSIGNED", "Consultation assigned"
        CONSULTATION_MESSAGE = "CONSULTATION_MESSAGE", "Consultation message"
        EXPERT_REPLIED = "EXPERT_REPLIED", "Expert replied"
        CONSULTATION_UPDATED = "CONSULTATION_UPDATED", "Consultation updated"
        EXPERT_APPROVED = "EXPERT_APPROVED", "Agriculturalist approved"
        EXPERT_REJECTED = "EXPERT_REJECTED", "Agriculturalist rejected"
        NEW_RECOMMENDATION = "NEW_RECOMMENDATION", "New recommendation"
        WEATHER_ALERT = "WEATHER_ALERT", "Weather alert"
        SUPPORT_UPDATED = "SUPPORT_UPDATED", "Support ticket updated"
        CONTENT_APPROVED = "CONTENT_APPROVED", "Learning content approved"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.SYSTEM, db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True, max_length=1000)
    target_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at", "-created_at"])]

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])

    def __str__(self):
        return self.title

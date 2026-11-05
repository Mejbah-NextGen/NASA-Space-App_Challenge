from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        DENIED = "DENIED", "Denied"
        FAILED = "FAILED", "Failed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120, db_index=True)
    target_type = models.CharField(max_length=80, blank=True)
    target_identifier = models.CharField(max_length=160, blank=True)
    result = models.CharField(max_length=12, choices=Result.choices, default=Result.SUCCESS, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "created_at"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} - {self.action}"

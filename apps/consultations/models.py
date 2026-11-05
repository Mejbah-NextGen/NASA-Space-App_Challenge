from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.accounts.validators import validate_profile_image


class Consultation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        DECLINED = "DECLINED", "Declined"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farmer_consultations")
    agriculturalist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expert_consultations",
    )
    farm = models.ForeignKey("farms.Farm", on_delete=models.SET_NULL, null=True, blank=True, related_name="consultations")
    title = models.CharField(max_length=180)
    description = models.TextField(max_length=4000)
    image = models.ImageField(upload_to="consultations/%Y/%m/", blank=True, validators=[validate_profile_image])
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["farmer", "status"]),
            models.Index(fields=["agriculturalist", "status"]),
        ]

    def clean(self):
        if self.farmer_id and self.farmer.role != "FARMER":
            raise ValidationError({"farmer": "The requester must have the Farmer role."})
        if self.agriculturalist_id:
            if self.agriculturalist.role != "AGRICULTURALIST":
                raise ValidationError({"agriculturalist": "The selected expert is not an Agriculturalist."})
            profile = getattr(self.agriculturalist, "agriculturalist_profile", None)
            if not profile or not profile.is_approved:
                raise ValidationError({"agriculturalist": "The selected Agriculturalist is not approved."})
        if self.farm_id and self.farmer_id and self.farm.owner_id != self.farmer_id:
            raise ValidationError({"farm": "You can only share a farm that belongs to the requester."})

    def close(self, status=Status.COMPLETED):
        if status not in {self.Status.COMPLETED, self.Status.CANCELLED, self.Status.DECLINED}:
            raise ValueError("A consultation can only be closed with a terminal status")
        self.status = status
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at", "updated_at"])

    def __str__(self):
        return self.title


class ExpertAssignment(models.Model):
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name="assignment")
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expert_assignments")
    agriculturalist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farmer_assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_made",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [models.Index(fields=["agriculturalist", "is_active"])]

    def clean(self):
        if self.consultation_id:
            if self.consultation.farmer_id != self.farmer_id:
                raise ValidationError("Assignment farmer must match the consultation requester.")
            if self.consultation.agriculturalist_id != self.agriculturalist_id:
                raise ValidationError("Assignment expert must match the consultation expert.")

    def __str__(self):
        return f"{self.farmer} -> {self.agriculturalist}"


class ConsultationMessage(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consultation_messages")
    body = models.TextField(max_length=4000)
    attachment = models.ImageField(upload_to="consultation_messages/%Y/%m/", blank=True, validators=[validate_profile_image])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        if self.consultation_id and self.sender_id not in {
            self.consultation.farmer_id,
            self.consultation.agriculturalist_id,
        }:
            raise ValidationError({"sender": "Only consultation participants may send messages."})


class ExpertRecommendation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    class Priority(models.TextChoices):
        INFO = "INFO", "Information"
        WATCH = "WATCH", "Watch"
        HIGH = "HIGH", "High"

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="recommendations")
    agriculturalist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    title = models.CharField(max_length=180)
    explanation = models.TextField(max_length=5000)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.INFO)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.consultation_id and self.consultation.agriculturalist_id != self.agriculturalist_id:
            raise ValidationError("Only the assigned Agriculturalist may provide a recommendation.")

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class FarmDataConsent(models.Model):
    class Scope(models.TextChoices):
        SUMMARY = "SUMMARY", "Farm summary"
        FULL = "FULL", "Farm and field details"

    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name="data_consent")
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farm_data_consents")
    agriculturalist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_consents")
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="data_consents")
    scope = models.CharField(max_length=12, choices=Scope.choices, default=Scope.SUMMARY)
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-granted_at"]

    @property
    def is_active(self):
        return self.revoked_at is None

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def clean(self):
        if self.consultation_id:
            if self.consultation.farmer_id != self.farmer_id:
                raise ValidationError("Consent farmer must match the consultation requester.")
            if self.consultation.agriculturalist_id != self.agriculturalist_id:
                raise ValidationError("Consent expert must match the assigned Agriculturalist.")
        if self.farm_id and self.farm.owner_id != self.farmer_id:
            raise ValidationError("Consent can only be granted for the farmer's own farm.")

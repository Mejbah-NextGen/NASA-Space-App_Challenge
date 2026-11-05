from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.farms.models import CropPlanting, Farm, Field
from apps.simulations.models import SimulationScenario


class FarmingDecision(models.Model):
    class DecisionType(models.TextChoices):
        PLANTING = "PLANTING", "Planting"
        IRRIGATION = "IRRIGATION", "Irrigation"
        CROP_CHANGE = "CROP_CHANGE", "Crop change"
        FERTILIZER = "FERTILIZER", "Fertilizer"
        HARVEST = "HARVEST", "Harvest"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        COMPLETED = "COMPLETED", "Completed"
        REVIEWED = "REVIEWED", "Reviewed"
        CANCELLED = "CANCELLED", "Cancelled"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farming_decisions")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="decisions")
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True, related_name="decisions")
    planting = models.ForeignKey(CropPlanting, on_delete=models.SET_NULL, null=True, blank=True, related_name="decisions")
    simulation = models.ForeignKey(SimulationScenario, on_delete=models.SET_NULL, null=True, blank=True, related_name="decisions")
    decision_type = models.CharField(max_length=20, choices=DecisionType.choices, db_index=True)
    title = models.CharField(max_length=180)
    decision_date = models.DateField(db_index=True)
    details = models.TextField(max_length=3000)
    rationale = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-decision_date", "-created_at"]
        indexes = [models.Index(fields=["owner", "decision_type", "decision_date"])]

    def clean(self):
        if self.farm_id and self.owner_id and self.farm.owner_id != self.owner_id:
            raise ValidationError({"farm": "The selected farm does not belong to this farmer."})
        if self.field_id and self.field.farm_id != self.farm_id:
            raise ValidationError({"field": "The selected field does not belong to this farm."})
        if self.planting_id and self.planting.field.farm_id != self.farm_id:
            raise ValidationError({"planting": "The selected crop record does not belong to this farm."})
        if self.simulation_id and self.simulation.owner_id != self.owner_id:
            raise ValidationError({"simulation": "The selected simulation does not belong to this farmer."})

    def __str__(self):
        return self.title


class DecisionOutcome(models.Model):
    decision = models.OneToOneField(FarmingDecision, on_delete=models.CASCADE, related_name="outcome")
    observed_date = models.DateField()
    outcome = models.TextField(max_length=3000)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    yield_impact = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-observed_date"]

    def clean(self):
        if self.decision_id and self.observed_date < self.decision.decision_date:
            raise ValidationError({"observed_date": "An outcome cannot be observed before the decision date."})

    def __str__(self):
        return f"Outcome: {self.decision.title}"


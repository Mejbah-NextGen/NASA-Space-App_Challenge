from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.farms.models import Crop, Farm, Field


class SimulationScenario(models.Model):
    class IrrigationScenario(models.TextChoices):
        NONE = "NONE", "No irrigation"
        LOW = "LOW", "Limited irrigation"
        MODERATE = "MODERATE", "Moderate irrigation"
        HIGH = "HIGH", "Reliable irrigation"

    class Season(models.TextChoices):
        AMAN = "AMAN", "Aman / monsoon"
        BORO = "BORO", "Boro / dry season"
        AUS = "AUS", "Aus / pre-monsoon"
        RABI = "RABI", "Rabi / winter"
        OTHER = "OTHER", "Other"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="simulation_scenarios")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="simulation_scenarios")
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True, related_name="simulation_scenarios")
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="simulation_scenarios")
    name = models.CharField(max_length=180)
    planting_date = models.DateField()
    temperature_assumption = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(Decimal("-10")), MaxValueValidator(Decimal("60"))])
    rainfall_assumption = models.DecimalField(max_digits=8, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(Decimal("5000"))])
    irrigation_scenario = models.CharField(max_length=16, choices=IrrigationScenario.choices, default=IrrigationScenario.MODERATE)
    historical_year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1980), MaxValueValidator(2100)])
    season = models.CharField(max_length=12, choices=Season.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"])]

    def clean(self):
        if self.farm_id and self.owner_id and self.farm.owner_id != self.owner_id:
            raise ValidationError({"farm": "The selected farm does not belong to this farmer."})
        if self.field_id and self.field.farm_id != self.farm_id:
            raise ValidationError({"field": "The selected field does not belong to this farm."})

    def __str__(self):
        return self.name


class SimulationResult(models.Model):
    scenario = models.OneToOneField(SimulationScenario, on_delete=models.CASCADE, related_name="result")
    estimated_suitability = models.DecimalField(max_digits=5, decimal_places=1)
    water_stress = models.DecimalField(max_digits=5, decimal_places=1)
    heat_stress = models.DecimalField(max_digits=5, decimal_places=1)
    overall_stress = models.DecimalField(max_digits=5, decimal_places=1)
    model_version = models.CharField(max_length=40, default="rule-baseline-1.0")
    summary = models.TextField(max_length=1200)
    disclaimer = models.TextField(default="Rule-based scenario illustration only. This is not a yield forecast or planting guarantee.")
    input_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.scenario.name}"


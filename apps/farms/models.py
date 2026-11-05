from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class AreaUnit(models.TextChoices):
    ACRE = "ACRE", "Acre"
    BIGHA = "BIGHA", "Bigha"
    KATHA = "KATHA", "Katha"
    DECIMAL = "DECIMAL", "Decimal / Shotangsho"
    HECTARE = "HECTARE", "Hectare"


class SoilType(models.TextChoices):
    LOAM = "LOAM", "Loam"
    CLAY = "CLAY", "Clay"
    SANDY = "SANDY", "Sandy"
    SILT = "SILT", "Silt"
    PEAT = "PEAT", "Peat"
    MIXED = "MIXED", "Mixed / Unknown"


class IrrigationType(models.TextChoices):
    RAINFED = "RAINFED", "Rain-fed"
    SURFACE = "SURFACE", "Surface irrigation"
    SPRINKLER = "SPRINKLER", "Sprinkler"
    DRIP = "DRIP", "Drip"
    PUMP = "PUMP", "Pump / shallow tube well"
    DEEP_TUBE = "DEEP_TUBE", "Deep tube well"
    OTHER = "OTHER", "Other"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Farm(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=140)
    district = models.CharField(max_length=80, db_index=True)
    upazila = models.CharField(max_length=80, blank=True)
    village = models.CharField(max_length=120, blank=True)
    land_area = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    area_unit = models.CharField(max_length=16, choices=AreaUnit.choices, default=AreaUnit.ACRE)
    soil_type = models.CharField(max_length=16, choices=SoilType.choices, default=SoilType.MIXED)
    irrigation_type = models.CharField(max_length=16, choices=IrrigationType.choices, default=IrrigationType.RAINFED)
    description = models.TextField(blank=True, max_length=2000)
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["is_archived", "name"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_farm_name_per_owner")]
        indexes = [models.Index(fields=["owner", "is_archived"])]

    def __str__(self):
        return self.name


class Field(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PREPARING = "PREPARING", "Preparing"
        FALLOW = "FALLOW", "Fallow"
        ARCHIVED = "ARCHIVED", "Archived"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=140)
    area = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    area_unit = models.CharField(max_length=16, choices=AreaUnit.choices, default=AreaUnit.ACRE)
    soil_type = models.CharField(max_length=16, choices=SoilType.choices, default=SoilType.MIXED)
    irrigation_type = models.CharField(max_length=16, choices=IrrigationType.choices, default=IrrigationType.RAINFED)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    description = models.TextField(blank=True, max_length=1200)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["farm", "name"], name="unique_field_name_per_farm")]

    def clean(self):
        if self.farm_id and self.area and self.area_unit == self.farm.area_unit and self.area > self.farm.land_area:
            raise ValidationError({"area": "A field cannot be larger than its farm when both use the same unit."})

    def __str__(self):
        return f"{self.farm.name} - {self.name}"


class Crop(TimeStampedModel):
    name = models.CharField(max_length=100)
    variety = models.CharField(max_length=120, blank=True, default="")
    is_supported = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "variety"]
        constraints = [models.UniqueConstraint(fields=["name", "variety"], name="unique_crop_variety")]

    def __str__(self):
        return f"{self.name} ({self.variety})" if self.variety else self.name


class CropPlanting(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        PLANTED = "PLANTED", "Planted"
        GROWING = "GROWING", "Growing"
        HARVESTED = "HARVESTED", "Harvested"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="plantings")
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="plantings")
    planting_date = models.DateField()
    expected_harvest_date = models.DateField(null=True, blank=True)
    actual_harvest_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED, db_index=True)
    notes = models.TextField(blank=True, max_length=2000)
    yield_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    yield_unit = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-planting_date", "-created_at"]
        indexes = [models.Index(fields=["field", "status", "planting_date"])]

    def clean(self):
        if self.expected_harvest_date and self.expected_harvest_date < self.planting_date:
            raise ValidationError({"expected_harvest_date": "Expected harvest cannot be before planting."})
        if self.actual_harvest_date and self.actual_harvest_date < self.planting_date:
            raise ValidationError({"actual_harvest_date": "Actual harvest cannot be before planting."})

    def __str__(self):
        return f"{self.crop} at {self.field}"


class FarmActivity(TimeStampedModel):
    class ActivityType(models.TextChoices):
        LAND_PREPARATION = "LAND_PREP", "Land preparation"
        PLANTING = "PLANTING", "Planting"
        IRRIGATION = "IRRIGATION", "Irrigation"
        FERTILIZER = "FERTILIZER", "Fertilizer"
        PEST_CONTROL = "PEST_CONTROL", "Pest or disease control"
        HARVEST = "HARVEST", "Harvest"
        OBSERVATION = "OBSERVATION", "Field observation"
        OTHER = "OTHER", "Other"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="activities")
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    planting = models.ForeignKey(CropPlanting, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices, db_index=True)
    activity_date = models.DateField(db_index=True)
    details = models.TextField(max_length=2000)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["-activity_date", "-created_at"]

    def clean(self):
        if self.field_id and self.farm_id and self.field.farm_id != self.farm_id:
            raise ValidationError({"field": "The selected field does not belong to this farm."})
        if self.planting_id and self.farm_id and self.planting.field.farm_id != self.farm_id:
            raise ValidationError({"planting": "The selected planting does not belong to this farm."})
        if self.planting_id and self.field_id and self.planting.field_id != self.field_id:
            raise ValidationError({"planting": "The selected planting does not belong to this field."})


class FarmTask(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="tasks")
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    title = models.CharField(max_length=180)
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    notes = models.TextField(blank=True, max_length=1200)

    class Meta:
        ordering = ["due_date", "-priority"]

    def clean(self):
        if self.field_id and self.farm_id and self.field.farm_id != self.farm_id:
            raise ValidationError({"field": "The selected field does not belong to this farm."})


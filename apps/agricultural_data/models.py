from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Region(models.Model):
    district = models.CharField(max_length=80, db_index=True)
    upazila = models.CharField(max_length=80, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["district", "upazila"]
        constraints = [
            models.UniqueConstraint(fields=["district", "upazila"], name="unique_region_district_upazila"),
        ]

    def __str__(self):
        return f"{self.upazila}, {self.district}" if self.upazila else self.district


class DataSource(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Weather"
        HISTORICAL_WEATHER = "HIST_WEATHER", "Historical weather"
        CROP = "CROP", "Crop production"
        SATELLITE = "SATELLITE", "Satellite"
        MANUAL = "MANUAL", "Manual submission"

    name = models.CharField(max_length=160, unique=True)
    provider = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    attribution = models.CharField(max_length=300, blank=True)
    geographic_coverage = models.CharField(max_length=300, blank=True)
    update_frequency = models.CharField(max_length=120, blank=True)
    limitations = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    last_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AgriculturalDataset(models.Model):
    class Status(models.TextChoices):
        SAMPLE = "SAMPLE", "Demonstration sample"
        VERIFIED = "VERIFIED", "Verified"
        REVIEW = "REVIEW", "Under review"
        FAILED = "FAILED", "Validation failed"

    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="datasets")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REVIEW, db_index=True)
    geographic_coverage = models.CharField(max_length=300, blank=True)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    units = models.CharField(max_length=120, blank=True)
    quality_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    @property
    def is_sample(self):
        return self.status == self.Status.SAMPLE or self.source.is_demo


class DataImportJob(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Historical weather"
        CROP = "CROP", "Historical crop production"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.CASCADE, related_name="import_jobs")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_import_jobs",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    rows_received = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename}: {self.get_status_display()}"


class HistoricalWeatherObservation(models.Model):
    class Quality(models.TextChoices):
        GOOD = "GOOD", "Good"
        ESTIMATED = "ESTIMATED", "Estimated"
        MISSING = "MISSING", "Missing fields"

    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.CASCADE, related_name="weather_observations")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="historical_weather")
    observed_on = models.DateField(db_index=True)
    rainfall_mm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    temperature_min_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperature_max_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperature_mean_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    quality_flag = models.CharField(max_length=16, choices=Quality.choices, default=Quality.GOOD)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["observed_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "region", "observed_on"],
                name="unique_historical_weather_observation",
            )
        ]
        indexes = [models.Index(fields=["region", "observed_on"])]

    def __str__(self):
        return f"{self.region} - {self.observed_on}"


class HistoricalCropObservation(models.Model):
    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.CASCADE, related_name="crop_observations")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="historical_crops")
    crop_name = models.CharField(max_length=100, db_index=True)
    variety = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(db_index=True, validators=[MinValueValidator(1900), MaxValueValidator(2200)])
    season = models.CharField(max_length=80, blank=True)
    cultivated_area_hectares = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    production_tonnes = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    yield_tonnes_per_hectare = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    quality_notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["year", "crop_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "region", "crop_name", "variety", "year", "season"],
                name="unique_historical_crop_observation",
            )
        ]
        indexes = [models.Index(fields=["region", "crop_name", "year"])]

    def __str__(self):
        return f"{self.crop_name}, {self.region} ({self.year})"

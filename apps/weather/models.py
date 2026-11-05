from django.db import models

from apps.agricultural_data.models import DataSource, Region


class WeatherObservation(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="weather_observations")
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="weather_observations")
    observed_at = models.DateTimeField(db_index=True)
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rainfall_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    wind_speed_kmh = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=120, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        constraints = [
            models.UniqueConstraint(fields=["region", "source", "observed_at"], name="unique_weather_observation")
        ]


class WeatherForecast(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="weather_forecasts")
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="weather_forecasts")
    forecast_for = models.DateField(db_index=True)
    temperature_min_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperature_max_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    precipitation_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    rainfall_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=120, blank=True)
    issued_at = models.DateTimeField()
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["forecast_for"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "source", "forecast_for", "issued_at"],
                name="unique_weather_forecast",
            )
        ]


class WeatherAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        WATCH = "WATCH", "Watch"
        WARNING = "WARNING", "Warning"
        EMERGENCY = "EMERGENCY", "Emergency"

    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="weather_alerts")
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="weather_alerts")
    title = models.CharField(max_length=180)
    description = models.TextField()
    recommendation = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.INFO, db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-severity", "-starts_at"]

    def __str__(self):
        return self.title

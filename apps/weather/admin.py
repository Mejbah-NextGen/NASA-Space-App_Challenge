from django.contrib import admin

from .models import WeatherAlert, WeatherForecast, WeatherObservation


@admin.register(WeatherAlert)
class WeatherAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "region", "severity", "starts_at", "ends_at", "is_active")
    list_filter = ("severity", "is_active")
    search_fields = ("title", "description", "region__district")


admin.site.register(WeatherObservation)
admin.site.register(WeatherForecast)

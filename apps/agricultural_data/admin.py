from django.contrib import admin

from .models import (
    AgriculturalDataset,
    DataImportJob,
    DataSource,
    HistoricalCropObservation,
    HistoricalWeatherObservation,
    Region,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_demo", "is_active", "last_updated_at")
    list_filter = ("kind", "is_demo", "is_active")
    search_fields = ("name", "provider", "geographic_coverage")


@admin.register(AgriculturalDataset)
class AgriculturalDatasetAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "status", "date_start", "date_end", "updated_at")
    list_filter = ("status", "source")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(DataImportJob)
class DataImportJobAdmin(admin.ModelAdmin):
    list_display = ("filename", "dataset", "kind", "status", "rows_imported", "created_at")
    list_filter = ("kind", "status")
    readonly_fields = ("errors", "started_at", "completed_at", "created_at")


admin.site.register(Region)
admin.site.register(HistoricalWeatherObservation)
admin.site.register(HistoricalCropObservation)

from django.contrib import admin

from .models import (
    AgriculturalDataset,
    CropDisease,
    DataImportJob,
    DataSource,
    DiseaseGuidance,
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


class DiseaseGuidanceInline(admin.TabularInline):
    model = DiseaseGuidance
    extra = 0
    fields = ("information_type", "category", "content", "source_row")
    readonly_fields = ("information_type", "category", "content", "source_row")
    can_delete = False
    max_num = 0


@admin.register(CropDisease)
class CropDiseaseAdmin(admin.ModelAdmin):
    list_display = ("crop_name", "disease_name", "dataset")
    list_filter = ("crop_name", "dataset")
    search_fields = ("crop_name", "disease_name", "guidance_entries__content")
    inlines = (DiseaseGuidanceInline,)


@admin.register(DiseaseGuidance)
class DiseaseGuidanceAdmin(admin.ModelAdmin):
    list_display = ("disease", "information_type", "category", "source_row")
    list_filter = ("category", "disease__crop_name")
    search_fields = ("disease__crop_name", "disease__disease_name", "information_type", "content")
    readonly_fields = ("content_hash", "source_row")

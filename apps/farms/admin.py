from django.contrib import admin

from .models import Crop, CropPlanting, Farm, FarmActivity, FarmTask, Field


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "district", "land_area", "area_unit", "is_archived")
    list_filter = ("district", "soil_type", "irrigation_type", "is_archived")
    search_fields = ("name", "owner__email", "district", "upazila")


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ("name", "farm", "area", "area_unit", "status")
    list_filter = ("status", "soil_type", "irrigation_type")


admin.site.register(Crop)
admin.site.register(CropPlanting)
admin.site.register(FarmActivity)
admin.site.register(FarmTask)


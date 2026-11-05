from django.contrib import admin

from .models import SimulationResult, SimulationScenario


@admin.register(SimulationScenario)
class SimulationScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "farm", "crop", "historical_year", "created_at")
    list_filter = ("season", "irrigation_scenario", "historical_year")
    search_fields = ("name", "owner__email", "farm__name", "crop__name")


admin.site.register(SimulationResult)


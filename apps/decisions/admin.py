from django.contrib import admin

from .models import DecisionOutcome, FarmingDecision


@admin.register(FarmingDecision)
class FarmingDecisionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "farm", "decision_type", "decision_date", "status")
    list_filter = ("decision_type", "status", "decision_date")
    search_fields = ("title", "details", "owner__email", "farm__name")


admin.site.register(DecisionOutcome)


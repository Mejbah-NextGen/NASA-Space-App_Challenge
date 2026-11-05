from django.contrib import admin

from .models import Consultation, ConsultationMessage, ExpertAssignment, ExpertRecommendation, FarmDataConsent


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("title", "farmer", "agriculturalist", "status", "priority", "updated_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "farmer__email", "agriculturalist__email")


admin.site.register(ConsultationMessage)
admin.site.register(ExpertAssignment)
admin.site.register(ExpertRecommendation)
admin.site.register(FarmDataConsent)

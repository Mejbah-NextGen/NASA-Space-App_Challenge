from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_identifier", "result")
    list_filter = ("result", "action")
    search_fields = ("action", "target_identifier", "actor__email")
    readonly_fields = ("actor", "action", "target_type", "target_identifier", "result", "metadata", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

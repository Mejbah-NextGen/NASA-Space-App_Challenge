from django.contrib import admin

from .models import PlatformSetting, SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "email", "status", "priority", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("subject", "email", "name", "message")


admin.site.register(PlatformSetting)

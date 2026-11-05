from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AgriculturalistProfile, AgriculturalistVerification, FarmerProfile, User, UserPreference


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_verified", "is_active", "is_staff")
    list_filter = ("role", "is_verified", "is_active", "is_staff")
    search_fields = ("email", "full_name", "phone_number")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal information", {"fields": ("full_name", "phone_number", "profile_image", "district", "upazila")}),
        ("Access", {"fields": ("role", "is_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Preferences", {"fields": ("preferred_language",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "role", "password1", "password2")}),)


admin.site.register(FarmerProfile)
admin.site.register(AgriculturalistProfile)
admin.site.register(AgriculturalistVerification)
admin.site.register(UserPreference)

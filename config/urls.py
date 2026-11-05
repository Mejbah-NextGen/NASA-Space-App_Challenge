from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("apps.accounts.urls")),
    path("farmer/simulator/", include("apps.simulations.urls")),
    path("farmer/decisions/", include("apps.decisions.urls")),
    path("farmer/consultations/", include("apps.consultations.farmer_urls")),
    path("farmer/", include("apps.farms.urls")),
    path("agriculturalist/", include("apps.consultations.agriculturalist_urls")),
    path("learning/", include("apps.learning.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("assistant/", include("apps.ai_assistant.urls")),
    path("platform-admin/", include("apps.administration.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.weather.urls")),
    path("", include("apps.agricultural_data.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

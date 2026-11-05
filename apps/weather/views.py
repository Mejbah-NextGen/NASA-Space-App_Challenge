from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.permissions import FarmerRequiredMixin
from apps.agricultural_data.models import Region

from .models import WeatherAlert
from .services import available_districts, get_weather


def weather_context(request):
    district = request.GET.get("district", "").strip()
    if not district and request.user.is_authenticated:
        district = request.user.district
    district = district or "Kurigram"
    payload = get_weather(district)
    alerts = WeatherAlert.objects.filter(
        region__district__iexact=payload["district"],
        is_active=True,
        starts_at__lte=timezone.now(),
        ends_at__gte=timezone.now(),
    ).select_related("source")
    return {"weather": payload, "districts": available_districts(), "alerts": alerts}


class PublicWeatherView(TemplateView):
    template_name = "public/weather.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(weather_context(self.request))
        return context


class FarmerWeatherView(FarmerRequiredMixin, TemplateView):
    template_name = "farmer/weather.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(weather_context(self.request))
        context["page_title"] = "Weather & Alerts"
        return context

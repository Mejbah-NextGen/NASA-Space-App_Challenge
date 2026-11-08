from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Avg, Count, Sum
from django.db.models.functions import ExtractYear
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.agricultural_data.models import (
    AgriculturalDataset,
    CropDisease,
    DataSource,
    DiseaseGuidance,
    HistoricalWeatherObservation,
)
from apps.agricultural_data.views import DEMO_RAINFALL, DEMO_YEARS, _public_series
from apps.weather.services import available_districts, get_weather

from .forms import SupportTicketForm


NASA_AGRICULTURE_NEWS = (
    {
        "date": "8 September 2026",
        "source": "NASA Landsat",
        "title": "Separating wheat from chaff — from space",
        "summary": "Researchers use harmonized Landsat and Sentinel-2 observations to distinguish winter cover crops from wheat and other vegetation.",
        "url": "https://science.nasa.gov/mission/landsat/separating-wheat-from-chaff-from-space/",
    },
    {
        "date": "29 August 2025",
        "source": "NASA Science",
        "title": "Mapping plant productivity with satellite data",
        "summary": "A NASA research update explores new global views of plant productivity and the data behind vegetation monitoring.",
        "url": "https://science.nasa.gov/blogs/science-news/2025/08/29/nasa-scientists-map-plant-productivity-with-data-from-ocean-satellite/",
    },
    {
        "date": "12 March 2025",
        "source": "NASA JPL",
        "title": "NISAR will map farmland from planting to harvest",
        "summary": "The NASA-ISRO radar mission is designed to track crop growth, plant water content, and soil moisture through cloudy and rainy conditions.",
        "url": "https://www.jpl.nasa.gov/news/nasa-isro-mission-will-map-farmland-from-planting-to-harvest/",
    },
)


def _home_crop_health_context():
    public_statuses = [AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE]
    diseases = CropDisease.objects.filter(
        dataset__status__in=public_statuses,
        dataset__source__is_active=True,
    )
    guidance = DiseaseGuidance.objects.filter(disease__in=diseases)
    top_crops = list(
        diseases.order_by()
        .values("crop_name")
        .annotate(disease_count=Count("id", distinct=True))
        .order_by("-disease_count", "crop_name")[:8]
    )
    category_counts = {
        row["category"]: row["count"]
        for row in guidance.order_by().values("category").annotate(count=Count("id"))
    }
    focus_crops = ("Rice", "Maize", "Tomato", "Potato", "Mango", "Brinjal")
    focus_counts = {
        row["crop_name"]: row["disease_count"]
        for row in (
            diseases.filter(crop_name__in=focus_crops)
            .order_by()
            .values("crop_name")
            .annotate(disease_count=Count("id", distinct=True))
        )
    }
    dataset = (
        AgriculturalDataset.objects.filter(crop_diseases__in=diseases)
        .select_related("source")
        .distinct()
        .order_by("-updated_at")
        .first()
    )
    return {
        "available": guidance.exists(),
        "crop_count": diseases.order_by().values("crop_name").distinct().count(),
        "disease_count": diseases.count(),
        "guidance_count": guidance.count(),
        "dataset": dataset,
        "focus_crops": [
            {"name": crop, "disease_count": focus_counts[crop]}
            for crop in focus_crops
            if crop in focus_counts
        ],
        "crop_chart": {
            "labels": [row["crop_name"] for row in top_crops],
            "values": [row["disease_count"] for row in top_crops],
        },
        "category_chart": {
            "labels": [label for value, label in DiseaseGuidance.Category.choices],
            "values": [category_counts.get(value, 0) for value, label in DiseaseGuidance.Category.choices],
        },
    }


def _support_request_allowed(request):
    if request.user.is_authenticated:
        identity = f"user:{request.user.pk}"
    else:
        remote_address = request.META.get("REMOTE_ADDR", "unknown").strip() or "unknown"
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "") if settings.TRUST_X_FORWARDED_FOR else ""
        identity = f"ip:{forwarded.split(',')[0].strip() if forwarded else remote_address}"
    key = f"support-rate:{identity}"
    if cache.add(key, 1, timeout=600):
        return True
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=600)
        count = 1
    return count <= settings.SUPPORT_RATE_LIMIT_PER_10_MINUTES


class HomeView(TemplateView):
    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        district = self.request.GET.get("district", "Kurigram")
        weather = get_weather(district)
        observation_candidates = HistoricalWeatherObservation.objects.filter(
            region__district__iexact=weather["district"],
            dataset__status__in=[AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE],
        )
        observations, history_is_demo = _public_series(observation_candidates)
        annual = list(
            observations
            .annotate(year=ExtractYear("observed_on"))
            .values("year")
            .annotate(rainfall=Sum("rainfall_mm"), temperature=Avg("temperature_mean_c"))
            .order_by("year")[:10]
        )
        if annual:
            chart = {
                "years": [row["year"] for row in annual],
                "rainfall": [float(row["rainfall"] or 0) for row in annual],
            }
        else:
            chart = {"years": DEMO_YEARS, "rainfall": DEMO_RAINFALL}
            history_is_demo = True
        context.update(
            {
                "weather": weather,
                "districts": available_districts(),
                "history_chart": chart,
                "history_is_demo": history_is_demo,
                "featured_sources": DataSource.objects.filter(is_active=True)[:3],
                "nasa_agriculture_news": NASA_AGRICULTURE_NEWS,
                "crop_health": _home_crop_health_context(),
            }
        )
        return context


class StaticPageView(TemplateView):
    pass


class HelpView(FormView):
    template_name = "public/help.html"
    form_class = SupportTicketForm

    def post(self, request, *args, **kwargs):
        if not _support_request_allowed(request):
            form = self.get_form()
            form.add_error(None, "Too many support requests. Please wait ten minutes and try again.")
            response = self.form_invalid(form)
            response.status_code = 429
            return response
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial.update({"name": self.request.user.display_name, "email": self.request.user.email})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tickets"] = (
            self.request.user.support_tickets.all()[:10] if self.request.user.is_authenticated else []
        )
        return context

    def form_valid(self, form):
        ticket = form.save(commit=False)
        if self.request.user.is_authenticated:
            ticket.user = self.request.user
        ticket.save()
        messages.success(self.request, f"Your support request #{ticket.pk} was submitted.")
        return redirect(self.request.resolver_match.view_name)

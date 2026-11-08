from collections import defaultdict

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Exists, Max, OuterRef, Prefetch, Q, Sum
from django.db.models.functions import ExtractYear
from django.views.generic import TemplateView

from apps.accounts.permissions import FarmerRequiredMixin

from .models import (
    AgriculturalDataset,
    CropDisease,
    DataSource,
    DiseaseGuidance,
    HistoricalCropObservation,
    HistoricalWeatherObservation,
    Region,
)


DEMO_RAINFALL = [980, 1120, 870, 640, 1050, 910, 980, 760, 850, 920]
DEMO_TEMPERATURE = [31.1, 31.5, 32.0, 32.8, 31.9, 32.4, 33.0, 32.6, 33.2, 32.9]
DEMO_YEARS = list(range(2016, 2026))


def _public_series(queryset):
    """Prefer verified observations and never mix them with demonstration rows."""
    verified = queryset.filter(
        dataset__status=AgriculturalDataset.Status.VERIFIED,
        dataset__source__is_demo=False,
    )
    if verified.exists():
        return verified, False
    sample = queryset.filter(
        Q(dataset__status=AgriculturalDataset.Status.SAMPLE) | Q(dataset__source__is_demo=True)
    )
    if sample.exists():
        return sample, True
    return queryset.none(), True


def _source_metadata(queryset, *, fallback_name, is_demo):
    names = list(
        queryset.order_by()
        .values_list("dataset__source__name", flat=True)
        .distinct()[:3]
    )
    updated_at = queryset.aggregate(updated=Max("dataset__updated_at"))["updated"]
    return {
        "name": ", ".join(names) if names else fallback_name,
        "status": "SAMPLE" if is_demo else "VERIFIED",
        "updated_at": updated_at,
    }


def history_context(params):
    district = params.get("district", "Kurigram").strip() or "Kurigram"
    crop = params.get("crop", "").strip()
    try:
        start_year = max(1900, int(params.get("start_year", 2016)))
        end_year = min(2200, int(params.get("end_year", 2025)))
    except (TypeError, ValueError):
        start_year, end_year = 2016, 2025
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    weather_candidates = HistoricalWeatherObservation.objects.filter(
        region__district__iexact=district,
        observed_on__year__range=(start_year, end_year),
        dataset__status__in=[AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE],
    )
    weather, weather_is_demo = _public_series(weather_candidates)
    annual_weather = list(
        weather.annotate(year=ExtractYear("observed_on"))
        .values("year")
        .annotate(rainfall=Sum("rainfall_mm"), temperature=Avg("temperature_mean_c"))
        .order_by("year")
    )
    if not annual_weather:
        years = [year for year in DEMO_YEARS if start_year <= year <= end_year]
        indexes = [DEMO_YEARS.index(year) for year in years]
        rainfall = [DEMO_RAINFALL[index] for index in indexes]
        temperatures = [DEMO_TEMPERATURE[index] for index in indexes]
        weather_is_demo = True
        weather_source = {
            "name": "Farm Time Machine built-in demonstration series",
            "status": "SAMPLE",
            "updated_at": None,
        }
    else:
        years = [row["year"] for row in annual_weather]
        rainfall = [float(row["rainfall"] or 0) for row in annual_weather]
        temperatures = [float(row["temperature"] or 0) for row in annual_weather]
        weather_source = _source_metadata(
            weather,
            fallback_name="Historical weather observations",
            is_demo=weather_is_demo,
        )

    crop_candidates = HistoricalCropObservation.objects.filter(
        region__district__iexact=district,
        year__range=(start_year, end_year),
        dataset__status__in=[AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE],
    )
    if crop:
        crop_candidates = crop_candidates.filter(crop_name__iexact=crop)
    crop_query, crop_is_demo = _public_series(crop_candidates)
    crop_rows = list(
        crop_query.values("year", "crop_name")
        .annotate(production=Sum("production_tonnes"), average_yield=Avg("yield_tonnes_per_hectare"))
        .order_by("year", "crop_name")[:100]
    )
    crop_series = defaultdict(list)
    for row in crop_rows:
        crop_series[row["crop_name"]].append(
            {"year": row["year"], "production": float(row["production"] or 0), "yield": float(row["average_yield"] or 0)}
        )
    crop_source = _source_metadata(
        crop_query,
        fallback_name="No crop observations match these filters",
        is_demo=crop_is_demo,
    )
    crop_years = sorted({row["year"] for row in crop_rows})
    return {
        "selected_district": district,
        "selected_crop": crop,
        "start_year": start_year,
        "end_year": end_year,
        "districts": Region.objects.order_by("district").values_list("district", flat=True).distinct(),
        "crops": HistoricalCropObservation.objects.order_by("crop_name").values_list("crop_name", flat=True).distinct(),
        "chart_data": {"years": years, "rainfall": rainfall, "temperature": temperatures},
        "crop_years": crop_years,
        "crop_series": dict(crop_series),
        "source_meta": weather_source,
        "weather_source_meta": weather_source,
        "crop_source_meta": crop_source,
        "is_demo_data": weather_is_demo,
        "weather_is_demo": weather_is_demo,
        "crop_is_demo": crop_is_demo,
    }


class PublicHistoryView(TemplateView):
    template_name = "public/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(history_context(self.request.GET))
        return context


class FarmerHistoryView(FarmerRequiredMixin, TemplateView):
    template_name = "farmer/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        if not params.get("district"):
            params["district"] = self.request.user.district or "Kurigram"
        context.update(history_context(params))
        context["page_title"] = "Farm History"
        return context


class CropInsightsView(TemplateView):
    template_name = "public/crop_insights.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        crop = self.request.GET.get("crop", "").strip()
        district = self.request.GET.get("district", "").strip()
        public_statuses = [AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE]
        observations = HistoricalCropObservation.objects.filter(
            dataset__status__in=public_statuses
        ).select_related("region", "dataset", "dataset__source")
        if crop:
            observations = observations.filter(crop_name__iexact=crop)
        if district:
            observations = observations.filter(region__district__iexact=district)
        context.update(
            {
                "observations": observations.order_by("-year", "crop_name")[:50],
                "selected_crop": crop,
                "selected_district": district,
                "crops": HistoricalCropObservation.objects.filter(dataset__status__in=public_statuses).order_by("crop_name").values_list("crop_name", flat=True).distinct(),
                "districts": Region.objects.filter(historical_crops__dataset__status__in=public_statuses).order_by("district").values_list("district", flat=True).distinct(),
            }
        )
        return context


class CropHealthView(TemplateView):
    template_name = "public/crop_health.html"
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()[:120]
        crop = self.request.GET.get("crop", "").strip()[:100]
        category = self.request.GET.get("category", "").strip().upper()
        if category not in DiseaseGuidance.Category.values:
            category = ""

        public_statuses = [AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE]
        public_diseases = CropDisease.objects.filter(
            dataset__status__in=public_statuses,
            dataset__source__is_active=True,
        )
        visible_guidance = DiseaseGuidance.objects.all()
        if category:
            visible_guidance = visible_guidance.filter(category=category)
        if query:
            visible_guidance = visible_guidance.filter(
                Q(disease__crop_name__icontains=query)
                | Q(disease__disease_name__icontains=query)
                | Q(information_type__icontains=query)
                | Q(content__icontains=query)
            )

        filtered = public_diseases
        if crop:
            filtered = filtered.filter(crop_name__iexact=crop)
        if category or query:
            filtered = filtered.annotate(
                has_visible_guidance=Exists(
                    visible_guidance.filter(disease_id=OuterRef("pk"))
                )
            ).filter(
                has_visible_guidance=True
            )
        filtered = (
            filtered.select_related("dataset", "dataset__source")
            .prefetch_related(
                Prefetch(
                    "guidance_entries",
                    queryset=visible_guidance.order_by("category", "information_type", "pk"),
                    to_attr="visible_guidance",
                )
            )
            .distinct()
            .order_by("crop_name", "disease_name")
        )

        paginator = Paginator(filtered, self.paginate_by)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        guidance = DiseaseGuidance.objects.filter(disease__in=public_diseases)
        top_crops = list(
            public_diseases.order_by()
            .values("crop_name")
            .annotate(disease_count=Count("id", distinct=True))
            .order_by("-disease_count", "crop_name")[:10]
        )
        category_counts = {
            row["category"]: row["count"]
            for row in guidance.order_by().values("category").annotate(count=Count("id"))
        }
        library_dataset = (
            AgriculturalDataset.objects.filter(crop_diseases__in=public_diseases)
            .select_related("source")
            .distinct()
            .order_by("-updated_at")
            .first()
        )
        context.update(
            {
                "diseases": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": paginator.num_pages > 1,
                "selected_query": query,
                "selected_crop": crop,
                "selected_category": category,
                "crops": public_diseases.order_by("crop_name").values_list("crop_name", flat=True).distinct(),
                "category_choices": DiseaseGuidance.Category.choices,
                "library_dataset": library_dataset,
                "library_summary": {
                    "crops": public_diseases.order_by().values("crop_name").distinct().count(),
                    "diseases": public_diseases.count(),
                    "guidance": guidance.count(),
                },
                "crop_chart": {
                    "labels": [row["crop_name"] for row in top_crops],
                    "values": [row["disease_count"] for row in top_crops],
                },
                "category_chart": {
                    "labels": [label for value, label in DiseaseGuidance.Category.choices],
                    "values": [category_counts.get(value, 0) for value, label in DiseaseGuidance.Category.choices],
                },
            }
        )
        return context


class DataSourcesView(TemplateView):
    template_name = "public/data_sources.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sources"] = DataSource.objects.filter(is_active=True).prefetch_related("datasets")
        return context

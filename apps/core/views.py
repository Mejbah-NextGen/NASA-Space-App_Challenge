from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Avg, Q, Sum
from django.db.models.functions import ExtractYear
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.agricultural_data.models import AgriculturalDataset, DataSource, HistoricalWeatherObservation
from apps.agricultural_data.views import DEMO_RAINFALL, DEMO_YEARS
from apps.weather.services import available_districts, get_weather

from .forms import SupportTicketForm


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
        observations = HistoricalWeatherObservation.objects.filter(
            region__district__iexact=weather["district"],
            dataset__status__in=[AgriculturalDataset.Status.VERIFIED, AgriculturalDataset.Status.SAMPLE],
        )
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
            history_is_demo = observations.filter(
                Q(dataset__status=AgriculturalDataset.Status.SAMPLE) | Q(dataset__source__is_demo=True)
            ).exists()
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

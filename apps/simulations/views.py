from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from apps.accounts.permissions import FarmerRequiredMixin

from .forms import SimulationScenarioForm
from .models import SimulationScenario
from .services import calculate_and_store


class SimulatorView(FarmerRequiredMixin, CreateView):
    model = SimulationScenario
    form_class = SimulationScenarioForm
    template_name = "farmer/simulator.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        calculate_and_store(self.object)
        messages.success(self.request, "Simulation completed and saved.")
        return response

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            recent_scenarios=SimulationScenario.objects.filter(owner=self.request.user).select_related("crop", "farm", "result")[:5],
            **kwargs,
        )

    def get_success_url(self):
        return reverse("simulations:detail", kwargs={"pk": self.object.pk})


class SimulationHistoryView(FarmerRequiredMixin, ListView):
    model = SimulationScenario
    template_name = "farmer/simulation_history.html"
    context_object_name = "scenarios"
    paginate_by = 12

    def get_queryset(self):
        queryset = SimulationScenario.objects.filter(owner=self.request.user).select_related("farm", "field", "crop", "result")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(crop__name__icontains=query) | Q(farm__name__icontains=query))
        return queryset


class SimulationDetailView(FarmerRequiredMixin, DetailView):
    model = SimulationScenario
    template_name = "farmer/simulation_detail.html"
    context_object_name = "scenario"

    def get_queryset(self):
        return SimulationScenario.objects.filter(owner=self.request.user).select_related("farm", "field", "crop", "result")


class SimulationCompareView(FarmerRequiredMixin, TemplateView):
    template_name = "farmer/simulation_compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = [value for value in self.request.GET.getlist("scenario") if value.isdigit()][:3]
        context["scenarios"] = SimulationScenario.objects.filter(owner=self.request.user, pk__in=ids).select_related("farm", "crop", "result")
        return context


from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from apps.accounts.permissions import FarmerRequiredMixin

from .forms import DecisionOutcomeForm, FarmingDecisionForm
from .models import DecisionOutcome, FarmingDecision


class DecisionListView(FarmerRequiredMixin, ListView):
    model = FarmingDecision
    template_name = "farmer/decision_list.html"
    context_object_name = "decisions"
    paginate_by = 15

    def get_queryset(self):
        queryset = FarmingDecision.objects.filter(owner=self.request.user).select_related("farm", "field", "planting__crop", "simulation")
        query = self.request.GET.get("q", "").strip()
        decision_type = self.request.GET.get("type", "")
        farm_id = self.request.GET.get("farm", "")
        year = self.request.GET.get("year", "")
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(details__icontains=query) | Q(rationale__icontains=query))
        if decision_type in FarmingDecision.DecisionType.values:
            queryset = queryset.filter(decision_type=decision_type)
        if farm_id.isdigit():
            queryset = queryset.filter(farm_id=farm_id, farm__owner=self.request.user)
        if year.isdigit():
            queryset = queryset.filter(decision_date__year=year)
        return queryset

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            decision_types=FarmingDecision.DecisionType.choices,
            farms=self.request.user.farms.filter(is_archived=False),
            **kwargs,
        )


class DecisionCreateView(FarmerRequiredMixin, CreateView):
    model = FarmingDecision
    form_class = FarmingDecisionForm
    template_name = "farmer/decision_form.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Decision added to your timeline.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("decisions:detail", kwargs={"pk": self.object.pk})


class DecisionDetailView(FarmerRequiredMixin, DetailView):
    model = FarmingDecision
    template_name = "farmer/decision_detail.html"
    context_object_name = "decision"

    def get_queryset(self):
        return FarmingDecision.objects.filter(owner=self.request.user).select_related("farm", "field", "planting__crop", "simulation")

    def get_context_data(self, **kwargs):
        outcome = getattr(self.object, "outcome", None)
        return super().get_context_data(outcome_form=DecisionOutcomeForm(instance=outcome), **kwargs)


class DecisionUpdateView(FarmerRequiredMixin, UpdateView):
    model = FarmingDecision
    form_class = FarmingDecisionForm
    template_name = "farmer/decision_form.html"

    def get_queryset(self):
        return FarmingDecision.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        messages.success(self.request, "Decision updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("decisions:detail", kwargs={"pk": self.object.pk})


class DecisionOutcomeUpdateView(FarmerRequiredMixin, FormView):
    form_class = DecisionOutcomeForm
    template_name = "farmer/outcome_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.decision = get_object_or_404(FarmingDecision, pk=kwargs["decision_pk"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = DecisionOutcome.objects.filter(decision=self.decision).first()
        return kwargs

    def form_valid(self, form):
        outcome = form.save(commit=False)
        outcome.decision = self.decision
        outcome.save()
        messages.success(self.request, "Observed outcome saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("decisions:detail", kwargs={"pk": self.decision.pk})


from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import FarmerRequiredMixin

from .forms import CropPlantingForm, FarmActivityForm, FarmForm, FarmTaskForm, FieldForm
from .models import CropPlanting, Farm, FarmActivity, FarmTask, Field


class FarmerOwnedQuerysetMixin(FarmerRequiredMixin):
    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class FarmListView(FarmerRequiredMixin, ListView):
    model = Farm
    template_name = "farmer/farm_list.html"
    context_object_name = "farms"

    def get_queryset(self):
        queryset = Farm.objects.filter(owner=self.request.user)
        if self.request.GET.get("archived") != "1":
            queryset = queryset.filter(is_archived=False)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(district__icontains=query) | Q(upazila__icontains=query))
        return queryset


class FarmCreateView(FarmerRequiredMixin, CreateView):
    model = Farm
    form_class = FarmForm
    template_name = "farmer/farm_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Farm added successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.object.pk})


class FarmDetailView(FarmerOwnedQuerysetMixin, DetailView):
    model = Farm
    template_name = "farmer/farm_detail.html"
    context_object_name = "farm"

    def get_queryset(self):
        plantings = CropPlanting.objects.select_related("crop").order_by("-planting_date")
        return super().get_queryset().prefetch_related(Prefetch("fields__plantings", queryset=plantings), "activities", "tasks")


class FarmUpdateView(FarmerOwnedQuerysetMixin, UpdateView):
    model = Farm
    form_class = FarmForm
    template_name = "farmer/farm_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Farm details updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.object.pk})


class FarmArchiveView(FarmerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, pk):
        farm = get_object_or_404(Farm, pk=pk, owner=request.user)
        farm.is_archived = True
        farm.save(update_fields=["is_archived", "updated_at"])
        messages.success(request, f"{farm.name} was archived. Its records are preserved.")
        return redirect("farms:farm_list")


class FieldCreateView(FarmerRequiredMixin, CreateView):
    model = Field
    form_class = FieldForm
    template_name = "farmer/field_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.farm = get_object_or_404(Farm, pk=kwargs["farm_pk"], owner=request.user, is_archived=False)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.farm = self.farm
        messages.success(self.request, "Field added successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(farm=self.farm, **kwargs)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.farm.pk})


class FieldUpdateView(FarmerRequiredMixin, UpdateView):
    model = Field
    form_class = FieldForm
    template_name = "farmer/field_form.html"

    def get_queryset(self):
        return Field.objects.filter(farm__owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Field updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(farm=self.object.farm, **kwargs)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.object.farm_id})


class PlantingCreateView(FarmerRequiredMixin, CreateView):
    model = CropPlanting
    form_class = CropPlantingForm
    template_name = "farmer/planting_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.field = get_object_or_404(Field, pk=kwargs["field_pk"], farm__owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.field = self.field
        messages.success(self.request, "Crop planting saved.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(field=self.field, **kwargs)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.field.farm_id})


class PlantingUpdateView(FarmerRequiredMixin, UpdateView):
    model = CropPlanting
    form_class = CropPlantingForm
    template_name = "farmer/planting_form.html"

    def get_queryset(self):
        return CropPlanting.objects.filter(field__farm__owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Crop record updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(field=self.object.field, **kwargs)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.object.field.farm_id})


class FarmActivityCreateView(FarmerRequiredMixin, CreateView):
    model = FarmActivity
    form_class = FarmActivityForm
    template_name = "farmer/activity_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.farm = get_object_or_404(Farm, pk=kwargs["farm_pk"], owner=request.user, is_archived=False)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "farm": self.farm}

    def form_valid(self, form):
        form.instance.farm = self.farm
        messages.success(self.request, "Farm activity recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.farm.pk})


class FarmTaskCreateView(FarmerRequiredMixin, CreateView):
    model = FarmTask
    form_class = FarmTaskForm
    template_name = "farmer/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.farm = get_object_or_404(Farm, pk=kwargs["farm_pk"], owner=request.user, is_archived=False)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "farm": self.farm}

    def form_valid(self, form):
        form.instance.farm = self.farm
        messages.success(self.request, "Farm task added.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("farms:farm_detail", kwargs={"pk": self.farm.pk})


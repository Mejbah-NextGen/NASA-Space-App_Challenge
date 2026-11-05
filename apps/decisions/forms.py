from django import forms

from apps.farms.models import CropPlanting, Farm, Field
from apps.simulations.models import SimulationScenario

from .models import DecisionOutcome, FarmingDecision


class FarmingDecisionForm(forms.ModelForm):
    class Meta:
        model = FarmingDecision
        fields = ("farm", "field", "planting", "simulation", "decision_type", "title", "decision_date", "details", "rationale", "status")
        widgets = {"decision_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["farm"].queryset = Farm.objects.filter(owner=user, is_archived=False)
        self.fields["field"].queryset = Field.objects.filter(farm__owner=user)
        self.fields["planting"].queryset = CropPlanting.objects.filter(field__farm__owner=user).select_related("crop", "field")
        self.fields["simulation"].queryset = SimulationScenario.objects.filter(owner=user).select_related("crop")

    def clean(self):
        cleaned = super().clean()
        farm = cleaned.get("farm")
        field = cleaned.get("field")
        planting = cleaned.get("planting")
        if field and farm and field.farm_id != farm.pk:
            self.add_error("field", "Choose a field from the selected farm.")
        if planting and farm and planting.field.farm_id != farm.pk:
            self.add_error("planting", "Choose a crop record from the selected farm.")
        return cleaned


class DecisionOutcomeForm(forms.ModelForm):
    class Meta:
        model = DecisionOutcome
        fields = ("observed_date", "outcome", "rating", "yield_impact")
        widgets = {"observed_date": forms.DateInput(attrs={"type": "date"})}


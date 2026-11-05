from django import forms

from apps.farms.models import Crop, Farm, Field

from .models import SimulationScenario


class SimulationScenarioForm(forms.ModelForm):
    class Meta:
        model = SimulationScenario
        fields = ("name", "farm", "field", "crop", "planting_date", "temperature_assumption", "rainfall_assumption", "irrigation_scenario", "historical_year", "season")
        widgets = {"planting_date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "temperature_assumption": "Seasonal temperature assumption in °C.",
            "rainfall_assumption": "Seasonal rainfall assumption in millimetres.",
            "historical_year": "A reference year; the baseline does not claim to recreate verified conditions unless imported data is linked.",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["farm"].queryset = Farm.objects.filter(owner=user, is_archived=False)
        self.fields["field"].queryset = Field.objects.filter(farm__owner=user).exclude(status=Field.Status.ARCHIVED)
        self.fields["crop"].queryset = Crop.objects.filter(is_supported=True)

    def clean(self):
        cleaned = super().clean()
        farm = cleaned.get("farm")
        field = cleaned.get("field")
        if field and farm and field.farm_id != farm.pk:
            self.add_error("field", "Choose a field from the selected farm.")
        return cleaned


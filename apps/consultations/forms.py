from django import forms

from apps.accounts.models import User
from apps.accounts.verification import restrict_to_email_verified
from apps.farms.models import Crop, Farm
from apps.simulations.models import SimulationScenario

from .models import Consultation, ConsultationMessage, ExpertRecommendation, FarmDataConsent


class ConsultationCreateForm(forms.ModelForm):
    share_farm_data = forms.BooleanField(
        required=False,
        help_text="Allow the selected expert to view the selected farm while this consultation is active.",
    )
    consent_scope = forms.ChoiceField(choices=FarmDataConsent.Scope.choices, initial=FarmDataConsent.Scope.SUMMARY)

    class Meta:
        model = Consultation
        fields = ("agriculturalist", "farm", "title", "description", "image", "priority")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, farmer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.farmer = farmer
        experts = User.objects.filter(
            role=User.Role.AGRICULTURALIST,
            is_active=True,
        )
        self.fields["agriculturalist"].queryset = restrict_to_email_verified(experts).select_related(
            "agriculturalist_profile"
        )
        self.fields["agriculturalist"].required = False
        self.fields["farm"].queryset = Farm.objects.filter(owner=farmer, is_archived=False) if farmer else Farm.objects.none()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("share_farm_data") and not cleaned.get("farm"):
            self.add_error("farm", "Select a farm before sharing farm data.")
        if cleaned.get("share_farm_data") and not cleaned.get("agriculturalist"):
            self.add_error("agriculturalist", "Select an Agriculturalist before sharing farm data.")
        return cleaned


class ConsultationMessageForm(forms.ModelForm):
    class Meta:
        model = ConsultationMessage
        fields = ("body", "attachment")
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Write a message..."})}


class RecommendationForm(forms.ModelForm):
    class Meta:
        model = ExpertRecommendation
        fields = ("title", "explanation", "priority", "status")
        widgets = {"explanation": forms.Textarea(attrs={"rows": 6})}


class AgriculturalistSimulationForm(forms.Form):
    consultation = forms.ModelChoiceField(queryset=Consultation.objects.none(), label="Authorized farmer case")
    crop = forms.ModelChoiceField(queryset=Crop.objects.none())
    temperature_assumption = forms.DecimalField(min_value=-10, max_value=60, decimal_places=1, label="Temperature assumption (°C)")
    rainfall_assumption = forms.DecimalField(min_value=0, max_value=5000, decimal_places=1, label="Rainfall assumption (mm)")
    irrigation_scenario = forms.ChoiceField(choices=SimulationScenario.IrrigationScenario.choices)
    historical_year = forms.IntegerField(min_value=1980, max_value=2100, initial=2025)
    season = forms.ChoiceField(choices=SimulationScenario.Season.choices)

    def __init__(self, *args, agriculturalist=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consultation"].queryset = Consultation.objects.filter(
            agriculturalist=agriculturalist,
            status__in=[Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE],
            data_consent__agriculturalist=agriculturalist,
            data_consent__revoked_at__isnull=True,
        ).select_related("farmer", "farm")
        self.fields["crop"].queryset = Crop.objects.filter(is_supported=True).order_by("name", "variety")

from django import forms

from apps.accounts.models import AgriculturalistVerification
from apps.accounts.models import User
from apps.accounts.verification import restrict_to_email_verified
from apps.agricultural_data.models import AgriculturalDataset, DataImportJob, DataSource, Region
from apps.consultations.models import Consultation
from apps.core.models import PlatformSetting, SupportTicket
from apps.farms.models import Crop
from apps.weather.models import WeatherAlert


class VerificationReviewForm(forms.ModelForm):
    class Meta:
        model = AgriculturalistVerification
        fields = ("status", "notes")

    def clean_status(self):
        status = self.cleaned_data["status"]
        allowed = {
            AgriculturalistVerification.Status.APPROVED,
            AgriculturalistVerification.Status.REJECTED,
            AgriculturalistVerification.Status.MORE_INFO,
        }
        if status not in allowed:
            raise forms.ValidationError("Select an actionable review decision.")
        return status


class UserStatusForm(forms.Form):
    action = forms.ChoiceField(choices=[("activate", "Activate"), ("suspend", "Suspend")])


class LearningReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[("approve", "Approve"), ("reject", "Request edits")])
    review_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class DataUploadForm(forms.Form):
    dataset = forms.ModelChoiceField(queryset=AgriculturalDataset.objects.none())
    kind = forms.ChoiceField(choices=DataImportJob.Kind.choices)
    csv_file = forms.FileField(help_text="UTF-8 CSV, maximum 5 MB and 5,000 rows.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dataset"].queryset = AgriculturalDataset.objects.select_related("source").order_by("title")

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file.")
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("CSV files must be 5 MB or smaller.")
        return upload


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = (
            "name",
            "provider",
            "kind",
            "url",
            "description",
            "attribution",
            "geographic_coverage",
            "update_frequency",
            "limitations",
            "is_active",
            "is_demo",
            "last_updated_at",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "limitations": forms.Textarea(attrs={"rows": 3}),
            "last_updated_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class AgriculturalDatasetForm(forms.ModelForm):
    class Meta:
        model = AgriculturalDataset
        fields = (
            "source",
            "title",
            "slug",
            "description",
            "status",
            "geographic_coverage",
            "date_start",
            "date_end",
            "units",
            "quality_notes",
            "metadata",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "date_start": forms.DateInput(attrs={"type": "date"}),
            "date_end": forms.DateInput(attrs={"type": "date"}),
            "quality_notes": forms.Textarea(attrs={"rows": 3}),
            "metadata": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = DataSource.objects.order_by("name")

    def clean(self):
        cleaned = super().clean()
        date_start = cleaned.get("date_start")
        date_end = cleaned.get("date_end")
        if date_start and date_end and date_end < date_start:
            self.add_error("date_end", "The coverage end date cannot precede the start date.")
        if cleaned.get("status") == AgriculturalDataset.Status.VERIFIED:
            source = cleaned.get("source")
            if source and source.is_demo:
                self.add_error("status", "A dataset from a demonstration source cannot be marked verified.")
            for field, label in (
                ("geographic_coverage", "Geographic coverage"),
                ("date_start", "Coverage start date"),
                ("date_end", "Coverage end date"),
                ("units", "Units"),
            ):
                if not cleaned.get(field):
                    self.add_error(field, f"{label} is required for a verified dataset.")
        return cleaned


class CropCatalogForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ("name", "variety", "is_supported")

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_variety(self):
        return self.cleaned_data.get("variety", "").strip()


class CropCatalogToggleForm(forms.Form):
    action = forms.ChoiceField(choices=[("support", "Support"), ("disable", "Disable")])


class ExpertAssignmentForm(forms.Form):
    consultation = forms.ModelChoiceField(queryset=Consultation.objects.none())
    agriculturalist = forms.ModelChoiceField(queryset=User.objects.none(), label="Approved Agriculturalist")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consultation"].queryset = Consultation.objects.filter(
            status__in=[Consultation.Status.PENDING, Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE]
        ).select_related("farmer", "farm").order_by("-updated_at")
        experts = User.objects.filter(
            role=User.Role.AGRICULTURALIST,
            agriculturalist_profile__is_approved=True,
            is_active=True,
        )
        self.fields["agriculturalist"].queryset = restrict_to_email_verified(experts).order_by("full_name")


class WeatherAlertForm(forms.ModelForm):
    class Meta:
        model = WeatherAlert
        fields = (
            "region",
            "source",
            "title",
            "description",
            "recommendation",
            "severity",
            "starts_at",
            "ends_at",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "recommendation": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].queryset = Region.objects.order_by("district", "upazila")
        self.fields["source"].queryset = DataSource.objects.filter(
            is_active=True,
            kind=DataSource.Kind.WEATHER,
        ).order_by("name")

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "The alert end time must be after its start time.")
        return cleaned


class WeatherAlertToggleForm(forms.Form):
    action = forms.ChoiceField(choices=[("activate", "Activate"), ("deactivate", "Deactivate")])


class SupportTicketUpdateForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ("status", "priority", "staff_response")
        widgets = {"staff_response": forms.Textarea(attrs={"rows": 6})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED}:
            if not (cleaned.get("staff_response") or "").strip():
                self.add_error("staff_response", "Add a staff response before resolving or closing a ticket.")
        return cleaned


class PublicPlatformSettingForm(forms.ModelForm):
    class Meta:
        model = PlatformSetting
        fields = ("description", "value")
        widgets = {"value": forms.Textarea(attrs={"rows": 5})}

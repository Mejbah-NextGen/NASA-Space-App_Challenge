from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.farms.models import AreaUnit

from .models import AgriculturalistProfile, FarmerProfile, User, UserPreference


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    def clean(self):
        email = self.cleaned_data.get("username", "").strip().lower()
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class SignUpForm(UserCreationForm):
    account_type = forms.ChoiceField(
        choices=[(User.Role.FARMER, "Farmer"), (User.Role.AGRICULTURALIST, "Agriculturalist")],
        widget=forms.RadioSelect,
    )
    agree_terms = forms.BooleanField(label="I agree to the Terms, Privacy Policy, and decision-support disclaimer")
    specialization = forms.CharField(required=False, max_length=160)
    qualifications = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = User
        fields = (
            "account_type", "full_name", "email", "phone_number", "district", "upazila",
            "specialization", "qualifications", "password1", "password2", "agree_terms",
        )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("account_type") == User.Role.AGRICULTURALIST:
            if not cleaned.get("specialization"):
                self.add_error("specialization", "Specialization is required for an Agriculturalist profile.")
            if not cleaned.get("qualifications"):
                self.add_error("qualifications", "Qualifications are required for an Agriculturalist profile.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["account_type"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            if user.role == User.Role.AGRICULTURALIST:
                profile = user.agriculturalist_profile
                profile.specialization = self.cleaned_data["specialization"]
                profile.qualifications = self.cleaned_data["qualifications"]
                profile.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "phone_number", "profile_image", "district", "upazila")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_profile = None
        if self.instance.role == User.Role.FARMER:
            self.role_profile, _ = FarmerProfile.objects.get_or_create(user=self.instance)
            self.fields["experience"] = forms.ChoiceField(
                label="Farming experience",
                choices=FarmerProfile.Experience.choices,
                initial=self.role_profile.experience,
            )
            self.fields["preferred_area_unit"] = forms.ChoiceField(
                label="Preferred area unit",
                choices=AreaUnit.choices,
                initial=self.role_profile.preferred_area_unit,
            )
            self.fields["bio"] = forms.CharField(
                label="About your farming work",
                required=False,
                max_length=1000,
                initial=self.role_profile.bio,
                widget=forms.Textarea(
                    attrs={
                        "rows": 4,
                        "placeholder": "Crops, farming interests, and the decisions you want help with",
                    }
                ),
            )
        elif self.instance.role == User.Role.AGRICULTURALIST:
            self.role_profile, _ = AgriculturalistProfile.objects.get_or_create(
                user=self.instance,
                defaults={"specialization": "General agriculture", "qualifications": "Self-described experience"},
            )
            profile_fields = (
                ("specialization", forms.CharField(max_length=160, label="Specialization")),
                (
                    "qualifications",
                    forms.CharField(
                        max_length=2000,
                        label="Qualifications and experience",
                        widget=forms.Textarea(attrs={"rows": 4}),
                    ),
                ),
                ("organization", forms.CharField(max_length=160, required=False)),
                (
                    "license_number",
                    forms.CharField(
                        max_length=80,
                        required=False,
                        label="Professional or registration number",
                        help_text="Optional. This is self-reported unless the profile carries a credential-review badge.",
                    ),
                ),
                (
                    "years_experience",
                    forms.IntegerField(min_value=0, max_value=80, label="Years of experience"),
                ),
                (
                    "bio",
                    forms.CharField(
                        max_length=2000,
                        required=False,
                        label="Professional bio",
                        widget=forms.Textarea(
                            attrs={
                                "rows": 4,
                                "placeholder": "Describe the crops, regions, and farm questions you support",
                            }
                        ),
                    ),
                ),
            )
            for name, field in profile_fields:
                field.initial = getattr(self.role_profile, name)
                self.fields[name] = field

    def save(self, commit=True):
        user = super().save(commit=commit)
        if not self.role_profile:
            return user
        if user.role == User.Role.FARMER:
            for field in ("experience", "preferred_area_unit", "bio"):
                setattr(self.role_profile, field, self.cleaned_data[field])
        elif user.role == User.Role.AGRICULTURALIST:
            for field in (
                "specialization",
                "qualifications",
                "organization",
                "license_number",
                "years_experience",
                "bio",
            ):
                setattr(self.role_profile, field, self.cleaned_data[field])
        if commit:
            self.role_profile.save()
        return user


class AccountSettingsForm(forms.ModelForm):
    email_notifications = forms.BooleanField(required=False)
    weather_alerts = forms.BooleanField(required=False)
    consultation_updates = forms.BooleanField(required=False)
    learning_updates = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ("preferred_language",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        preference, _ = UserPreference.objects.get_or_create(user=self.instance)
        for field in ("email_notifications", "weather_alerts", "consultation_updates", "learning_updates"):
            self.fields[field].initial = getattr(preference, field)

    def save(self, commit=True):
        user = super().save(commit=commit)
        preference, _ = UserPreference.objects.get_or_create(user=user)
        for field in ("email_notifications", "weather_alerts", "consultation_updates", "learning_updates"):
            setattr(preference, field, self.cleaned_data[field])
        preference.save()
        return user

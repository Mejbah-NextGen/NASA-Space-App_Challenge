from django import forms

from .models import Crop, CropPlanting, Farm, FarmActivity, FarmTask, Field


class DateInput(forms.DateInput):
    input_type = "date"


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ("name", "district", "upazila", "village", "land_area", "area_unit", "soil_type", "irrigation_type", "description")


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ("name", "area", "area_unit", "soil_type", "irrigation_type", "status", "description")


class CropPlantingForm(forms.ModelForm):
    crop_name = forms.CharField(max_length=100)
    crop_variety = forms.CharField(max_length=120, required=False)

    class Meta:
        model = CropPlanting
        fields = ("crop_name", "crop_variety", "planting_date", "expected_harvest_date", "actual_harvest_date", "status", "notes", "yield_amount", "yield_unit")
        widgets = {"planting_date": DateInput(), "expected_harvest_date": DateInput(), "actual_harvest_date": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["crop_name"].initial = self.instance.crop.name
            self.fields["crop_variety"].initial = self.instance.crop.variety

    def save(self, commit=True):
        planting = super().save(commit=False)
        crop_name = self.cleaned_data["crop_name"].strip().title()
        crop_variety = self.cleaned_data["crop_variety"].strip().title()
        planting.crop, _ = Crop.objects.get_or_create(name=crop_name, variety=crop_variety)
        if commit:
            planting.save()
        return planting


class FarmActivityForm(forms.ModelForm):
    class Meta:
        model = FarmActivity
        fields = ("field", "planting", "activity_type", "activity_date", "details", "cost")
        widgets = {"activity_date": DateInput()}

    def __init__(self, *args, farm, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field"].queryset = farm.fields.exclude(status=Field.Status.ARCHIVED)
        self.fields["planting"].queryset = CropPlanting.objects.filter(field__farm=farm)


class FarmTaskForm(forms.ModelForm):
    class Meta:
        model = FarmTask
        fields = ("field", "title", "due_date", "status", "priority", "notes")
        widgets = {"due_date": DateInput()}

    def __init__(self, *args, farm, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field"].queryset = farm.fields.exclude(status=Field.Status.ARCHIVED)


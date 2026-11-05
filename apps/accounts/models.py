from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .validators import validate_profile_image


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude={"password"})
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        AGRICULTURALIST = "AGRICULTURALIST", "Agriculturalist"
        FARMER = "FARMER", "Farmer"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        BENGALI = "bn", "বাংলা"

    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FARMER, db_index=True)
    phone_number = models.CharField(max_length=24, blank=True)
    profile_image = models.ImageField(upload_to="profiles/%Y/%m/", blank=True, validators=[validate_profile_image])
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    district = models.CharField(max_length=80, blank=True)
    upazila = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["full_name", "email"]

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.full_name or self.email.split("@", 1)[0]


class FarmerProfile(models.Model):
    class Experience(models.TextChoices):
        NEW = "NEW", "New farmer"
        ONE_TO_FIVE = "1_5", "1-5 years"
        SIX_TO_TEN = "6_10", "6-10 years"
        ELEVEN_PLUS = "11_PLUS", "11+ years"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="farmer_profile")
    experience = models.CharField(max_length=16, choices=Experience.choices, default=Experience.NEW)
    preferred_area_unit = models.CharField(max_length=16, default="ACRE")
    bio = models.TextField(blank=True, max_length=1000)

    def __str__(self):
        return f"Farmer profile: {self.user.display_name}"


class AgriculturalistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agriculturalist_profile")
    specialization = models.CharField(max_length=160)
    qualifications = models.TextField(max_length=2000)
    organization = models.CharField(max_length=160, blank=True)
    license_number = models.CharField(max_length=80, blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)
    bio = models.TextField(blank=True, max_length=2000)
    is_approved = models.BooleanField(default=False, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Agriculturalist profile: {self.user.display_name}"


class AgriculturalistVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        MORE_INFO = "MORE_INFO", "More information requested"

    agriculturalist = models.ForeignKey(AgriculturalistProfile, on_delete=models.CASCADE, related_name="verifications")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="expert_reviews")
    notes = models.TextField(blank=True, max_length=2000)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    email_notifications = models.BooleanField(default=True)
    weather_alerts = models.BooleanField(default=True)
    consultation_updates = models.BooleanField(default=True)
    learning_updates = models.BooleanField(default=False)

    def __str__(self):
        return f"Preferences: {self.user.email}"

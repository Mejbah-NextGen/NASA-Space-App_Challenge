from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AgriculturalistProfile, FarmerProfile, User, UserPreference


@receiver(post_save, sender=User)
def create_role_profiles(sender, instance, created, **kwargs):
    if not created:
        return
    UserPreference.objects.get_or_create(user=instance)
    if instance.role == User.Role.FARMER:
        FarmerProfile.objects.get_or_create(user=instance)
    elif instance.role == User.Role.AGRICULTURALIST:
        AgriculturalistProfile.objects.get_or_create(
            user=instance,
            defaults={"specialization": "General agriculture", "qualifications": "Pending details"},
        )

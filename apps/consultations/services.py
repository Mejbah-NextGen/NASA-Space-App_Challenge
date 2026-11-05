from django.db import transaction
from django.utils import timezone

from apps.notifications.services import create_notification

from .models import ExpertAssignment, FarmDataConsent


@transaction.atomic
def assign_consultation(consultation, *, assigned_by=None, share_farm=False, consent_scope=FarmDataConsent.Scope.SUMMARY):
    if not consultation.agriculturalist_id:
        return None
    existing_assignment = ExpertAssignment.objects.filter(consultation=consultation).select_related("agriculturalist").first()
    previous_expert = existing_assignment.agriculturalist if existing_assignment else None
    is_reassignment = bool(previous_expert and previous_expert.pk != consultation.agriculturalist_id)
    defaults = {
        "farmer": consultation.farmer,
        "agriculturalist": consultation.agriculturalist,
        "assigned_by": assigned_by,
        "is_active": True,
        "ended_at": None,
    }
    if is_reassignment:
        defaults["assigned_at"] = timezone.now()
    assignment, _ = ExpertAssignment.objects.update_or_create(
        consultation=consultation,
        defaults=defaults,
    )
    if share_farm and consultation.farm_id:
        grant_farm_data_consent(consultation, scope=consent_scope)
    if is_reassignment:
        create_notification(
            previous_expert,
            kind="CONSULTATION_UPDATED",
            title="Consultation reassigned",
            body=f'Your assignment to "{consultation.title}" has ended.',
            target_url="/agriculturalist/questions/",
        )
    create_notification(
        consultation.agriculturalist,
        kind="CONSULTATION_ASSIGNED",
        title="New consultation assigned",
        body=f"{consultation.farmer.display_name} asked: {consultation.title}",
        target_url=f"/agriculturalist/questions/{consultation.pk}/",
    )
    return assignment


@transaction.atomic
def grant_farm_data_consent(consultation, *, scope=FarmDataConsent.Scope.SUMMARY):
    if not consultation.agriculturalist_id or not consultation.farm_id:
        raise ValueError("An assigned Agriculturalist and farm are required before sharing data.")
    if scope not in FarmDataConsent.Scope.values:
        raise ValueError("Invalid farm-data consent scope.")
    consent, _ = FarmDataConsent.objects.get_or_create(
        consultation=consultation,
        defaults={
            "farmer": consultation.farmer,
            "agriculturalist": consultation.agriculturalist,
            "farm": consultation.farm,
            "scope": scope,
        },
    )
    consent.farmer = consultation.farmer
    consent.agriculturalist = consultation.agriculturalist
    consent.farm = consultation.farm
    consent.scope = scope
    consent.revoked_at = None
    consent.full_clean()
    consent.save()
    create_notification(
        consultation.agriculturalist,
        kind="CONSULTATION_UPDATED",
        title="Farm data sharing granted",
        body=f'{consultation.farmer.display_name} shared {consultation.farm.name} for "{consultation.title}".',
        target_url=f"/agriculturalist/questions/{consultation.pk}/",
    )
    return consent


def notify_message(message):
    consultation = message.consultation
    recipient = consultation.agriculturalist if message.sender_id == consultation.farmer_id else consultation.farmer
    if recipient:
        create_notification(
            recipient,
            kind="EXPERT_REPLIED" if message.sender_id == consultation.agriculturalist_id else "CONSULTATION_MESSAGE",
            title="New consultation message",
            body=f"{message.sender.display_name} replied to {consultation.title}",
            target_url=(
                f"/farmer/consultations/{consultation.pk}/"
                if recipient.role == "FARMER"
                else f"/agriculturalist/questions/{consultation.pk}/"
            ),
        )

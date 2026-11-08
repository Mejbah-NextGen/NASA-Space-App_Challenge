from django.db import transaction
from django.utils import timezone

from apps.notifications.services import create_notification

from .models import Consultation, ExpertAssignment, FarmDataConsent


@transaction.atomic
def assign_consultation(consultation, *, assigned_by=None, share_farm=False, consent_scope=FarmDataConsent.Scope.SUMMARY):
    if not consultation.agriculturalist_id:
        return None
    existing_assignment = ExpertAssignment.objects.filter(consultation=consultation).select_related("agriculturalist").first()
    previous_expert = existing_assignment.agriculturalist if existing_assignment else None
    is_reassignment = bool(previous_expert and previous_expert.pk != consultation.agriculturalist_id)
    active_consent = FarmDataConsent.objects.filter(
        consultation=consultation,
        revoked_at__isnull=True,
    ).first()
    consent_is_stale = bool(
        active_consent
        and (
            active_consent.agriculturalist_id != consultation.agriculturalist_id
            or active_consent.farmer_id != consultation.farmer_id
            or active_consent.farm_id != consultation.farm_id
        )
    )
    if is_reassignment or consent_is_stale:
        FarmDataConsent.objects.filter(
            consultation=consultation,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
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
def close_consultation(consultation, *, status, closed_by):
    """Close a consultation and retire every access grant in one transaction."""
    terminal_statuses = {
        Consultation.Status.COMPLETED,
        Consultation.Status.CANCELLED,
        Consultation.Status.DECLINED,
    }
    if status not in terminal_statuses:
        raise ValueError("A consultation can only be closed with a terminal status.")

    consultation = (
        Consultation.objects.select_for_update()
        .select_related("farmer", "agriculturalist")
        .get(pk=consultation.pk)
    )
    if consultation.status in terminal_statuses:
        raise ValueError("This consultation is already closed.")
    if closed_by.pk not in {consultation.farmer_id, consultation.agriculturalist_id}:
        raise ValueError("Only a consultation participant may close it.")

    consultation.close(status)
    ExpertAssignment.objects.filter(
        consultation=consultation,
        is_active=True,
    ).update(is_active=False, ended_at=timezone.now())
    FarmDataConsent.objects.filter(
        consultation=consultation,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())

    recipient = (
        consultation.agriculturalist
        if closed_by.pk == consultation.farmer_id
        else consultation.farmer
    )
    if recipient:
        notification_title = {
            Consultation.Status.COMPLETED: "Consultation completed",
            Consultation.Status.DECLINED: "Consultation declined",
            Consultation.Status.CANCELLED: "Consultation closed",
        }[status]
        create_notification(
            recipient,
            kind="CONSULTATION_UPDATED",
            title=notification_title,
            body=consultation.title,
            target_url=(
                f"/farmer/consultations/{consultation.pk}/"
                if recipient.pk == consultation.farmer_id
                else f"/agriculturalist/questions/{consultation.pk}/"
            ),
        )
    return consultation


@transaction.atomic
def grant_farm_data_consent(consultation, *, scope=FarmDataConsent.Scope.SUMMARY):
    consultation = (
        Consultation.objects.select_for_update()
        .select_related("farmer", "agriculturalist", "farm")
        .get(pk=consultation.pk)
    )
    if consultation.status not in {Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE}:
        raise ValueError("Farm data can only be shared for an open assigned consultation.")
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

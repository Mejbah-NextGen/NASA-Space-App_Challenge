from django.conf import settings

from .models import AuditLog


SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "authorization"}


def record_audit(request, action, target=None, result=AuditLog.Result.SUCCESS, metadata=None):
    safe_metadata = {
        str(key): value
        for key, value in (metadata or {}).items()
        if str(key).lower() not in SENSITIVE_KEYS
    }
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "") if settings.TRUST_X_FORWARDED_FOR else ""
    address = (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
    return AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target_type=target.__class__.__name__ if target else "",
        target_identifier=str(getattr(target, "pk", "")) if target else "",
        result=result,
        metadata=safe_metadata,
        ip_address=address,
    )

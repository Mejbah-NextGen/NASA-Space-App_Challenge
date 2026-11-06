from django.conf import settings


def email_verification_enabled():
    """Return whether email ownership must be confirmed before account use."""
    return getattr(settings, "EMAIL_VERIFICATION_ENABLED", False)


def user_has_verified_email(user):
    """Treat email verification as satisfied while the feature is disabled."""
    return not email_verification_enabled() or bool(getattr(user, "is_verified", False))


def restrict_to_email_verified(queryset):
    """Apply the email-verification filter only when enforcement is enabled."""
    if email_verification_enabled():
        return queryset.filter(is_verified=True)
    return queryset

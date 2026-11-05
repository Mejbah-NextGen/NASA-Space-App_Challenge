from pathlib import Path

from django.core.exceptions import ValidationError


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def validate_profile_image(upload):
    if upload.size > 3 * 1024 * 1024:
        raise ValidationError("Profile images must be 3 MB or smaller.")
    content_type = getattr(upload, "content_type", "")
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")
    if Path(upload.name).suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")

from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
IMAGE_FORMAT_BY_SUFFIX = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
MAX_IMAGE_PIXELS = 20_000_000


def validate_profile_image(upload):
    if upload.size > 3 * 1024 * 1024:
        raise ValidationError("Profile images must be 3 MB or smaller.")
    content_type = getattr(upload, "content_type", "")
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")
    suffix = Path(upload.name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")
    position = upload.tell() if hasattr(upload, "tell") else 0
    try:
        upload.seek(0)
        image = Image.open(upload)
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError("Upload a valid JPEG, PNG, or WebP image.")
        if image.format != IMAGE_FORMAT_BY_SUFFIX[suffix]:
            raise ValidationError("The image content does not match its filename extension.")
        width, height = image.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ValidationError("Images must contain 20 megapixels or fewer.")
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("The uploaded file is not a valid image.") from exc
    finally:
        upload.seek(position)

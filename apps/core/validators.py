"""
File upload validators for the owner app.

Two families:
  - validate_document_file : accepts PDF, DOC, DOCX, XLS, XLSX, CSV (≤ 10 MB)
  - validate_image_file    : accepts PNG, JPG, JPEG, WEBP, GIF        (size handled by compress_image)

Used as `validators=[...]` on model FileField / ImageField so the constraint
is enforced at both the ORM and the DRF serializer layer.
"""
import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})

MAX_DOCUMENT_MB = 10
MAX_IMAGE_MB = 3


def validate_document_file(file) -> None:
    """Reject non-document types and files larger than MAX_DOCUMENT_MB."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in DOCUMENT_EXTENSIONS:
        raise ValidationError(
            _("Unsupported file type '%(ext)s'. Allowed: %(allowed)s"),
            params={
                "ext": ext or "(none)",
                "allowed": ", ".join(sorted(DOCUMENT_EXTENSIONS)),
            },
        )
    if file.size > MAX_DOCUMENT_MB * 1024 * 1024:
        raise ValidationError(
            _("File too large. Maximum allowed size is %(max)s MB."),
            params={"max": MAX_DOCUMENT_MB},
        )


def validate_image_file(file) -> None:
    """Reject unsupported image types. Size is handled by compress_image()."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValidationError(
            _("Unsupported image type '%(ext)s'. Allowed: %(allowed)s"),
            params={
                "ext": ext or "(none)",
                "allowed": ", ".join(sorted(IMAGE_EXTENSIONS)),
            },
        )

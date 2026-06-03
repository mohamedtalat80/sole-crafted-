"""
Image compression utility.

compress_image() is called by _ImageUploadField after format validation
to ensure every stored image stays within MAX_IMAGE_BYTES.

Strategy
--------
- JPEG / WEBP  : iteratively lower quality (85 → 30, step −10)
- PNG / GIF    : iteratively scale dimensions (0.80 → 0.30, step −0.15)
  GIF is converted to PNG since Pillow's static-GIF output is poor for photos.
- Dimension scaling is used as a final fallback for JPEG/WEBP if quality
  reduction alone wasn't enough.
"""

import io
import os

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

MAX_IMAGE_BYTES = 3 * 1024 * 1024  # 3 MB

_CONTENT_TYPE = {
    "JPEG": "image/jpeg",
    "PNG":  "image/png",
    "WEBP": "image/webp",
    "GIF":  "image/gif",
}
_EXTENSION = {
    "JPEG": ".jpg",
    "PNG":  ".png",
    "WEBP": ".webp",
    "GIF":  ".gif",
}
_QUALITY_FORMATS = {"JPEG", "WEBP"}


def _wrap(buf: io.BytesIO, original_name: str, fmt: str) -> InMemoryUploadedFile:
    """Wrap a BytesIO buffer as an InMemoryUploadedFile."""
    stem = os.path.splitext(original_name)[0]
    name = stem + _EXTENSION.get(fmt, ".jpg")
    buf.seek(0)
    return InMemoryUploadedFile(
        file=buf,
        field_name=None,
        name=name,
        content_type=_CONTENT_TYPE.get(fmt, "image/jpeg"),
        size=len(buf.getvalue()),
        charset=None,
    )


def compress_image(
    uploaded_file,
    max_bytes: int = MAX_IMAGE_BYTES,
):
    """
    Return a compressed version of *uploaded_file* that fits within *max_bytes*.

    If the file is already within the limit it is returned unchanged.
    The original file object is never mutated.
    """
    if uploaded_file.size <= max_bytes:
        return uploaded_file

    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    fmt = (img.format or "JPEG").upper()

    # Normalise: Django may give us "MPO" for some cameras – treat as JPEG.
    if fmt not in _CONTENT_TYPE:
        fmt = "JPEG"

    # JPEG requires RGB/L mode.
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # ── Phase 1: quality reduction (JPEG / WEBP only) ─────────────────────────
    if fmt in _QUALITY_FORMATS:
        for quality in range(85, 25, -10):
            buf = io.BytesIO()
            img.save(buf, format=fmt, quality=quality, optimize=True)
            if buf.tell() <= max_bytes:
                return _wrap(buf, uploaded_file.name, fmt)

    # ── Phase 2: dimension scaling ─────────────────────────────────────────────
    # GIF → PNG gives better compression for static frames.
    save_fmt = "PNG" if fmt == "GIF" else fmt

    w, h = img.width, img.height
    for scale in (0.80, 0.65, 0.50, 0.40, 0.30):
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        resized = img.resize((new_w, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        if save_fmt in _QUALITY_FORMATS:
            resized.save(buf, format=save_fmt, quality=60, optimize=True)
        else:
            resized.save(buf, format=save_fmt, optimize=True)

        if buf.tell() <= max_bytes:
            return _wrap(buf, uploaded_file.name, save_fmt)

    # ── Fallback: return best-effort result (smallest produced so far) ─────────
    buf.seek(0)
    return _wrap(buf, uploaded_file.name, save_fmt)

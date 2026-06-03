from rest_framework import serializers
from apps.core.validators import validate_image_file, validate_document_file
from apps.core.image_utils import compress_image

class _ImageUploadField(serializers.ImageField):
    """
    ImageField that validates the image format then auto-compresses
    anything over 3 MB before it reaches the service/repository layer.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault("help_text", "PNG / JPG / JPEG / WEBP — images over 3 MB are auto-compressed")
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        file = super().to_internal_value(data)
        validate_image_file(file)          # format check only
        return compress_image(file)        # transparent size reduction if needed

class _DocumentUploadField(serializers.FileField):
    """FileField that runs validate_document_file on upload."""
    def __init__(self, **kwargs):
        kwargs.setdefault("help_text", "PDF / DOC / DOCX / XLS / XLSX / CSV — max 10 MB")
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        file = super().to_internal_value(data)
        validate_document_file(file)
        return file

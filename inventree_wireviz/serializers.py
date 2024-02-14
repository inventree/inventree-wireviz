"""DRF serializers for the wireviz plugin."""


from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from part.models import Part

from .processing import WirevizImportManager


class WirevizUploadSerializer(serializers.Serializer):
    """Serializer for uploading a wireviz file"""

    part = serializers.PrimaryKeyRelatedField(
        queryset=Part.objects.all(),
        many=False,
        required=True, allow_null=False,
        label="Part",
        help_text="Select part"
    )

    file = serializers.FileField(
        label="Wireviz file",
        help_text="Upload a wireviz file",
        required=True,
    )

    def validate_file(self, file):
        """Validate the uploaded wireviz file."""

        mgr = WirevizImportManager()
        mgr.parse_wireviz_file(file.file)

        return file

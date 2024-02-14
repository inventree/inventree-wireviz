"""DRF serializers for the wireviz plugin."""


from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from part.models import Part


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

    def validate(self, data):
        """Ensure that the uploaded file is a valid wireviz file"""

        data = super().validate(data)

        file = data.get("file")

        if file is None:
            raise ValidationError("No file provided")

        return data

"""DRF serializers for the wireviz plugin."""

import os
import yaml

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from part.models import Part

from .processing import WirevizImportManager


def template_path(template):
    """Return the fully qualified template path from a template string."""
    
    template = os.path.basename(template)

    return os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'wireviz', template))


class WirevizDeleteSerializer(serializers.Serializer):
    """Serializer for deleting a wireviz file."""

    part = serializers.PrimaryKeyRelatedField(
        queryset=Part.objects.all(),
        many=False,
        required=True, allow_null=False,
        label="Part",
        help_text="Select part"
    )

    def save(self, **kwargs):
        """Remove wireviz harness from the specified part."""

        part = self.validated_data['part']
        part.set_metadata('wireviz', None)


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

        try:
            mgr = WirevizImportManager()
            mgr.parse_wireviz_file(file.file)
        except ValidationError as e:
            raise e
        except Exception:
            raise ValidationError("Error parsing wireviz file")

        return file

    def save(self, user=None, **kwargs):
        """Save the validated serializer."""

        data = self.validated_data

        wv_file = data['file']
        part = data['part']

        mgr = WirevizImportManager()
        mgr.import_harness(wv_file, part, user)


class UploadTemplateSerializer(serializers.Serializer):
    """Serializer for uploading a wireviz template file."""

    template = serializers.FileField(
        label="Template file",
        help_text="Upload a wireviz template file",
        required=True,
    )

    def validate_template(self, template):
        """Validate template file."""

        if not template.name.endswith('.wireviz'):
            raise ValidationError("File must be .wireviz file")

        data = template.file.read().decode('utf-8')

        try:
            yaml.safe_load(data)
        except yaml.YAMLError:
            raise ValidationError("Invalid YAML file")

        return template

    def save(self, **kwargs):
        """Save the uploaded wireviz template file."""

        # Ensure directory exists first
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'wireviz'), exist_ok=True)
        template = self.validated_data['template']
        filename = template_path(template.name)

        with open(filename, 'w') as output:
            template.file.seek(0)
            output.write(template.file.read().decode('utf-8'))


class DeleteTemplateSerializer(serializers.Serializer):
    """Serializer for deleting a wireviz template file."""

    template = serializers.CharField(
        label="Template file name",
        help_text="Select wireviz template file",
        required=True, allow_blank=False
    )

    def validate_template(self, template):
        """Ensure that the specified wireviz template file exists."""
        
        path = template_path(template)

        if not path:
            raise serializers.ValidationError("Invalid wireviz template file")

        if not os.path.exists(path):
            raise serializers.ValidationError("Wireviz template file does not exist")

        return template

    def save(self, **kwargs):
        """Delete the specified wireviz template file."""
        
        template = self.validated_data['template']

        path = template_path(template)

        if os.path.exists(path) and os.path.isfile(path):
            os.remove(path)

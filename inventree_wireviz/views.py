"""DRF views for the wireviz plugin"""

from rest_framework import permissions
from rest_framework.response import Response
from InvenTree.mixins import CreateAPI

from .serializers import WirevizDeleteSerializer, WirevizUploadSerializer


class UploadWirevizView(CreateAPI):
    """View for uploading a new wireviz file."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WirevizUploadSerializer

    def post(self, request, *args, **kwargs):
        """Handle POST request for uploading a new wireviz file."""

        serializer = WirevizUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)

        return Response(serializer.data, status=201)


class DeleteWirevizView(CreateAPI):
    """View for deleting a wireviz file."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WirevizDeleteSerializer

    def post(self, request, *args, **kwargs):
        """Handle POST request for deleting a wireviz file."""

        serializer = WirevizDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data, status=201)

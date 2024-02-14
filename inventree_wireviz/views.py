"""DRF views for the wireviz plugin"""

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import WirevizUploadSerializer



class UploadWirevizView(APIView):
    """View for uploading a new wireviz file"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Handle POST request for uploading a new wireviz file."""

        serializer = WirevizUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)

        return Response(serializer.data, status=201)



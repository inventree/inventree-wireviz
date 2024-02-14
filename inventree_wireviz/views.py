"""DRF views for the wireviz plugin"""

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response


class UploadWirevizView(APIView):
    """View for uploading a new wireviz file"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        print("POST:", request)
        print("args:", *args)
        print("kwargs:", **kwargs)

        return Response({"status": "ok"})



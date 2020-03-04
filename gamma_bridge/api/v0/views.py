from django.http import HttpResponseForbidden, JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from enrollment.views import ApiKeyPermissionMixIn
from .serializers import EventTypesSerializer


class GammaEventsView(APIView, ApiKeyPermissionMixIn):
    """
    Gamma Events view
    """

    def get(self, request):
        """
        Return the list of events that could be processed.
        """
        if not self.has_api_key_permissions(request):
            return HttpResponseForbidden()

        serializer = EventTypesSerializer()
        return JsonResponse(data=serializer.data, safe=False, status=status.HTTP_200_OK)

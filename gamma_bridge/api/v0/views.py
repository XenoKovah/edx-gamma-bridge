from django.http import HttpResponseForbidden, JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from openedx.core.djangoapps.enrollments.views import ApiKeyPermissionMixIn
from xmodule.modulestore.django import modulestore


class GammaCoursesView(APIView, ApiKeyPermissionMixIn):
    """
    Gamma Courses view.
    """

    def get(self, request):
        """
        Return the list of courses id.
        """
        if not self.has_api_key_permissions(request):
            return HttpResponseForbidden()

        courses = modulestore().get_courses()
        data = [str(course.id) for course in courses]
        return JsonResponse(data=data, safe=False, status=status.HTTP_200_OK)


class GammaOrganizationsView(APIView, ApiKeyPermissionMixIn):
    """
    Gamma Organizations view.
    """

    def get(self, request):
        """
        Return the list of organizations.
        """
        if not self.has_api_key_permissions(request):
            return HttpResponseForbidden()

        courses = modulestore().get_courses()
        orgs = set([course.org for course in courses])
        return JsonResponse(data=list(orgs), safe=False, status=status.HTTP_200_OK)

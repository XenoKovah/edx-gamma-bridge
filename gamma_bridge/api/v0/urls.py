from django.urls import re_path

from .views import GammaCoursesView, GammaOrganizationsView

urlpatterns = [
    re_path(r'courses/$', GammaCoursesView.as_view(), name="gamma-course-list"),
    re_path(r'organizations/$', GammaOrganizationsView.as_view(), name="gamma-organization-list"),
]

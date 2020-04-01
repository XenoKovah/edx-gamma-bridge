from django.conf.urls import include, url

from .views import GammaEventsView, GammaCoursesView, GammaOrganizationsView

urlpatterns = [
    url(r'tracking-events-list/$', GammaEventsView.as_view(), name="gamma-events-list"),
    url(r'courses/$', GammaCoursesView.as_view(), name="gamma-course-list"),
    url(r'organizations/$', GammaOrganizationsView.as_view(), name="gamma-organization-list"),

]

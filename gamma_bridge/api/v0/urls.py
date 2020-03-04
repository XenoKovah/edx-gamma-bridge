from django.conf.urls import include, url

from .views import GammaEventsView

urlpatterns = [
    url(r'tracking-events-list/', GammaEventsView.as_view(), name="gamma-events-list"),
]

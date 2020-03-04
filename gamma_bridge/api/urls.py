"""
Root API URLs.

All API URLs should be versioned, so urlpatterns should only
contain namespaces for the active versions of the API.
"""
from django.conf.urls import include, url

urlpatterns = [
    url(r'v0/',  include(('gamma_bridge.api.v0.urls', 'api'), namespace='v0'))
]

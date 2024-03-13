"""
Root API URLs.

All API URLs should be versioned, so urlpatterns should only
contain namespaces for the active versions of the API.
"""
from os.path import join

from django.conf import settings
from django.urls import include, re_path
from django.views.static import serve

urlpatterns = [
    re_path(r'v0/',  include(('gamma_bridge.api.v0.urls', 'api'), namespace='v0')),
]


def onesignal_js_with_header(request, *args, **kwargs):
    """
    Add 'service-worker-allowed' header for static files.

    OneSignal workers should be served with the header if they are not
    accessible from site root. Is used for devstack only. For production,
    OneSignal workers should be set up with static server options.
    """
    response = serve(request, *args, document_root='/',
                     path=join(settings.GAMMA_BRIDGE_BASE_DIR, 'static', kwargs.pop('script')), **kwargs)
    response['service-worker-allowed'] = '/'
    return response


if getattr(settings, 'GAMMA_DEVSTACK', False):
    urlpatterns.extend([
        re_path(r'^OneSignalSDKWorker.js$', onesignal_js_with_header, {'script': 'OneSignalSDKWorker.js'}),
        re_path(r'^OneSignalSDKUpdaterWorker.js$', onesignal_js_with_header, {'script': 'OneSignalSDKUpdaterWorker.js'}),
    ])

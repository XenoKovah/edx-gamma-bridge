from django.conf import settings


def pytest_configure(config):
    # The statement modules import django.contrib.auth models at import time, so
    # the auth app must be installed and a database configured (statements
    # resolve the user's signup source); pytest-django picks this up and runs
    # django.setup() itself.
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        DEBUG=False,
        USE_TZ=True,
        FEATURES={'RG_GAMIFICATION': {'IGNORED_EVENT_TYPES': []}},
    )

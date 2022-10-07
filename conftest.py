from django.conf import settings


def pytest_configure(config):
    settings.configure()

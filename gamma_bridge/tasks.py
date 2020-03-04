"""Celery tasks for working asynchronously."""
import socket

from celery.task import task
from django.conf import settings

from gamma_bridge.exceptions import GammaConnectionError
from gamma_bridge.storage_logger import StorageLogger
from gamma_bridge.storage import GammaStorage


@task(bind=True)
def publish_event_to_gamma(self, params, event, sleep_interval):
    """
    Send event to GammaStorage.
    """
    storage = GammaStorage(**params)
    exception = None
    try:
        storage.save(event)
    except socket.gaierror as e:  # can't connect at all, no response
        exception = GammaConnectionError(message=event)

    if storage.response_data is not None and not exception:
        StorageLogger.logging(storage, event)
    else:
        self.retry(
            kwargs={"sleep_interval": sleep_interval * 2},
            countdown=sleep_interval,
            max_retries=settings.GAMMA_CELERY_MAX_RETRIES,
            exc=exception,
            throw=bool(exception)
        )

"""Celery tasks for working asynchronously."""
import socket

from celery import shared_task
from django.conf import settings

from gamma_bridge.exceptions import GammaConnectionError
from gamma_bridge.storage_logger import StorageLogger
from gamma_bridge.storage import GammaStorage

GAMIFICATION_CONF = settings.FEATURES.get('RG_GAMIFICATION', {})


@shared_task(bind=True)
def publish_event_to_gamma(self, event, sleep_interval=settings.GAMMA_FIRST_SLEEP_INTERVAL):
    """
    Send event to GammaStorage.
    """
    storage = GammaStorage(
        enabled=GAMIFICATION_CONF.get('ENABLED'),
        endpoint=GAMIFICATION_CONF.get('RG_GAMIFICATION_ENDPOINT'),
        secret=GAMIFICATION_CONF.get('SECRET'),
        key=GAMIFICATION_CONF.get('KEY')
    )
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

"""Gamification Client to send payload data."""
import logging

from django.conf import settings

from gamma_bridge.tasks import publish_event_to_gamma

LOGGER = logging.getLogger(__name__)

GAMIFICATION_CONF = settings.FEATURES.get('RG_GAMIFICATION')


class GamificationPublisher(object):
    """
    Gamification publisher.

    Work with Gamma default storage to interact with storage backend.
    """
    def publish_event(self, event):
        """
        params:
        event gamification event
        """
        publish_event_to_gamma(GAMIFICATION_CONF, event, settings.GAMMA_FIRST_SLEEP_INTERVAL)


publisher = GamificationPublisher()

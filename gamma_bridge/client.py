"""Gamification Client to send payload data."""
import logging

from gamma_bridge.tasks import publish_event_to_gamma

LOGGER = logging.getLogger(__name__)


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
        publish_event_to_gamma.delay(event)


publisher = GamificationPublisher()

import re

from django.conf import settings

from gamma_bridge.converter import TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP


class EventTypesSerializer(object):
    @property
    def data(self):
        ignored_events = settings.FEATURES.get('RG_GAMIFICATION', {}).get('IGNORED_EVENT_TYPES', [])
        events_map = [
            {'event_type': re.sub('\.+', '_', key),
             'verbose_name': value['verbose_name']}
            for key, value in TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP.items()
            if key not in ignored_events
        ]
        return events_map

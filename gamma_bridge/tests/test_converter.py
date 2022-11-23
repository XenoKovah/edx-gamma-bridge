import pytest

from django.test import override_settings

from gamma_bridge.converter import to_gamma, TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP
from gamma_bridge.tests.utils.helpers import load_params_from_json


class TestConverter:

    @pytest.mark.parametrize(
        "entry",
        load_params_from_json('gamma_bridge/tests/resources/events.json'),
    )
    @pytest.mark.unittests
    @override_settings(FEATURES={ 'RG_GAMIFICATION': { 'IGNORED_EVENT_TYPES': [] }})
    def test_to_gamma(self, entry):
        """
        Test setting/getting progress documents.
        """
        result = to_gamma(entry)
        event_type = entry['event_type']
        if event_type in TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP:
            assert isinstance(result, TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP[event_type]['statement_class'])
        else:
            assert result is None

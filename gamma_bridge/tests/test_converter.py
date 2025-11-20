import sys

import pytest
from unittest import mock
from django.test import override_settings

import gamma_bridge.converter as converter
from gamma_bridge import statements
from gamma_bridge.tests.utils.helpers import load_params_from_json


class DummyStatement(statements.base.BaseGammaEvent):
    pass


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
        result = converter.to_gamma(entry)
        event_type = entry['event_type']
        if event_type in converter.TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP:
            assert isinstance(result, converter.TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP[event_type]['statement_class'])
        else:
            assert result is None

    @pytest.mark.parametrize("event_type", ["custom.event", "another.event"])
    def test_get_statement_class_from_extension_valid(self, settings, event_type):
        """Ensure valid dynamic imports return proper class and cache works."""
        test_path = "gamma_bridge.tests.test_converter.DummyStatement"
        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            event_type: {"statement_class": test_path, "verbose_name": "Test Event"}
        }
        cls = converter.get_statement_class_from_extension(event_type)
        assert cls is DummyStatement

    def test_get_statement_class_from_extension_invalid_import(self, settings):
        """Invalid module path should log error and return None."""
        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            "bad.event": {"statement_class": "nonexistent.module.Class"}
        }
        with mock.patch.object(converter.LOGGER, "error") as mock_log:
            cls = converter.get_statement_class_from_extension("bad.event")
        assert cls is None
        mock_log.assert_called_once()
        assert "Failed to import statement class" in mock_log.call_args[0][0]

    def test_get_statement_class_from_extension_invalid_class(self, monkeypatch, settings):
        """If imported class does not subclass BaseGammaEvent, return None."""

        class NotGammaEvent:
            pass

        module = mock.MagicMock()
        module.NotGammaEvent = NotGammaEvent
        monkeypatch.setitem(sys.modules, "fake.module", module)

        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            "fake.event": {"statement_class": "fake.module.NotGammaEvent"}
        }

        with mock.patch.object(converter.LOGGER, "warning") as mock_warn:
            cls = converter.get_statement_class_from_extension("fake.event")
        assert cls is None
        mock_warn.assert_called_once()
        assert "does not inherit from BaseGammaEvent" in mock_warn.call_args[0][0]

    def test_get_statement_class_from_extension_invalid_path(self, settings):
        """Invalid dotted path format should trigger ValueError and warning."""
        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            "invalid.event": {"statement_class": "BadPathWithoutDot"}
        }

        with mock.patch.object(converter.LOGGER, "warning") as mock_warn:
            cls = converter.get_statement_class_from_extension("invalid.event")
        assert cls is None
        mock_warn.assert_called_once()
        assert "Invalid class path format" in mock_warn.call_args[0][0]

    @mock.patch("gamma_bridge.statements.base.BaseGammaEvent.__init__", return_value=None)
    def test_to_gamma_uses_extension(self, mock_init, settings):
        """If event not found in default map, to_gamma should use extension."""
        event_type = "custom.dynamic.event"
        dummy_path = "gamma_bridge.tests.test_converter.DummyStatement"

        settings.FEATURES = {"RG_GAMIFICATION": {"IGNORED_EVENT_TYPES": []}}
        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            event_type: {"statement_class": dummy_path, "verbose_name": "Dynamic event"}
        }

        event = {"event_type": event_type, "username": "user1", "event": {}}

        cls = converter.get_statement_class_from_extension(event_type)
        assert cls is DummyStatement
        result = converter.to_gamma(event)
        assert isinstance(result, cls)

    def test_to_gamma_untracked_event_logs(self, settings):
        """Untracked events should log and return None."""
        settings.FEATURES = {"RG_GAMIFICATION": {"IGNORED_EVENT_TYPES": []}}
        settings.TRACKING_EVENTS_TO_GAMMA_EXTENSION = {}

        event = {"event_type": "unknown.event", "username": "x", "event": {}}
        with mock.patch.object(converter.LOGGER, "debug") as mock_debug:
            result = converter.to_gamma(event)
        assert result is None
        mock_debug.assert_called()

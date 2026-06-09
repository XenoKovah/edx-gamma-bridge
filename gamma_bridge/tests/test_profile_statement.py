from unittest import mock

import pytest
from django.test import override_settings

from gamma_bridge.converter import to_gamma
from gamma_bridge.statements.profile import (
    PUBLIC_VISIBILITY_VALUE,
    SETTING_TO_GAMMA_EVENT,
    ProfileSettingStatement,
    _is_set,
)


def make_settings_changed_event(setting, new, old=None, username='learner1'):
    """Build an `edx.user.settings.changed` tracking event like the LMS emits."""
    return {
        'name': 'edx.user.settings.changed',
        'event_type': 'edx.user.settings.changed',
        'username': username,
        'context': {'user_id': 7, 'course_id': '', 'org_id': ''},
        'event': {
            'setting': setting,
            'old': old,
            'new': new,
            'truncated': [],
            'user_id': 7,
            'table': 'auth_userprofile',
        },
    }


@pytest.fixture(autouse=True)
def _no_db_user():
    """Avoid the DB lookup BaseGammaEvent.__init__ does for the signup source."""
    with mock.patch('gamma_bridge.statements.base.User') as user_model:
        user_model.objects.get.return_value.usersignupsource_set.first.return_value = None
        yield


@override_settings(FEATURES={'RG_GAMIFICATION': {'IGNORED_EVENT_TYPES': []}})
class TestProfileSettingStatement:

    @pytest.mark.unittests
    @pytest.mark.parametrize('setting, new, expected_type', [
        ('bio', 'Hello, world', 'edx_profile_about_me_set'),
        ('country', 'US', 'edx_profile_location_set'),
        ('level_of_education', 'm', 'edx_profile_education_set'),
        ('language_proficiencies', [{'code': 'en'}], 'edx_profile_language_set'),
        ('profile_image_uploaded_at', '2026-06-09T12:00:00+00:00', 'edx_profile_image_added'),
    ])
    def test_rewardable_settings_map_to_their_event_type(self, setting, new, expected_type):
        result = to_gamma(make_settings_changed_event(setting, new))
        assert isinstance(result, ProfileSettingStatement)
        assert result.data['event_type'] == expected_type

    @pytest.mark.unittests
    def test_visibility_name_public_fires_name_made_public(self):
        result = to_gamma(make_settings_changed_event('visibility.name', PUBLIC_VISIBILITY_VALUE))
        assert isinstance(result, ProfileSettingStatement)
        assert result.data['event_type'] == 'edx_profile_name_made_public'

    @pytest.mark.unittests
    @pytest.mark.parametrize('value', ['private', 'custom', '', None])
    def test_visibility_name_non_public_is_ignored(self, value):
        # Only an explicit share-with-everyone makes the name public; anything
        # else (incl. the account_privacy mode value 'custom') is not the signal.
        assert to_gamma(make_settings_changed_event('visibility.name', value)) is None

    @pytest.mark.unittests
    def test_profile_image_removed_is_ignored(self):
        # Deleting a profile image writes profile_image_uploaded_at = None.
        assert to_gamma(make_settings_changed_event('profile_image_uploaded_at', None)) is None

    @pytest.mark.unittests
    @pytest.mark.parametrize('setting', ['bio', 'country', 'level_of_education', 'language_proficiencies'])
    @pytest.mark.parametrize('empty', [None, '', '   ', [], 'null'])
    def test_cleared_values_are_ignored(self, setting, empty):
        assert to_gamma(make_settings_changed_event(setting, empty)) is None

    @pytest.mark.unittests
    @pytest.mark.parametrize('setting', ['gender', 'year_of_birth', 'account_privacy', 'time_zone', 'mailing_address'])
    def test_non_rewardable_settings_are_ignored(self, setting):
        assert to_gamma(make_settings_changed_event(setting, 'whatever')) is None

    @pytest.mark.unittests
    def test_uid_is_stable_per_user_and_milestone(self):
        first = to_gamma(make_settings_changed_event('bio', 'first version'))
        second = to_gamma(make_settings_changed_event('bio', 'edited later'))
        # Same user + same milestone => same uid, so the badge is awarded once.
        assert first.data['uid'] == second.data['uid']

        other_user = to_gamma(make_settings_changed_event('bio', 'hi', username='someone_else'))
        assert other_user.data['uid'] != first.data['uid']

    @pytest.mark.unittests
    def test_payload_accepts_json_string_event(self):
        import json
        event = make_settings_changed_event('country', 'DE')
        event['event'] = json.dumps(event['event'])
        result = to_gamma(event)
        assert isinstance(result, ProfileSettingStatement)
        assert result.data['event_type'] == 'edx_profile_location_set'


@pytest.mark.unittests
@pytest.mark.parametrize('value, expected', [
    (None, False),
    ('', False),
    ('   ', False),
    ('null', False),
    ('[]', False),
    ([], False),
    ({}, False),
    ('US', True),
    ('m', True),
    (['en'], True),
    ([{'code': 'en'}], True),
    ('Some bio text', True),
])
def test_is_set(value, expected):
    assert _is_set(value) is expected


@pytest.mark.unittests
def test_setting_map_matches_documented_events():
    assert set(SETTING_TO_GAMMA_EVENT.values()) == {
        'edx_profile_name_made_public',
        'edx_profile_image_added',
        'edx_profile_education_set',
        'edx_profile_location_set',
        'edx_profile_language_set',
        'edx_profile_about_me_set',
    }

"""Statement for Open edX profile / account settings changes.

Open edX emits a single tracking event, ``edx.user.settings.changed``, for every
account or preference field a learner edits (bio, country, level_of_education,
language_proficiencies, the ``profile_image_uploaded_at`` timestamp written when
a profile picture is uploaded, the ``visibility.name`` preference, etc.). The
specific field is carried in the event payload's ``setting`` key, with the new
value in ``new``.

The bridge maps each *rewardable* setting onto its own Gamma ``event_type`` so a
badge rule can be wired to it independently, and ignores every other setting via
``is_allowed_to_save``. The Gamma event names below must match the
``EdxCommonEventTypes`` enum in the gamma repo.
"""
import json

from .base import BaseGammaEvent

# Open edX ``setting`` name -> Gamma event_type a badge rule can target.
SETTING_TO_GAMMA_EVENT = {
    'visibility.name': 'edx_profile_name_made_public',
    'profile_image_uploaded_at': 'edx_profile_image_added',
    'level_of_education': 'edx_profile_education_set',
    'country': 'edx_profile_location_set',
    'language_proficiencies': 'edx_profile_language_set',
    'bio': 'edx_profile_about_me_set',
}

# The per-field visibility value that means "shared with everyone". A learner's
# real name is publicly visible only when ``visibility.name`` is set to this --
# which in the profile MFE happens in the ``account_privacy='custom'`` mode the
# MFE migrates everyone to. (Note: ``account_privacy='all_users'`` deliberately
# EXCLUDES the name from the shared set, so the "name is public" signal is keyed
# on ``visibility.name`` alone, not on the overall profile-public toggle.)
PUBLIC_VISIBILITY_VALUE = 'all_users'

# String forms that should be treated as "no value set".
_EMPTY_SENTINELS = {'', 'none', 'null', '[]', '{}'}

# Fallback type used only for settings we do not reward; such statements are
# dropped by ``is_allowed_to_save`` before they are ever published.
_IGNORED_EVENT_TYPE = 'edx_user_settings_changed_ignored'


def _is_set(value):
    """Return ``True`` when ``value`` represents a non-empty setting value.

    Handles native types (``None`` / ``list`` / ``dict``) as well as their
    stringified forms, since ``edx.user.settings.changed`` values are passed
    through largely unserialized.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _EMPTY_SENTINELS
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


class ProfileSettingStatement(BaseGammaEvent):
    """Turn an ``edx.user.settings.changed`` event into a per-setting Gamma event."""

    @staticmethod
    def _payload(event):
        payload = event.get('event', {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (ValueError, TypeError):
                payload = {}
        return payload if isinstance(payload, dict) else {}

    def get_type(self, event):
        """Map the changed ``setting`` to its Gamma event_type."""
        setting = self._payload(event).get('setting')
        return SETTING_TO_GAMMA_EVENT.get(setting, _IGNORED_EVENT_TYPE)

    def get_uid(self, event):
        """Stable per (gamma event_type, user).

        A given profile milestone is recorded once, so re-editing the same field
        does not re-award the badge. (The first qualifying change is what counts.)
        """
        return '{}:{}'.format(self.get_type(event), self.get_username(event))

    def get_course_id(self, event):
        return ''

    def get_org(self, event):
        return ''

    def is_allowed_to_save(self, event):
        """Only forward rewardable settings, and only when actually populated."""
        payload = self._payload(event)
        setting = payload.get('setting')
        if setting not in SETTING_TO_GAMMA_EVENT:
            return False

        new_value = payload.get('new')
        if setting == 'visibility.name':
            return str(new_value).strip() == PUBLIC_VISIBILITY_VALUE
        return _is_set(new_value)

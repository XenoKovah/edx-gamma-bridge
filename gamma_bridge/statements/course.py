import json
import logging
import re

from django.conf import settings

from .base import BaseGammaEvent, validate_event_fields

LOGGER = logging.getLogger(__name__)

# Allowlist notes that mark a certificate granted because the learner completed the beta
# of the class. These are the notes OST2 uses: "completed beta", "finished beta",
# "completed beta (under different email)" and "beta->p completion migration ...".
# Override with FEATURES['RG_GAMIFICATION']['BETA_COMPLETION_ALLOWLIST_NOTE_REGEX'].
DEFAULT_BETA_COMPLETION_NOTE_REGEX = r'\b(?:completed|finished)\s+beta\b|\bbeta\s*->\s*p\s+completion\b'


def allowlist_entry_notes(user_id, course_id):
    """
    Return the notes of the learner's active certificate allowlist entry for this run, or None.
    """
    # LMS models, imported here so the bridge (and its tests) load without edx-platform.
    from lms.djangoapps.certificates.models import CertificateAllowlist  # pylint: disable=import-outside-toplevel
    from opaque_keys.edx.keys import CourseKey  # pylint: disable=import-outside-toplevel

    entry = CertificateAllowlist.objects.filter(
        user_id=user_id,
        course_id=CourseKey.from_string(course_id),
        allowlist=True,
    ).first()
    return entry.notes if entry else None


class BaseCourse(BaseGammaEvent):
    def get_uid(self, event):
        event_dict = event.get('event', {})
        validate_event_fields(event_dict, ('course_id', 'user_id', 'mode'))
        uid = '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            event_dict.get('course_id'),
            event_dict.get('user_id'),
            event_dict.get('mode')
        )
        return uid

    def is_allowed_to_save(self, event):
        return True


class CourseEnrollmentStatement(BaseCourse):
    pass


class CourseCompletionStatement(BaseCourse):
    """
    Course certificate generation event.

    When a certificate is generated, a record is created in the
    certificates_generatedcertificate table, triggering an
    edx.certificate.created event.

    A certificate allowlisted because the learner completed the beta of the
    class is sent with ``beta_completion: True``; gamma grades it Gold whatever
    its timing. Allowlisted and earned certificates emit the same tracking
    event, so the allowlist entry and its note are read here.

    Event source: server
    """

    def __init__(self, event, *args, **kwargs):
        super().__init__(event, *args, **kwargs)
        if self.is_beta_completion(event):
            self.data['beta_completion'] = True

    @staticmethod
    def is_beta_completion(event):
        """
        Whether this certificate was allowlisted because the learner completed the class's beta.

        Any failure reads as "no": the certificate is still forwarded, and graded by timing.
        """
        event_dict = event.get('event', {})
        try:
            notes = allowlist_entry_notes(event_dict.get('user_id'), event_dict.get('course_id'))
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception('Could not read the certificate allowlist for %r', event_dict)
            return False
        pattern = settings.FEATURES.get('RG_GAMIFICATION', {}).get(
            'BETA_COMPLETION_ALLOWLIST_NOTE_REGEX', DEFAULT_BETA_COMPLETION_NOTE_REGEX,
        )
        return bool(notes and re.search(pattern, notes, re.IGNORECASE))

    def get_uid(self, event):
        event_dict = event.get('event', {})

        validate_event_fields(event_dict,
            ('course_id',
             'user_id',
             'certificate_id'))

        return '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            event_dict.get('course_id'),
            event_dict.get('user_id'),
            event_dict.get('certificate_id'),
        )


class CourseStudentNotesStatement(BaseCourse):
    def get_uid(self, event):

        event_dict = event.get('event', {})
        if not isinstance(event_dict, dict):
            event_dict = json.loads(event_dict)

        validate_event_fields(event_dict, ('note_id', ))
        return event_dict['note_id']


class BookmarkAddedStatement(BaseCourse):

    def get_uid(self, event):
        event_dict = event.get('event', {})
        validate_event_fields(event_dict, ('bookmark_id', ))

        return event_dict['bookmark_id']

    def get_course_id(self, event):
        return event.get('event', {}).get('course_id', '')

    def get_org(self, event):
        regex = r"^course-v1:([^+]+)"
        if result := re.match(regex, self.get_course_id(event)):
            return result.group(1)

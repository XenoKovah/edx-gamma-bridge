from unittest import mock

import pytest
from django.test import override_settings

from gamma_bridge.converter import TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP
from gamma_bridge.statements.base import BaseGammaEvent
from gamma_bridge.statements.course import CourseCompletionStatement

COURSE = 'course-v1:OpenSecurityTraining2+Arch1001_x86-64_Asm+2021_v1'
NOTES = 'gamma_bridge.statements.course.allowlist_entry_notes'


def make_certificate_event(user_id=5, course_id=COURSE):
    """
    Shape mirrors a real edx.certificate.created tracking-log entry (certificates.utils.emit_certificate_event).
    """
    return {
        'event_type': 'edx.certificate.created',
        'username': 'learner',
        'context': {'course_id': course_id, 'org_id': 'OpenSecurityTraining2', 'user_id': user_id},
        'event': {
            'user_id': user_id,
            'course_id': course_id,
            'certificate_id': '0123456789abcdef0123456789abcdef',
            'enrollment_mode': 'honor',
            'generation_mode': 'batch',
            'certificate_url': 'https://p.ost2.fyi/certificates/0123456789abcdef0123456789abcdef',
        },
    }


class TestCourseCompletionStatement:

    @pytest.mark.unittests
    def test_mapped_in_converter(self):
        entry = TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP['edx.certificate.created']
        assert entry['statement_class'] is CourseCompletionStatement

    @pytest.mark.unittests
    @pytest.mark.parametrize(
        'notes, expected',
        [
            ('completed beta', True),
            ('Completed beta', True),
            ('finished beta', True),
            ('completed beta (under different email)', True),
            ('beta->p completion migration 2026-06-14 catA', True),
            ('beta->p completion migration 2026-06-14 dbg3011 catA', True),
            ('Extra quiz question added after completion but still 94% complete', False),
            ('test to see how it would work for others', False),
            ('', False),
            (None, False),
        ],
        ids=[
            'completed beta', 'capitalised', 'finished beta', 'under a different email',
            'beta->p migration', 'beta->p migration, class tag', 'other reason', 'test grant',
            'blank note', 'not allowlisted',
        ],
    )
    def test_beta_completion_is_read_from_the_allowlist_note(self, notes, expected):
        with mock.patch(NOTES, return_value=notes) as lookup:
            assert CourseCompletionStatement.is_beta_completion(make_certificate_event()) is expected
        lookup.assert_called_once_with(5, COURSE)

    @pytest.mark.unittests
    def test_allowlist_lookup_failure_reads_as_not_beta(self):
        with mock.patch(NOTES, side_effect=RuntimeError('db down')):
            assert CourseCompletionStatement.is_beta_completion(make_certificate_event()) is False

    @pytest.mark.unittests
    @override_settings(FEATURES={'RG_GAMIFICATION': {'IGNORED_EVENT_TYPES': [],
                                                     'BETA_COMPLETION_ALLOWLIST_NOTE_REGEX': r'\bbeta grad\b'}})
    def test_note_pattern_can_be_overridden(self):
        with mock.patch(NOTES, return_value='Beta grad, 2026 cohort'):
            assert CourseCompletionStatement.is_beta_completion(make_certificate_event()) is True
        with mock.patch(NOTES, return_value='completed beta'):
            assert CourseCompletionStatement.is_beta_completion(make_certificate_event()) is False

    @pytest.mark.unittests
    @pytest.mark.parametrize('notes, flagged', [('completed beta', True), ('Extra quiz question added', False)])
    def test_payload_carries_the_flag_only_for_beta_completions(self, notes, flagged):
        with mock.patch(NOTES, return_value=notes), \
                mock.patch.object(BaseGammaEvent, 'get_signup_source', return_value='main'):
            statement = CourseCompletionStatement(make_certificate_event())

        assert statement.data['event_type'] == 'edx_certificate_created'
        assert statement.data['course_id'] == COURSE
        if flagged:
            assert statement.data['beta_completion'] is True
        else:
            assert 'beta_completion' not in statement.data

from unittest import mock

import pytest

from gamma_bridge.converter import TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP
from gamma_bridge.statements.base import BaseGammaEvent
from gamma_bridge.statements.course import CourseCompletionStatement

COURSE = 'course-v1:OpenSecurityTraining2+Arch1001_x86-64_Asm+2021_v1'
ALLOWLISTED = 'gamma_bridge.statements.course.is_allowlisted'


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
    @pytest.mark.parametrize('allowlisted', [True, False], ids=['allowlisted', 'earned'])
    def test_any_allowlist_entry_flags_the_certificate(self, allowlisted):
        # Every hand-granted (allowlisted) certificate is Gold, whatever its note says.
        with mock.patch(ALLOWLISTED, return_value=allowlisted) as lookup:
            assert CourseCompletionStatement.is_allowlisted_certificate(make_certificate_event()) is allowlisted
        lookup.assert_called_once_with(5, COURSE)

    @pytest.mark.unittests
    def test_allowlist_lookup_failure_reads_as_not_allowlisted(self):
        with mock.patch(ALLOWLISTED, side_effect=RuntimeError('db down')):
            assert CourseCompletionStatement.is_allowlisted_certificate(make_certificate_event()) is False

    @pytest.mark.unittests
    @pytest.mark.parametrize('allowlisted', [True, False], ids=['allowlisted', 'earned'])
    def test_payload_carries_the_flag_only_for_allowlisted_certificates(self, allowlisted):
        with mock.patch(ALLOWLISTED, return_value=allowlisted), \
                mock.patch.object(BaseGammaEvent, 'get_signup_source', return_value='main'):
            statement = CourseCompletionStatement(make_certificate_event())

        assert statement.data['event_type'] == 'edx_certificate_created'
        assert statement.data['course_id'] == COURSE
        if allowlisted:
            assert statement.data['beta_completion'] is True
        else:
            assert 'beta_completion' not in statement.data

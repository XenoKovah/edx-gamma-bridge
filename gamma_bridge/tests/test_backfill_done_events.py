from unittest import mock

import pytest

from gamma_bridge.management.commands.backfill_done_events import Command
from gamma_bridge.statements.completion import UnitDoneStatement
from gamma_bridge.tests.test_done_statement import BLOCK, make_done_event


class FakeCourseKey(str):
    """
    str with the .org attribute the command reads off a CourseKey.
    """
    org = 'Org'


def fake_student_module():
    module = mock.Mock()
    module.course_id = FakeCourseKey('course-v1:Org+C1+2026')
    module.module_state_key = BLOCK
    module.student.username = 'learner'
    return module


class TestBackfillDoneEvents:

    @pytest.mark.unittests
    def test_rebuilt_event_matches_live_tracking_event_shape(self):
        rebuilt = Command._as_tracking_event(fake_student_module())
        live = make_done_event(done=True)

        assert rebuilt['event_type'] == live['event_type']
        assert rebuilt['username'] == live['username']
        assert rebuilt['event'] == {'done': True}
        assert rebuilt['context']['course_id'] == live['context']['course_id']
        assert rebuilt['context']['org_id'] == live['context']['org_id']
        assert rebuilt['context']['module']['usage_key'] == live['context']['module']['usage_key']

    @pytest.mark.unittests
    def test_rebuilt_event_dedupes_against_the_live_pipeline(self):
        """
        The whole point of the backfill: its uid must equal the live pipeline's uid for
        the same (course, user, block), so re-sent history collides instead of double
        counting (and Gamma can patch block_id onto pre-block_id rows by uid).
        """
        statement = object.__new__(UnitDoneStatement)

        live_uid = statement.get_uid(make_done_event(done=True))
        rebuilt_uid = statement.get_uid(Command._as_tracking_event(fake_student_module()))

        assert rebuilt_uid == live_uid

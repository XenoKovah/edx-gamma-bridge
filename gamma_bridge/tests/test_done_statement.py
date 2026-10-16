import logging
from unittest import mock

import pytest

from gamma_bridge.converter import TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP, to_gamma
from gamma_bridge.exceptions import GammaEventDataError
from gamma_bridge.statements.completion import UnitDoneStatement

BLOCK = 'block-v1:Org+C1+2026+type@done+block@761ee26eb2ad47aea8a0582700ec9832'


def make_done_event(done=True, username='learner', block=BLOCK):
    """
    Shape mirrors a real edx.done.toggled tracking-log entry (see DoneXBlock).
    """
    return {
        'event_type': 'edx.done.toggled',
        'username': username,
        'context': {
            'course_id': 'course-v1:Org+C1+2026',
            'org_id': 'Org',
            'user_id': 5,
            'module': {'display_name': 'Completion', 'usage_key': block},
        },
        'event': {'done': done},
        'page': 'x_module',
    }


def statement():
    """
    Bare instance without __init__ (which builds the full payload and resolves
    the signup source from the DB); the methods under test are pure.
    """
    return object.__new__(UnitDoneStatement)


class TestUnitDoneStatement:

    @pytest.mark.unittests
    def test_mapped_in_converter(self):
        entry = TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP['edx.done.toggled']
        assert entry['statement_class'] is UnitDoneStatement

    @pytest.mark.unittests
    def test_check_is_allowed_to_save(self):
        assert statement().is_allowed_to_save(make_done_event(done=True)) is True

    @pytest.mark.unittests
    def test_uncheck_is_not_allowed_to_save(self):
        assert statement().is_allowed_to_save(make_done_event(done=False)) is False

    @pytest.mark.unittests
    def test_missing_done_flag_is_not_allowed_to_save(self):
        event = make_done_event()
        event['event'] = {}
        assert statement().is_allowed_to_save(event) is False

    @pytest.mark.unittests
    def test_uid_stable_across_toggles(self):
        check = make_done_event(done=True)
        recheck = make_done_event(done=True)
        assert statement().get_uid(check) == statement().get_uid(recheck)

    @pytest.mark.unittests
    def test_uid_distinct_per_block_and_user(self):
        base = statement().get_uid(make_done_event())
        other_block = statement().get_uid(make_done_event(block=BLOCK.replace('761e', 'aaaa')))
        other_user = statement().get_uid(make_done_event(username='someone_else'))
        assert len({base, other_block, other_user}) == 3

    @pytest.mark.unittests
    def test_missing_usage_key_raises(self):
        event = make_done_event()
        event['context'].pop('module')
        with pytest.raises(GammaEventDataError):
            statement().get_uid(event)

    @pytest.mark.unittests
    def test_get_block_id(self):
        assert statement().get_block_id(make_done_event()) == BLOCK

    @pytest.mark.unittests
    def test_payload_carries_block_id(self):
        with mock.patch('gamma_bridge.statements.base.User') as user_model:
            user_model.objects.get.return_value.usersignupsource_set.first.return_value = None
            data = UnitDoneStatement(make_done_event()).data
        assert data['block_id'] == BLOCK
        assert data['course_id'] == 'course-v1:Org+C1+2026'


def make_browser_done_event(done=True):
    """
    The duplicate the browser emits for the same click: posted to /event, so
    the context carries no ``module`` (and therefore no usage_key).
    """
    event = make_done_event(done=done)
    event['event_source'] = 'browser'
    event['context'].pop('module')
    event['context']['path'] = '/event'
    event['page'] = 'https://dev.ost2.fyi/xblock/' + BLOCK
    return event


def make_server_done_event(done=True):
    event = make_done_event(done=done)
    event['event_source'] = 'server'
    event['context']['path'] = '/courses/course-v1:Org+C1+2026/xblock/{}/handler/toggle_button'.format(BLOCK)
    return event


@pytest.fixture
def no_signup_source():
    with mock.patch('gamma_bridge.statements.base.User') as user_model:
        user_model.objects.get.return_value.usersignupsource_set.first.return_value = None
        yield


class TestDoneToggledConversion:

    @pytest.mark.unittests
    def test_server_event_emits(self, no_signup_source):
        statement = to_gamma(make_server_done_event())
        assert isinstance(statement, UnitDoneStatement)
        assert statement.data['block_id'] == BLOCK
        assert statement.data['event_type'] == 'edx_done_toggled'

    @pytest.mark.unittests
    @pytest.mark.parametrize('done', [True, False])
    def test_browser_duplicate_skipped_without_error(self, no_signup_source, caplog, done):
        caplog.set_level(logging.DEBUG)
        assert to_gamma(make_browser_done_event(done=done)) is None
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    @pytest.mark.unittests
    def test_server_uncheck_still_dropped(self, no_signup_source):
        assert to_gamma(make_server_done_event(done=False)) is None

    @pytest.mark.unittests
    def test_server_event_missing_module_still_raises(self, no_signup_source):
        event = make_server_done_event()
        event['context'].pop('module')
        with pytest.raises(GammaEventDataError):
            to_gamma(event)

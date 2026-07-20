import pytest

from gamma_bridge.converter import TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP
from gamma_bridge.statements.completion import BlockCompletionStatement

BLOCK = 'block-v1:Org+C1+2026+type@video+block@6a1b1c2d3e4f5061728394a5b6c7d8e9'
COURSE = 'course-v1:Org+C1+2026'


def make_completion_event(block_type='video', block_id=BLOCK, course_id=COURSE):
    """
    Shape mirrors what gamma_bridge.handlers.emit_block_completion emits: the block
    lives in the event BODY, not in context.module the way edx.done.toggled carries it.
    """
    event = {
        'user_id': 5,
        'course_id': course_id,
        'block_type': block_type,
        'completion': 1.0,
    }
    if block_id is not None:
        event['block_id'] = block_id
    return {
        'event_type': 'rgg.block.completed',
        'username': 'learner',
        'context': {'course_id': course_id, 'org_id': 'Org'},
        'event': event,
    }


def statement():
    """
    Bare instance without __init__ (which builds the full payload and resolves the
    signup source from the DB); the methods under test are pure.
    """
    return object.__new__(BlockCompletionStatement)


class TestBlockCompletionStatement:

    @pytest.mark.unittests
    def test_mapped_in_converter(self):
        entry = TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP['rgg.block.completed']
        assert entry['statement_class'] is BlockCompletionStatement

    @pytest.mark.unittests
    def test_block_id_comes_from_the_event_body(self):
        # The inherited BaseGammaEvent.get_block_id returns None; this event puts the
        # usage key in the body, and gamma's block-set badge rules filter on it.
        assert statement().get_block_id(make_completion_event()) == BLOCK

    @pytest.mark.unittests
    def test_block_id_absent_is_none_not_an_error(self):
        # None is dropped from the POST body, keeping the payload shape unchanged for
        # any future block-less completion rather than failing the whole statement.
        assert statement().get_block_id(make_completion_event(block_id=None)) is None

    @pytest.mark.unittests
    def test_payload_block_agrees_with_the_dedup_uid(self):
        # get_uid dedups per (gamma event, course, user, block). If get_block_id read a
        # different field the stored row would claim a block the uid never covered, and
        # a second completion of a DIFFERENT block could dedup away.
        event = make_completion_event()
        inst = statement()
        assert inst.get_block_id(event) in inst.get_uid(event)

    @pytest.mark.unittests
    def test_video_maps_to_stop_video_and_is_saved(self):
        inst = statement()
        event = make_completion_event(block_type='video')
        assert inst.get_type(event) == 'stop_video'
        assert inst.is_allowed_to_save(event) is True

    @pytest.mark.unittests
    def test_unmapped_block_type_is_skipped(self):
        # 'done' is deliberately absent from the default mapping — the DoneXBlock owns
        # it through edx.done.toggled, so mapping it here too would double-award.
        inst = statement()
        event = make_completion_event(block_type='done')
        assert inst.get_type(event) is None
        assert inst.is_allowed_to_save(event) is False

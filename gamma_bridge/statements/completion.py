import datetime

from django.conf import settings

from . base import BaseGammaEvent, validate_event_fields

# Map a completed block's `block_type` to the gamma event whose EventConfiguration
# carries the reward. Override RGG_BLOCK_COMPLETION_GAMMA_EVENTS in settings to retune
# (e.g. drop 'html' if auto-on-view completion would over-award).
DEFAULT_BLOCK_TYPE_GAMMA_EVENTS = {
    'done': 'edx_done_toggled',   # "Mark a Unit as Complete"
    'video': 'stop_video',        # "Watch a Video to the End" (now real 95% completion)
    'html': 'edx_done_toggled',   # reading a page counts as completing the unit
}


class BaseCompletion(BaseGammaEvent):
    def get_uid(self, event):
        event_dict = event.get('event', '{}')
        validate_event_fields(event_dict, ('user_id', 'block_id'))
        uid = '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            self.get_course_id(event),
            event_dict.get('user_id'),
            event_dict.get('block_id'),
        )
        return uid

    def is_allowed_to_save(self, event):
        return True


class CompletionStatement(BaseCompletion):
    pass


class CompletionDailyStatement(BaseCompletion):
    def get_uid(self, event):
        event_dict = event.get('event', '{}')
        validate_event_fields(event_dict, ('user_id',))
        uid = '{}:{}:{}'.format(
            self.__class__.__name__,
            event_dict.get('user_id'),
            datetime.date.today(),
        )
        return uid


class BlockCompletionStatement(BaseCompletion):
    """
    Unified statement for the `rgg.block.completed` event emitted by
    gamma_bridge.handlers.emit_block_completion. Maps the BlockCompletion's `block_type`
    to the appropriate gamma event (done -> edx_done_toggled, video -> stop_video, ...)
    so the existing gamma EventConfigurations award the right points from ONE source.
    """
    def _block_type(self, event):
        return event.get('event', {}).get('block_type')

    def get_type(self, event):
        mapping = getattr(settings, 'RGG_BLOCK_COMPLETION_GAMMA_EVENTS', DEFAULT_BLOCK_TYPE_GAMMA_EVENTS)
        return mapping.get(self._block_type(event))

    def get_course_id(self, event):
        return event.get('event', {}).get('course_id') or super().get_course_id(event)

    def is_allowed_to_save(self, event):
        # Skip block types that have no configured gamma event.
        return bool(self.get_type(event))

    def get_uid(self, event):
        event_dict = event.get('event', '{}')
        validate_event_fields(event_dict, ('user_id', 'block_id'))
        # Dedup per (gamma event, course, user, block) so re-saves never double-award.
        return '{}:{}:{}:{}'.format(
            self.get_type(event),
            self.get_course_id(event),
            event_dict.get('user_id'),
            event_dict.get('block_id'),
        )


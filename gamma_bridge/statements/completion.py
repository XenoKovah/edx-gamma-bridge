import datetime

from . base import BaseGammaEvent, validate_event_fields


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


class UnitDoneStatement(BaseGammaEvent):
    """
    "Mark as complete" (DoneXBlock) checked by the learner (``edx.done.toggled``).

    The XBlock emits the same event for checking AND unchecking; uncheck
    (``done: false``) is dropped here. The uid hashes (course, user, block), so
    re-checking after an uncheck produces the same uid and Gamma's
    (uid, client, username) uniqueness rejects it — toggling cannot farm points.
    """

    def get_uid(self, event):
        module = event.get('context', {}).get('module') or {}
        validate_event_fields(module, ('usage_key',))
        uid = '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            self.get_course_id(event),
            self.get_username(event),
            module.get('usage_key'),
        )
        return uid

    def is_allowed_to_save(self, event):
        return event.get('event', {}).get('done') is True


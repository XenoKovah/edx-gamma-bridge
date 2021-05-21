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


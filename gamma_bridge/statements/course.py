import json

from .base import BaseGammaEvent, validate_event_fields


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
    pass


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

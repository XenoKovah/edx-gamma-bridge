from . base import BaseGammaEvent, validate_event_fields
from gamma_bridge.exceptions import GammaEventDataError


class BaseProblem(BaseGammaEvent):
    def get_uid(self, event):
        event_dict = event.get('event', {})
        validate_event_fields(event_dict, ('problem_id', ))

        uid = '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            event_dict.get('problem_id'),
            self.get_course_id(event),
            self.get_username(event)
        )
        return uid
    
    def is_allowed_to_save(self, event):
        return True


class ProblemCheckStatement(BaseProblem):

    def get_uid(self, event):
        event_data = event.get('event')
        if not event_data:
            raise GammaEventDataError('"event" should not be empty')

        uid = '{}:{}:{}:{}'.format(
            self.__class__.__name__,
            event_data[0] if isinstance(event_data, list) and len(event_data) > 0 else event_data,
            self.get_course_id(event),
            self.get_username(event)
        )
        return uid

    def is_allowed_to_save(self, event):
        return True


class ProblemSubmittedStatement(BaseProblem):
    pass


class ProblemResetStatement(BaseProblem):
    pass


class ProblemGradedStatement(ProblemCheckStatement):
    pass


class OpenAssessmentSubmittedStatement(BaseGammaEvent):

    def get_uid(self, event):
        context_dict = event.get('context', {})
        validate_event_fields(context_dict, ('path', ))
        # path contains course id and block id
        return context_dict['path']

    def is_allowed_to_save(self, event):
        return True

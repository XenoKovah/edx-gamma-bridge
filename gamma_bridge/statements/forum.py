from .base import BaseGammaEvent, validate_event_fields


class BaseForum(BaseGammaEvent):
    def get_uid(self, event):
        event_dict = event.get('event', {})
        validate_event_fields(event_dict, ('id', ))
        return event_dict['id']

    def is_allowed_to_save(self, event):
        return True


class ForumCommentStatement(BaseForum):
    pass


class ForumResponseStatement(BaseForum):
    pass


class ForumThreadStatement(BaseForum):
    pass


class ForumVoteStatement(BaseForum):
    def get_uid(self, event):
        # make event uid from thread id and voted user username
        return '{}_{}'.format(super(ForumVoteStatement, self).get_uid(event), event['username'])

    def get_username(self, event):
        event_dict = event.get('event', {})
        validate_event_fields(event_dict, ('target_username', ))
        # points goes to user who created thread, not for user who voted
        return event_dict['target_username']

"""Statements base for Gamma Event Log."""
from abc import ABCMeta, abstractmethod
import json
import re

import hashlib

from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.contrib.auth.models import User

from gamma_bridge.exceptions import GammaEventDataError

MAIN_SITE_NAME = 'main'


class SHA1UIDStrategy(object):
    """
    Default strategy for handling event's UID.

    Goal is to return the same hex data for any length UID.

    :return: hexdigest of _hashlib.HASH
    """
    def handle(self, uid):
        return hashlib.sha1(uid).hexdigest()


def validate_event_fields(data, required_fields_list):
    if not isinstance(data, dict):
        raise GammaEventDataError('"event" structure is not a dict')
    required_fields_list = set(required_fields_list)
    missed_fields = required_fields_list.difference(data.keys())
    if missed_fields:
        raise GammaEventDataError(
            '"event" does not have required fields - {}'.format(', '.join(missed_fields))
        )


class BaseGammaEvent(object):
    """
    Base class for Gamification Event Logs.
    """
    __metaclass__ = ABCMeta

    # TODO: setup a desired strategy via settings
    UID = SHA1UIDStrategy()

    def __init__(self, event, *args, **kwargs):
        """
        Initialize an Gamma event statement from a tracking log event.
        """
        self.data = dict(
            event_type=self.get_type(event),
            username=self.get_username(event),
            signup_source=self.get_signup_source(event),
            course_id=self.get_course_id(event),
            org=self.get_org(event),
            uid=self.UID.handle(self.get_uid(event).encode('utf-8')),
            event=json.dumps(self.get_event(event), cls=DjangoJSONEncoder) if settings.DEBUG else None,
            context=json.dumps(self.get_context(event), cls=DjangoJSONEncoder) if settings.DEBUG else None,
            full_event=json.dumps(event, cls=DjangoJSONEncoder) if settings.DEBUG else None,
        )

    def get_type(self, event):
        return re.sub('\.+', '_', event['event_type'])

    def get_username(self, event):
        return event['username']

    @staticmethod
    def get_signup_source(event):
        if username := event.get('username'):
            user = User.objects.get(username=username)
            signup_source = user.usersignupsource_set.first()
            return signup_source.site if signup_source else MAIN_SITE_NAME

    def get_course_id(self, event):
        return event.get('context', {}).get('course_id', '')

    def get_org(self, event):
        return event.get('context', {}).get('org_id', '')

    def get_event(self, event):
        return event.get('event', {})

    def get_context(self, event):
        return event.get('context', {})

    @abstractmethod
    def is_allowed_to_save(self, event):
        """
        This is for a possible filtering on provider side.
        """
        pass

    @abstractmethod
    def get_uid(self, event):
        pass

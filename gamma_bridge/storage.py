"""Default RG Gamification backend."""
from abc import ABCMeta, abstractmethod, abstractproperty
import json
import requests
import urlparse

from django.conf import settings


class BaseStorage(object):
    """
    The base class for work with remote storage.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def save(self, event):
        """
        Save event in remote storage.
        """
        pass

    @abstractproperty
    def response_has_errors(self):
        """
        Check response for any errors.

        Return boolean value.
        """
        pass

    @abstractproperty
    def request_unauthorised(self):
        """
        Check response for unauthorised error.

        Return boolean value.
        """
        pass

    @abstractproperty
    def response_has_storage_errors(self):
        """
        Check response for any error from storage.

        Return boolean value.
        """
        pass


class GammaStorage(BaseStorage):
    """
    RG Gamification default backend known as GAMMA.
    """
    def __init__(self, enabled=False, endpoint=None, key=None, secret=None):
        super(GammaStorage, self).__init__()
        self.is_enabled = all((enabled, endpoint, key, secret))
        self.endpoint = endpoint
        self.key = key
        self.secret = secret
        self.response_data = None
        self.response_data_content = None

    def save(self, event):
        """
        Save event in gamma storage.
        """
        headers = {
            'App-key': self.key,
            'App-secret': self.secret
        }
        if self.is_enabled:
            self.response_data = requests.put(
                urlparse.urljoin(self.endpoint, settings.GAMMA_API_SUFFIX),
                data=event,
                headers=headers,
                verify=False
            )
            self.response_data_content = json.loads(self.response_data.content)

    @property
    def response_has_errors(self):
        """
        Check response for any errors.

        Return boolean value.
        """
        return 'Error' in self.response_data_content

    @property
    def request_unauthorised(self):
        """
        Check response for unauthorised error.

        Return boolean value.
        """
        return 'unauthorised' in self.response_data_content.get('Error', '')

    @property
    def response_has_storage_errors(self):
        """
        Check response for any error from gamma storage.

        Return boolean value.
        """
        return 'warnings' in self.response_data_content.get('Error', '')

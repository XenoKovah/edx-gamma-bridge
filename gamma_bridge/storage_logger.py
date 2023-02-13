"""Logger class for logging storage work."""
import logging

from gamma_bridge.storage import BaseStorage
from gamma_bridge.exceptions import NotBaseStorageError, GammaValueError

LOGGER = logging.getLogger(__name__)


class StorageLogger(object):
    """
    Log the GammaStorage result and event.
    """

    @staticmethod
    def logging(gamma_storage, event):
        """
        Login the status of Storage's response and event.
        """
        # TODO: Move raise exception to StorageLogger initialization
        if not isinstance(gamma_storage, BaseStorage):
            raise NotBaseStorageError("Current type: {}".format(type(gamma_storage)))

        if not isinstance(event, dict):
            raise GammaValueError("'event' property must be a dictionary.")

        if gamma_storage.response_data.status_code == 200:
            LOGGER.debug("Succeeded sending statement {}".format(event))
        elif gamma_storage.response_has_errors:
            if gamma_storage.response_has_storage_errors:
                LOGGER.info(
                    "Storage error during saving event statement {}/{} Details: {}".format
                    (event.get('username'), event.get('event_type'), gamma_storage.response_data.content))
            elif gamma_storage.request_unauthorised:
                LOGGER.info("Unauthorized request during saving event statement {}/{} Details: {}".format
                            (event.get('username'), event.get('event_type'), gamma_storage.response_data.content))
            else:
                LOGGER.info("Error during saving event statement {}/{} Details: {}".format
                            (event.get('username'), event.get('event_type'), gamma_storage.response_data.content))

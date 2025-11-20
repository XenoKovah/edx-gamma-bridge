"""Convert tracking log entries to xAPI statements."""

import logging
from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from gamma_bridge.statements import completion, course, forum, problem, video, base

LOGGER = logging.getLogger(__name__)
_CLASS_CACHE = {}

# For test purpose
# Todo: provide test.py settings where AUTH_USER_MODEL is specified
try:
    User = get_user_model()
except ImproperlyConfigured:
    LOGGER.error('Error during loading User model')


TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP = {

    # course enrollment
    'edx.course.enrollment.activated': {
        "statement_class": course.CourseEnrollmentStatement,
        "verbose_name": "Course Enrollment"
    },

    # course completion
    'edx.certificate.created': {
        "statement_class": course.CourseCompletionStatement,
        "verbose_name": "Course Certificate is Received"
    },

    'edx.course.student_notes.added': {
        "statement_class": course.CourseStudentNotesStatement,
        "verbose_name": "Learner Note Added"
    },

    # problems
    'problem_check': {
        "statement_class": problem.ProblemCheckStatement,
        "verbose_name": "Problem Check"
    },
    'edx.grades.problem.submitted': {
        "statement_class": problem.ProblemSubmittedStatement,
        "verbose_name": "Problem Submitted"
    },
    'problem_graded': {
        "statement_class": problem.ProblemGradedStatement,
        "verbose_name": "Problem Finished"
    },

    # open assessment submission
    "openassessmentblock.save_submission": {
        "statement_class": problem.OpenAssessmentSubmittedStatement,
        "verbose_name": "Open Assessment Submitted"
    },

    # video
    'stop_video': {
        "statement_class": video.VideoCompleteStatement,
        "verbose_name": "Complete Video"
    },

    'edx.bookmark.added': {
        "statement_class": course.BookmarkAddedStatement,
        "verbose_name": "Unit Bookmark Added"
    },

    # forum
    'edx.forum.comment.created': {
        "statement_class": forum.ForumCommentStatement,
        "verbose_name": "Forum Comment Added"
    },

    'edx.forum.response.created': {
        "statement_class": forum.ForumResponseStatement,
        "verbose_name": "Forum Question Response Added"
    },

    # Users create a new top-level thread, also known as a post,
    # by clicking New Post and then submitting their contributions.
    'edx.forum.thread.created': {
        "statement_class": forum.ForumThreadStatement,
        "verbose_name": "Forum Thread Created"
    },

    'edx.forum.thread.voted': {
        "statement_class": forum.ForumVoteStatement,
        "verbose_name": "Forum Thread Voted"
    },
    # Completions
    'completion.submited': {
        "statement_class": completion.CompletionStatement,
        "verbose_name": "Completion Submited"
    },

    'completion.submited.daily': {
        "statement_class": completion.CompletionDailyStatement,
        "verbose_name": "Daily Learning Tracking"
    },
}

ADDITIONAL_TRACKING_EVENTS = {
    # Completions
    'completion.submited': 'completion.submited.daily'
}


def to_gamma(event):
    """Return tuple of Gamification statements or None if ignored or unhandled event type."""

    # strip Video XBlock prefixes for checking
    event_type = event['event_type'].replace("xblock-video.", "")

    if event_type in settings.FEATURES.get('RG_GAMIFICATION', {}).get('IGNORED_EVENT_TYPES'):
        LOGGER.debug("Ignored event {}".format(
                event.get('event_type')))
        return  # deliberately ignored event

    try:
        statement_class = TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP[event_type]['statement_class']
    except KeyError:  # event is not in the default map, try extension
        statement_class = get_statement_class_from_extension(event_type)
        if not statement_class:  # event is untracked
            LOGGER.debug(
                f"Event '{event.get('event_type')}' was skipped because it is not in default or extension map."
            )
            return

    # some events (like edx.certificate.created) lack username in the context
    # see RGOeX-1014 for more info
    if not event.get('username'):
        user_id = event['event'].get('user_id')
        try:
            event['username'] = User.objects.get(id=user_id).username
        except User.DoesNotExist:
            LOGGER.warning(
                f"Skipping event {event_type} processing because user with "
                f"id {user_id} does not exist."
            )
    return statement_class(event)


def get_additional_statement(event):
    """
    Check if there is additional statements for this event type.

    Returns:
        Tuple of Gamification statements or None if ignored or unhandled event type.
    """
    # TODO: use a list as a values in the ADDITIONAL_TRACKING_EVENTS
    if additional_event := ADDITIONAL_TRACKING_EVENTS.get(event['event_type']):
        event['event_type'] = additional_event
        return to_gamma(event)
    return


def get_statement_class_from_extension(event_type: str):
    """
    Helper function for looking up custom event classes.

    Try to resolve a statement class for the given event_type using the TRACKING_EVENTS_TO_GAMMA_EXTENSION setting.
    Retrieved classes are stored to a module-level cache to avoid repeated parsing of the same events.

    The statement_class values are expected to be path strings (see example below).
    This string-based approach helps avoid circular imports, ensure custom events are loaded on-demand,
    and preserve loose coupling between gamma-bridge and any other plugins.

    Args:
        event_type: The event type identifier (e.g., 'custom.event.type')

    Returns:
        Statement class if found and successfully imported, None otherwise.

    Example configuration:
        TRACKING_EVENTS_TO_GAMMA_EXTENSION = {
            'custom.event.type': {
                'statement_class': 'myapp.statements.CustomEventStatement',
                'verbose_name: 'Custom Event Type'
            }
        }
    """

    if event_type in _CLASS_CACHE:
        return _CLASS_CACHE[event_type]

    extension_map = getattr(settings, "TRACKING_EVENTS_TO_GAMMA_EXTENSION", {})
    event_entry = extension_map.get(event_type)
    if not event_entry:
        return None

    class_path = event_entry.get("statement_class")
    if not class_path:
        return None

    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = import_module(module_path)
        cls = getattr(module, class_name)

        if not (isinstance(cls, type) and issubclass(cls, base.BaseGammaEvent)):
            LOGGER.warning(f"Statement class '{class_path}' does not inherit from BaseGammaEvent")
            return None

        _CLASS_CACHE[event_type] = cls
        return cls

    except (ImportError, AttributeError) as e:
        LOGGER.error(f"Failed to import statement class '{class_path}': {e}")
        return None
    except ValueError as e:
        LOGGER.warning(f"Invalid class path format '{class_path}': {e}")
        return None

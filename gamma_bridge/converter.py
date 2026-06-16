"""Convert tracking log entries to xAPI statements."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from gamma_bridge.statements import completion, course, forum, problem, profile, video

LOGGER = logging.getLogger(__name__)

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

    # Block completion (unified): the single `rgg.block.completed` event emitted by
    # gamma_bridge.handlers.emit_block_completion. BlockCompletionStatement maps the
    # block_type to the right gamma event (done->edx_done_toggled, video->stop_video, ...),
    # so done/video/html all flow from ONE BlockCompletion-backed source. This drives
    # "Watch a Video to the End" off real segment-aware 95% completion instead of the raw
    # `stop_video` end event (which the YouTube-embedded player never fires here).
    'rgg.block.completed': {
        "statement_class": completion.BlockCompletionStatement,
        "verbose_name": "Block Completed"
    },

    'edx.bookmark.added': {
        "statement_class": course.BookmarkAddedStatement,
        "verbose_name": "Unit Bookmark Added"
    },

    # profile / account settings
    # A single tracking event (edx.user.settings.changed) carries every account
    # and preference field change; ProfileSettingStatement discriminates by the
    # `setting` payload key and drops non-rewardable settings via is_allowed_to_save.
    'edx.user.settings.changed': {
        "statement_class": profile.ProfileSettingStatement,
        "verbose_name": "Profile Setting Changed"
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
    # LEGACY / superseded by 'rgg.block.completed' above. Nothing in the LMS ever emitted
    # 'completion.submited'; kept only so the 'completion.submited.daily' streak path below
    # stays reachable. Done/video/html completions now flow via BlockCompletionStatement.
    'completion.submited': {
        "statement_class": completion.CompletionStatement,
        "verbose_name": "Completion Submited"
    },

    'completion.submited.daily': {
        "statement_class": completion.CompletionDailyStatement,
        "verbose_name": "Daily Learning Tracking"
    },

    # "Mark as complete" (DoneXBlock). Emitted on both check and uncheck;
    # UnitDoneStatement drops unchecks and dedupes re-checks per block.
    'edx.done.toggled': {
        "statement_class": completion.UnitDoneStatement,
        "verbose_name": "Unit Marked Complete"
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
    except KeyError:  # untracked event
        LOGGER.debug(
            f"Event '{event.get('event_type')}' was skipped because it is not in TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP"
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

    statement = statement_class(event)
    # Provider-side filtering hook: a statement may opt out of forwarding an
    # event. ProfileSettingStatement ignores non-rewardable settings/values, and
    # BlockCompletionStatement returns False for block types with no configured
    # gamma event (e.g. 'done' — owned by edx.done.toggled — or unmapped types).
    if not statement.is_allowed_to_save(event):
        LOGGER.debug(
            "Statement %s opted out of event %r; not forwarding to Gamma.",
            statement_class.__name__,
            event_type,
        )
        return
    return statement


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

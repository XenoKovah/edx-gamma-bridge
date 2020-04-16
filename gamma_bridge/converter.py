"""Convert tracking log entries to xAPI statements."""

import logging

from django.conf import settings

from gamma_bridge.statements import course, video, problem, forum


LOGGER = logging.getLogger(__name__)


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
}


def to_gamma(event):
    """Return tuple of Gamification statements or None if ignored or unhandled event type."""

    # strip Video XBlock prefixes for checking
    event_type = event['event_type'].replace("xblock-video.", "")

    if event_type in settings.FEATURES.get('RG_GAMIFICATION', {}).get('IGNORED_EVENT_TYPES'):
        LOGGER.info("Ignored event {}".format(
                event.get('event_type')))
        return  # deliberately ignored event

    try:
        statement_class = TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP[event_type]['statement_class']
    except KeyError:  # untracked event
        LOGGER.exception("Missing transformer method implementation for {}".format(
                event.get('event_type')))
        return
    return statement_class(event)

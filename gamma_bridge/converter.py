"""Convert tracking log entries to xAPI statements."""

import logging

from django.conf import settings

from gamma_bridge.statements import course, video, problem


LOGGER = logging.getLogger(__name__)


TRACKING_EVENTS_TO_GAMMA_STATEMENT_MAP = {

    # course enrollment
    'edx.course.enrollment.activated': {
        "statement_class": course.CourseEnrollmentStatement,
        "verbose_name": "Course Enrollment"
    },
    'edx.course.enrollment.deactivated': {
        "statement_class": course.CourseUnenrollmentStatement,
        "verbose_name": "Course Enrollment Cancelled"
    },

    # course completion
    'edx.certificate.created': {
        "statement_class": course.CourseCompletionStatement,
        "verbose_name": "Get Certificate for Course"
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
        "verbose_name": "Problem Graded"
    },
    'reset_problem': {
        "statement_class": problem.ProblemResetStatement,
        "verbose_name": "Problem Reset"
    },

    # video
    'ready_video': {
        "statement_class": video.VideoStatement,
        "verbose_name": "Video Loaded"
    },
    'load_video': {
        "statement_class": video.VideoStatement,
        "verbose_name": "Video Loaded"
    },
    'edx.video.loaded': {
        "statement_class": video.VideoStatement,
        "verbose_name": "Video Loaded"
    },

    'play_video': {
        "statement_class": video.VideoPlayStatement,
        "verbose_name": "Play Video"
    },
    'edx.video.played': {
        "statement_class": video.VideoPlayStatement,
        "verbose_name": "Play Video"
    },

    'pause_video': {
        "statement_class": video.VideoPauseStatement,
        "verbose_name": "Pause Video"
    },
    'edx.video.paused': {
        "statement_class": video.VideoPauseStatement,
        "verbose_name": "Pause Video"
    },

    'stop_video': {
        "statement_class": video.VideoCompleteStatement,
        "verbose_name": "Complete Video"
    },
    'edx.video.stopped': {
        "statement_class": video.VideoCompleteStatement,
        "verbose_name": "Complete Video"
    },

    'seek_video': {
        "statement_class": video.VideoSeekStatement,
        "verbose_name": "Seek Video"
    },
    'edx.video.position.changed': {
        "statement_class": video.VideoSeekStatement,
        "verbose_name": "Seek Video"
    },

    'show_transcript': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Show Video Transcript"
    },
    'hide_transcript': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Hide Video Transcript"
    },
    'edx.video.transcript.shown': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Show Video Transcript"
    },
    'edx.video.transcript.hidden': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Hide Video Transcript"
    },
    'edx.video.closed_captions.shown': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Show Video Transcript"
    },
    'edx.video.closed_captions.hidden': {
        "statement_class": video.VideoTranscriptStatement,
        "verbose_name": "Hide Video Transcript"
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

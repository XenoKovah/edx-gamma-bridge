"""
Replay historical bookmarks into Gamma as edx.bookmark.added events, so "Bookmark a
Unit" badge rules can count them. Resume-safe (see gamma_bridge.backfill_base).
POINTS CAVEAT: set the 'Bookmark a Unit' award to 0 for the run, then restore it.
"""
from gamma_bridge.backfill_base import BaseBackfillCommand
from gamma_bridge.statements.course import BookmarkAddedStatement


class Command(BaseBackfillCommand):
    help = "Replay Bookmark rows into Gamma (resume-safe)."
    CHECKPOINT_NAME = 'bookmark'
    STATEMENT_CLASS = BookmarkAddedStatement

    def get_queryset(self, options):
        from openedx.core.djangoapps.bookmarks.models import Bookmark
        qs = Bookmark.objects.select_related('user')
        if options['course_id']:
            qs = qs.filter(course_key=options['course_id'])
        if options['username']:
            qs = qs.filter(user__username=options['username'])
        return qs

    def should_skip(self, row):
        return not (row.user_id and row.course_key)

    def created_at_for(self, row):
        return row.created

    def row_label(self, row):
        return row.resource_id

    def build_event(self, row):
        ck = row.course_key
        return {
            'event_type': 'edx.bookmark.added',
            'username': row.user.username,
            'context': {'course_id': str(ck), 'org_id': ck.org},
            'event': {
                'bookmark_id': row.resource_id,
                'course_id': str(ck),
                'component_usage_id': str(row.usage_key),
            },
        }

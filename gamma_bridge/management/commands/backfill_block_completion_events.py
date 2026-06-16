"""
Replay historical video completions into Gamma as rgg.block.completed events, so
"Watch a Video to the End" (gamma event stop_video, +10) is finally awarded.

OST2 videos are YouTube embeds whose player never fires the native `stop_video`
tracking event, so that reward has awarded nothing — but completion.models.BlockCompletion
DID record each video reaching COMPLETION_VIDEO_COMPLETE_PERCENTAGE (~95%, segment-aware)
while ENABLE_COMPLETION_TRACKING was on. This command replays those rows through the
SAME BlockCompletionStatement the live emitter (gamma_bridge.handlers.emit_block_completion)
uses, so the dedup uid is identical (stop_video:course:user:block) and re-running is safe.

Default scope is block_type='video' (matching the live emitter's video-only mapping).
--block-types lets you widen it if RGG_BLOCK_COMPLETION_GAMMA_EVENTS maps more types;
rows whose type has no gamma mapping are skipped. Resume-safe (gamma_bridge.backfill_base).
POINTS CAVEAT: set the 'Watch a Video to the End' award to 0 for the run, then restore it.
"""
from gamma_bridge.backfill_base import BaseBackfillCommand
from gamma_bridge.statements.completion import BlockCompletionStatement


class Command(BaseBackfillCommand):
    help = "Replay BlockCompletion rows (video) into Gamma as rgg.block.completed (resume-safe)."
    CHECKPOINT_NAME = 'block_completion'
    STATEMENT_CLASS = BlockCompletionStatement

    def add_extra_arguments(self, parser):
        super().add_extra_arguments(parser)
        parser.add_argument('--block-types', default='video', dest='block_types',
                            help='Comma list of block_types to replay (default: video).')

    def get_queryset(self, options):
        from completion.models import BlockCompletion
        types = [t.strip() for t in options['block_types'].split(',') if t.strip()]
        qs = (BlockCompletion.objects
              .filter(completion__gte=1.0, block_type__in=types)
              .select_related('user'))
        if options['course_id']:
            qs = qs.filter(context_key=options['course_id'])
        if options['username']:
            qs = qs.filter(user__username=options['username'])
        return qs

    def should_skip(self, row):
        # Skip rows whose block_type has no gamma mapping (would POST a null event name).
        # Check the mapping directly — don't build a statement here (that does a per-row
        # user lookup and would run even in --dry-run).
        if not (row.user_id and row.block_key):
            return True
        from django.conf import settings
        from gamma_bridge.statements.completion import DEFAULT_BLOCK_TYPE_GAMMA_EVENTS
        mapping = getattr(settings, 'RGG_BLOCK_COMPLETION_GAMMA_EVENTS', DEFAULT_BLOCK_TYPE_GAMMA_EVENTS)
        return row.block_type not in mapping

    def created_at_for(self, row):
        return row.modified

    def row_label(self, row):
        return '%s/%s' % (row.block_key, row.user_id)

    def build_event(self, row):
        course_id = str(getattr(row, 'context_key', None) or getattr(row, 'course_key', '') or '')
        return {
            'event_type': 'rgg.block.completed',
            'username': row.user.username,
            'context': {'course_id': course_id},
            'event': {
                'user_id': row.user_id,
                'course_id': course_id,
                'block_id': str(row.block_key),
                'block_type': row.block_type,
                'completion': row.completion,
            },
        }

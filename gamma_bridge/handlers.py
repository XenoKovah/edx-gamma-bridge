"""
LMS-side emitter: turn every BlockCompletion into ONE gamification tracking event.

Open edX records a `completion.models.BlockCompletion` whenever a learner completes a block
-- a `done` XBlock clicked "Mark as complete", a `video` watched past
COMPLETION_VIDEO_COMPLETE_PERCENTAGE (segment-aware, ~95%), an `html` page read, etc. --
but ONLY while ENABLE_COMPLETION_TRACKING is on.

We emit a single `rgg.block.completed` tracking event carrying the `block_type`. The
GamificationProcessor -> converter -> BlockCompletionStatement then maps that block_type to
the right gamma event (done -> edx_done_toggled, video -> stop_video, ...), so the existing
gamma EventConfigurations award the right points.

This replaces the two brittle per-event paths that never produced anything in practice:
  - `completion.submited`  -- no emitter ever existed in the LMS, and
  - `stop_video`           -- the YouTube-embedded player never fires the `ended` event,
                              and "reached the literal end" is a poor completeness signal
                              anyway (misses real finishers, seek-spoofable).
Riding on BlockCompletion means we are inherently gated by ENABLE_COMPLETION_TRACKING and we
reuse the same segment-aware 95% video signal as the progress UI -- the correct "is it done"
measure rather than a raw end-of-media event.
"""
import logging

from django.conf import settings

log = logging.getLogger(__name__)

# Block types whose completion is forwarded to gamma. Override in settings to retune.
DEFAULT_TRACKED_BLOCK_TYPES = {'done', 'video', 'html'}

EVENT_NAME = 'rgg.block.completed'


def emit_block_completion(sender, instance, **kwargs):
    """post_save receiver on completion.models.BlockCompletion."""
    try:
        # Only fully-complete blocks: `done`/`html` are 1.0 when complete; a `video`
        # reaches 1.0 once watched past the 95% threshold. Partial video saves are skipped.
        if (getattr(instance, 'completion', 0) or 0) < 1.0:
            return

        block_type = getattr(instance, 'block_type', None)
        tracked = getattr(settings, 'RGG_BLOCK_COMPLETION_TRACKED_TYPES', DEFAULT_TRACKED_BLOCK_TYPES)
        if block_type not in tracked:
            return

        # `context_key` on modern django-completion; older schema used `course_key`.
        course_id = str(getattr(instance, 'context_key', None) or getattr(instance, 'course_key', '') or '')
        block_id = str(getattr(instance, 'block_key', '') or '')

        from eventtracking import tracker
        tracker.emit(EVENT_NAME, {
            'user_id': instance.user_id,
            'course_id': course_id,
            'block_id': block_id,
            'block_type': block_type,
            'completion': instance.completion,
        })
    except Exception:  # never let gamification break a completion write
        log.exception('gamma_bridge: failed to emit %s for a BlockCompletion', EVENT_NAME)

"""
Shared base for the gamma event-backfill management commands.

Provides a restart-safe driver loop with an on-disk resume cursor so a backfill
that is interrupted (VM shutdown, OOM, manual kill) resumes from where it stopped
instead of re-scanning every prior row. Correctness never depends on the cursor:
Gamma dedups on the event uid, so a stale or missing cursor only costs a re-scan,
never a double-grant.

Cursor files live under ``--checkpoint-dir`` (default ``/openedx/data/gamma_backfill``,
a persistent bind-mount, so they survive container *recreate*, not just restart):
  <name>.cursor  -> highest source-row id confirmed processed
  <name>.done    -> written once the whole source is exhausted (a later --resume is a no-op)

Subclasses define the source queryset and how to turn one row into the tracking
event the live pipeline would have emitted; the Statement class derives the payload
and dedup uid exactly as in production.
"""
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from gamma_bridge.storage import GammaStorage

DEFAULT_CHECKPOINT_DIR = '/openedx/data/gamma_backfill'


class Checkpoint:
    """Atomic, persistent resume cursor for one feed. No-op unless ``enabled``."""

    def __init__(self, name, directory, enabled):
        self.name = name
        self.enabled = enabled
        self.cursor_path = os.path.join(directory, '%s.cursor' % name)
        self.done_path = os.path.join(directory, '%s.done' % name)
        if enabled:
            os.makedirs(directory, exist_ok=True)

    def is_done(self):
        return self.enabled and os.path.exists(self.done_path)

    def load(self):
        if not self.enabled:
            return 0
        try:
            with open(self.cursor_path) as fh:
                return int((fh.read() or '0').strip())
        except (IOError, OSError, ValueError):
            return 0

    def save(self, last_id):
        if not self.enabled or last_id is None:
            return
        tmp = self.cursor_path + '.tmp'
        with open(tmp, 'w') as fh:
            fh.write(str(last_id))
        os.replace(tmp, self.cursor_path)  # atomic: a crash mid-write can't corrupt the cursor

    def mark_done(self):
        if self.enabled:
            open(self.done_path, 'w').close()


class BaseBackfillCommand(BaseCommand):
    """
    Drives one source through the live-equivalent tracking event into Gamma.

    Subclass contract:
      CHECKPOINT_NAME  - short feed name used for the cursor files
      STATEMENT_CLASS  - the gamma_bridge Statement that derives payload + uid
      get_queryset(options) -> queryset (will be ordered by id here)
      build_event(row) -> dict tracking event
      created_at_for(row) -> datetime or None  (event date; None => Gamma uses now())
      should_skip(row) -> bool                 (rows that aren't backfillable)
      row_label(row) -> str                    (for error lines)
    """

    CHECKPOINT_NAME = None
    STATEMENT_CLASS = None
    SAVE_EVERY = 200

    # ---- argument parsing -------------------------------------------------
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, dest='limit',
                            help='Stop after sending this many events (default: no limit).')
        parser.add_argument('--sleep-ms', type=int, default=0, dest='sleep_ms',
                            help='Pause between POSTs in milliseconds (default: 0).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Only report how many events would be sent.')
        parser.add_argument('--resume', action='store_true',
                            help='Skip rows up to the saved checkpoint and checkpoint progress as '
                                 'we go, so an interrupted run resumes instead of re-scanning.')
        parser.add_argument('--checkpoint-dir', default=DEFAULT_CHECKPOINT_DIR, dest='checkpoint_dir',
                            help='Directory for resume cursor files (default: %(default)s).')
        parser.add_argument('--course', default=None, dest='course_id',
                            help='Only replay rows of this course id (default: all).')
        parser.add_argument('--username', default=None, dest='username',
                            help='Only replay rows of this learner (default: all).')
        self.add_extra_arguments(parser)

    def add_extra_arguments(self, parser):
        """Hook for subclass-specific args."""

    # ---- subclass hooks ---------------------------------------------------
    def get_queryset(self, options):
        raise NotImplementedError

    def build_event(self, row):
        raise NotImplementedError

    def created_at_for(self, row):
        return None

    def should_skip(self, row):
        return False

    def row_label(self, row):
        return str(getattr(row, 'id', '?'))

    # ---- driver -----------------------------------------------------------
    def handle(self, *args, **options):
        conf = settings.FEATURES.get('RG_GAMIFICATION', {})
        storage = GammaStorage(
            enabled=conf.get('ENABLED'),
            endpoint=conf.get('RG_GAMIFICATION_ENDPOINT'),
            secret=conf.get('SECRET'),
            key=conf.get('KEY'),
        )
        if not (storage.is_enabled or options['dry_run']):
            raise CommandError('RG_GAMIFICATION is not enabled/configured in FEATURES.')

        # A dry-run must never persist cursor state, even with --resume.
        cp = Checkpoint(self.CHECKPOINT_NAME, options['checkpoint_dir'],
                        enabled=options['resume'] and not options['dry_run'])
        if cp.is_done():
            self.stdout.write(self.style.SUCCESS(
                '[%s] checkpoint marks this feed complete; nothing to do.' % self.CHECKPOINT_NAME))
            return

        qs = self.get_queryset(options).order_by('id')
        start_id = cp.load()
        if start_id:
            qs = qs.filter(id__gt=start_id)
            self.stdout.write('[%s] resuming after id %d.' % (self.CHECKPOINT_NAME, start_id))

        sent = created = duplicates = skipped = errors = 0
        last_id = start_id
        limit_hit = False

        for row in qs.iterator():
            if options['limit'] is not None and sent >= options['limit']:
                limit_hit = True
                break
            last_id = row.id

            if self.should_skip(row):
                skipped += 1
            elif options['dry_run']:
                sent += 1
            else:
                outcome = self._send(storage, row)
                if outcome == 'created':
                    sent += 1; created += 1
                elif outcome == 'duplicate':
                    sent += 1; duplicates += 1
                elif outcome == 'error':
                    errors += 1
                else:
                    sent += 1
                if options['sleep_ms']:
                    time.sleep(options['sleep_ms'] / 1000.0)

            if cp.enabled and (sent + skipped + errors) % self.SAVE_EVERY == 0:
                cp.save(last_id)

        cp.save(last_id)
        if not limit_hit and not options['dry_run']:
            cp.mark_done()

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                '[dry-run] %s: would send %d (%d skipped).' % (self.CHECKPOINT_NAME, sent, skipped)))
        else:
            self.stdout.write(self.style.SUCCESS(
                '%s: sent %d (%d created, %d duplicate, %d error, %d skipped); cursor id %s%s.' % (
                    self.CHECKPOINT_NAME, sent, created, duplicates, errors, skipped, last_id,
                    '' if limit_hit else ' [DONE]')))

    def _send(self, storage, row):
        try:
            statement = self.STATEMENT_CLASS(self.build_event(row))
            payload = dict(statement.data)
            when = self.created_at_for(row)
            if when is not None:
                payload['created_at'] = when.isoformat()
            storage.save(payload)
        except Exception as exc:  # noqa: B902 - per-row resilience, summarized at the end
            self.stderr.write('ERROR %s: %s' % (self.row_label(row), exc))
            return 'error'
        code = storage.response_data.status_code
        if code == 201:
            return 'created'
        if code == 400 and 'unique set' in storage.response_data.text:
            return 'duplicate'
        self.stderr.write('UNEXPECTED %s for %s: %s' % (code, self.row_label(row), storage.response_data.text[:200]))
        return 'error'

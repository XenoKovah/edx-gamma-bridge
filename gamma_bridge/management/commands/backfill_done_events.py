"""
Replay historical "Mark as complete" (DoneXBlock) state into Gamma as events.

Done state lives in courseware_studentmodule (module_type='done', state
{"done": true}); clicks from before the edx.done.toggled bridge mapping was
deployed never reached Gamma, so block-set badge rules cannot count them. This
command rebuilds each click as the exact event the live pipeline would have
sent — the payload (and the dedup uid) comes from UnitDoneStatement itself —
and POSTs it synchronously to Gamma.

Outcomes per row:
  - new event row: created in Gamma, dated by the StudentModule's modified
    time (so interval-filtered rules see it in the right window);
  - duplicate (already ingested live): rejected by Gamma's uniqueness, which
    also fills block_id onto rows from before that column existed;
  - after a run, grant retroactively via the badge recompute endpoint.

NOTE on points: Gamma awards EventConfiguration.award points for every NEW
event at ingest time (the award is read live, not from the event). To backfill
badge credit WITHOUT retroactive points, set the 'Mark a Unit as Complete'
award to 0 in the Gamma admin for the duration of the run, then restore it.
"""
import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from gamma_bridge.statements.completion import UnitDoneStatement
from gamma_bridge.storage import GammaStorage

DONE_BLOCK_TYPE = 'done'


class Command(BaseCommand):
    help = (
        "Replay historical DoneXBlock 'Mark as complete' state into Gamma so "
        "block-set badge rules can count it (see module docstring for the "
        "points caveat)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--course',
            dest='course_id',
            default=None,
            help='Only replay done blocks of this course id (default: all courses).',
        )
        parser.add_argument(
            '--username',
            dest='username',
            default=None,
            help='Only replay done blocks of this learner (default: all learners).',
        )
        parser.add_argument(
            '--limit',
            dest='limit',
            type=int,
            default=None,
            help='Stop after sending this many events (default: no limit).',
        )
        parser.add_argument(
            '--sleep-ms',
            dest='sleep_ms',
            type=int,
            default=0,
            help='Pause between POSTs in milliseconds (default: 0).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report how many events would be sent.',
        )

    def handle(self, *args, **options):
        # Imported here so the module stays importable outside the LMS (tests).
        from lms.djangoapps.courseware.models import StudentModule

        gamification_conf = settings.FEATURES.get('RG_GAMIFICATION', {})
        storage = GammaStorage(
            enabled=gamification_conf.get('ENABLED'),
            endpoint=gamification_conf.get('RG_GAMIFICATION_ENDPOINT'),
            secret=gamification_conf.get('SECRET'),
            key=gamification_conf.get('KEY'),
        )
        if not (storage.is_enabled or options['dry_run']):
            raise CommandError('RG_GAMIFICATION is not enabled/configured in FEATURES.')

        modules = (
            StudentModule.objects
            .filter(module_type=DONE_BLOCK_TYPE)
            .select_related('student')
            .order_by('id')
        )
        if options['course_id']:
            modules = modules.filter(course_id=options['course_id'])
        if options['username']:
            modules = modules.filter(student__username=options['username'])

        sent = created = duplicates = skipped = errors = 0
        for module in modules.iterator():
            if options['limit'] is not None and sent >= options['limit']:
                break

            try:
                state = json.loads(module.state or '{}')
            except ValueError:
                state = {}
            if state.get('done') is not True:
                skipped += 1
                continue

            if options['dry_run']:
                sent += 1
                continue

            try:
                statement = UnitDoneStatement(self._as_tracking_event(module))
                payload = dict(statement.data)
                payload['created_at'] = module.modified.isoformat()
                storage.save(payload)
            except Exception as exc:  # noqa: B902 - per-row resilience, summarized below
                errors += 1
                self.stderr.write(f'ERROR {module.module_state_key} for {module.student.username}: {exc}')
                continue

            sent += 1
            status_code = storage.response_data.status_code
            if status_code == 201:
                created += 1
            elif status_code == 400 and 'unique set' in storage.response_data.text:
                duplicates += 1
            else:
                errors += 1
                self.stderr.write(
                    f'UNEXPECTED {status_code} for {module.module_state_key} '
                    f'({module.student.username}): {storage.response_data.text[:200]}'
                )

            if options['sleep_ms']:
                time.sleep(options['sleep_ms'] / 1000.0)

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'[dry-run] would send {sent} done events ({skipped} rows skipped as not done).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Sent {sent}: {created} created, {duplicates} duplicates '
                f'(block_id repaired where missing), {errors} errors, {skipped} skipped.'
            ))

    @staticmethod
    def _as_tracking_event(module):
        """
        Rebuild the tracking event the live pipeline would have produced for this
        click, so UnitDoneStatement derives the identical payload and dedup uid.
        """
        course_key = module.course_id
        return {
            'event_type': 'edx.done.toggled',
            'username': module.student.username,
            'context': {
                'course_id': str(course_key),
                'org_id': course_key.org,
                'module': {'usage_key': str(module.module_state_key)},
            },
            'event': {'done': True},
        }

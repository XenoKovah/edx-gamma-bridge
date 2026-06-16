"""
Replay historical "Mark as complete" (DoneXBlock) state into Gamma as
edx.done.toggled events, so block-set / "Mark a Unit as Complete" badge rules can
count them. Done state lives in courseware_studentmodule (module_type='done',
state {"done": true}); unchecks (done != true) are skipped. Resume-safe (see
gamma_bridge.backfill_base). POINTS CAVEAT: set the 'Mark a Unit as Complete' award
to 0 for the run, then restore it.
"""
import json

from gamma_bridge.backfill_base import BaseBackfillCommand
from gamma_bridge.statements.completion import UnitDoneStatement

DONE_BLOCK_TYPE = 'done'


class Command(BaseBackfillCommand):
    help = "Replay DoneXBlock 'Mark as complete' state into Gamma (resume-safe)."
    CHECKPOINT_NAME = 'done'
    STATEMENT_CLASS = UnitDoneStatement

    def get_queryset(self, options):
        from lms.djangoapps.courseware.models import StudentModule
        qs = StudentModule.objects.filter(module_type=DONE_BLOCK_TYPE).select_related('student')
        if options['course_id']:
            qs = qs.filter(course_id=options['course_id'])
        if options['username']:
            qs = qs.filter(student__username=options['username'])
        return qs

    def should_skip(self, row):
        try:
            state = json.loads(row.state or '{}')
        except ValueError:
            state = {}
        return state.get('done') is not True

    def created_at_for(self, row):
        return row.modified

    def row_label(self, row):
        return '%s/%s' % (row.module_state_key, row.student_id)

    def build_event(self, row):
        ck = row.course_id
        return {
            'event_type': 'edx.done.toggled',
            'username': row.student.username,
            'context': {
                'course_id': str(ck),
                'org_id': ck.org,
                'module': {'usage_key': str(row.module_state_key)},
            },
            'event': {'done': True},
        }

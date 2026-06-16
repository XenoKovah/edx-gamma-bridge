"""
Replay historical problem submissions into Gamma as edx.grades.problem.submitted
events (one per learner-problem), so "Submit an Answer" badge rules can count them.
Resume-safe (see gamma_bridge.backfill_base). POINTS CAVEAT: set the 'Submit an
Answer' award to 0 for the run, then restore it.
"""
from gamma_bridge.backfill_base import BaseBackfillCommand
from gamma_bridge.statements.problem import ProblemSubmittedStatement

PROBLEM_BLOCK_TYPE = 'problem'


class Command(BaseBackfillCommand):
    help = "Replay problem StudentModule rows into Gamma (resume-safe)."
    CHECKPOINT_NAME = 'problem'
    STATEMENT_CLASS = ProblemSubmittedStatement

    def get_queryset(self, options):
        from lms.djangoapps.courseware.models import StudentModule
        qs = StudentModule.objects.filter(module_type=PROBLEM_BLOCK_TYPE).select_related('student')
        if options['course_id']:
            qs = qs.filter(course_id=options['course_id'])
        if options['username']:
            qs = qs.filter(student__username=options['username'])
        return qs

    def should_skip(self, row):
        return not (row.module_state_key and row.student_id)

    def created_at_for(self, row):
        return row.modified

    def row_label(self, row):
        return '%s/%s' % (row.module_state_key, row.student_id)

    def build_event(self, row):
        ck = row.course_id
        return {
            'event_type': 'edx.grades.problem.submitted',
            'username': row.student.username,
            'context': {'course_id': str(ck), 'org_id': ck.org},
            'event': {'problem_id': str(row.module_state_key)},
        }

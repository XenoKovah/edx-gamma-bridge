"""
Replay historical active enrollments into Gamma as edx.course.enrollment.activated
events, so "Enroll in a Course" badge rules can count them. Resume-safe (see
gamma_bridge.backfill_base). POINTS CAVEAT: set the 'Enroll in a Course' award to 0
in the Gamma admin for the run, then restore it, to backfill badge credit without
retroactive points.
"""
from gamma_bridge.backfill_base import BaseBackfillCommand
from gamma_bridge.statements.course import CourseEnrollmentStatement


class Command(BaseBackfillCommand):
    help = "Replay active CourseEnrollment rows into Gamma (resume-safe)."
    CHECKPOINT_NAME = 'enrollment'
    STATEMENT_CLASS = CourseEnrollmentStatement

    def get_queryset(self, options):
        from common.djangoapps.student.models import CourseEnrollment
        qs = CourseEnrollment.objects.filter(is_active=True).select_related('user')
        if options['course_id']:
            qs = qs.filter(course_id=options['course_id'])
        if options['username']:
            qs = qs.filter(user__username=options['username'])
        return qs

    def should_skip(self, row):
        return not (row.user_id and row.course_id)

    def created_at_for(self, row):
        return row.created

    def row_label(self, row):
        return '%s/%s' % (row.course_id, row.user_id)

    def build_event(self, row):
        ck = row.course_id
        return {
            'event_type': 'edx.course.enrollment.activated',
            'username': row.user.username,
            'context': {'course_id': str(ck), 'org_id': ck.org},
            'event': {'course_id': str(ck), 'user_id': row.user_id, 'mode': row.mode},
        }

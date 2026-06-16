"""
Replay historical forum activity into Gamma as edx.forum.* events.

Forum content on this deployment lives in MongoDB cs_comments_service.contents
(forum v1); the forum-v2 MySQL tables are empty here. Threads, responses, comments
and votes from before the edx.forum.* bridge mappings were deployed never reached
Gamma, so the four forum badge rules cannot count them:

  CommentThread                         -> edx.forum.thread.created   (ForumThreadStatement)
  Comment (parent_id is null)           -> edx.forum.response.created (ForumResponseStatement)
  Comment (parent_id is set)            -> edx.forum.comment.created  (ForumCommentStatement)
  CommentThread.votes.up[voter]         -> edx.forum.thread.voted     (ForumVoteStatement)

This command rebuilds each item as the exact event the live pipeline would have
sent — the payload (and the dedup uid) comes from the Forum*Statement classes
themselves — and POSTs it synchronously to Gamma.

Dedup uids: thread/response/comment use the content's mongo id; a vote uses
"{thread_id}_{voter_username}" and awards the THREAD AUTHOR (target_username), not
the voter — matching ForumVoteStatement.

Dating: threads/responses/comments are dated by their Mongo created_at. Votes carry
no per-vote timestamp in cs_comments_service, so they fall back to the thread's
created_at (interval-filtered vote rules are therefore approximate).

NOTE on points: Gamma awards EventConfiguration.award points for every NEW event at
ingest time. To backfill badge credit WITHOUT retroactive points, set the four forum
awards (Add a Discussion Post / Response to a Discussion Post / Comment a Discussion
Response / Someone likes your Post) to 0 in the Gamma admin for the run, then restore.
"""
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from gamma_bridge.statements.forum import (
    ForumCommentStatement,
    ForumResponseStatement,
    ForumThreadStatement,
    ForumVoteStatement,
)
from gamma_bridge.storage import GammaStorage

ALL_KINDS = ('thread', 'response', 'comment', 'vote')


class Command(BaseCommand):
    help = (
        "Replay historical forum threads/responses/comments/votes from MongoDB "
        "cs_comments_service into Gamma so the forum badge rules can count them "
        "(see module docstring for the points caveat)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--course',
            dest='course_id',
            default=None,
            help='Only replay items of this course id (default: all courses).',
        )
        parser.add_argument(
            '--kinds',
            dest='kinds',
            default=','.join(ALL_KINDS),
            help='Comma list of kinds to replay: thread,response,comment,vote (default: all).',
        )
        parser.add_argument(
            '--limit',
            dest='limit',
            type=int,
            default=None,
            help='Stop after sending this many events total (default: no limit).',
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
        parser.add_argument('--mongo-host', dest='mongo_host', default='mongodb')
        parser.add_argument('--mongo-port', dest='mongo_port', type=int, default=27017)
        parser.add_argument('--mongo-db', dest='mongo_db', default='cs_comments_service')

    def handle(self, *args, **options):
        import pymongo

        gamification_conf = settings.FEATURES.get('RG_GAMIFICATION', {})
        storage = GammaStorage(
            enabled=gamification_conf.get('ENABLED'),
            endpoint=gamification_conf.get('RG_GAMIFICATION_ENDPOINT'),
            secret=gamification_conf.get('SECRET'),
            key=gamification_conf.get('KEY'),
        )
        if not (storage.is_enabled or options['dry_run']):
            raise CommandError('RG_GAMIFICATION is not enabled/configured in FEATURES.')

        kinds = [k.strip() for k in options['kinds'].split(',') if k.strip()]
        bad = set(kinds) - set(ALL_KINDS)
        if bad:
            raise CommandError(f'Unknown --kinds {sorted(bad)}; allowed: {ALL_KINDS}.')

        client = pymongo.MongoClient(
            host=options['mongo_host'],
            port=options['mongo_port'],
            serverSelectionTimeoutMS=8000,
        )
        contents = client[options['mongo_db']]['contents']
        course_match = {'course_id': options['course_id']} if options['course_id'] else {}

        # Cache external_id (mongo author/voter id) -> username lookups.
        user_model = get_user_model()
        username_by_id = {}

        def username_for_id(uid):
            if uid is None:
                return None
            key = str(uid)
            if key not in username_by_id:
                try:
                    username_by_id[key] = user_model.objects.values_list(
                        'username', flat=True
                    ).get(id=int(key))
                except (ValueError, user_model.DoesNotExist):
                    username_by_id[key] = None
            return username_by_id[key]

        counters = {'sent': 0, 'created': 0, 'duplicates': 0, 'skipped': 0, 'errors': 0}

        def at_limit():
            return options['limit'] is not None and counters['sent'] >= options['limit']

        def emit(statement_cls, event, when, label):
            """Build + POST one statement (or just count in dry-run)."""
            if options['dry_run']:
                counters['sent'] += 1
                return
            try:
                statement = statement_cls(event)
                payload = dict(statement.data)
                if when is not None:
                    payload['created_at'] = when.isoformat()
                storage.save(payload)
            except Exception as exc:  # noqa: B902 - per-row resilience, summarized below
                counters['errors'] += 1
                self.stderr.write(f'ERROR {label}: {exc}')
                return
            counters['sent'] += 1
            status_code = storage.response_data.status_code
            if status_code == 201:
                counters['created'] += 1
            elif status_code == 400 and 'unique set' in storage.response_data.text:
                counters['duplicates'] += 1
            else:
                counters['errors'] += 1
                self.stderr.write(f'UNEXPECTED {status_code} for {label}: {storage.response_data.text[:200]}')
            if options['sleep_ms']:
                time.sleep(options['sleep_ms'] / 1000.0)

        # --- Threads + thread votes --------------------------------------------
        if 'thread' in kinds or 'vote' in kinds:
            q = dict(course_match, _type='CommentThread')
            for doc in contents.find(q):
                if at_limit():
                    break
                course_id = doc.get('course_id') or ''
                author = doc.get('author_username')
                thread_id = str(doc.get('_id'))

                if 'thread' in kinds:
                    if not author or not course_id:
                        counters['skipped'] += 1
                    else:
                        emit(
                            ForumThreadStatement,
                            self._content_event('edx.forum.thread.created', author, course_id, thread_id),
                            doc.get('created_at'),
                            f'thread {thread_id}',
                        )

                if 'vote' in kinds and not at_limit():
                    up_voters = ((doc.get('votes') or {}).get('up')) or []
                    for voter_id in up_voters:
                        if at_limit():
                            break
                        voter = username_for_id(voter_id)
                        if not voter or not author or not course_id:
                            counters['skipped'] += 1
                            continue
                        emit(
                            ForumVoteStatement,
                            self._vote_event(voter, author, course_id, thread_id),
                            doc.get('created_at'),
                            f'vote {thread_id} by {voter}',
                        )

        # --- Responses + comments ----------------------------------------------
        want_resp = 'response' in kinds
        want_comment = 'comment' in kinds
        if want_resp or want_comment:
            q = dict(course_match, _type='Comment')
            for doc in contents.find(q):
                if at_limit():
                    break
                is_comment = doc.get('parent_id') is not None
                if is_comment and not want_comment:
                    continue
                if (not is_comment) and not want_resp:
                    continue

                course_id = doc.get('course_id') or ''
                author = doc.get('author_username')
                content_id = str(doc.get('_id'))
                if not author or not course_id:
                    counters['skipped'] += 1
                    continue

                if is_comment:
                    statement_cls = ForumCommentStatement
                    event_type = 'edx.forum.comment.created'
                    label = f'comment {content_id}'
                else:
                    statement_cls = ForumResponseStatement
                    event_type = 'edx.forum.response.created'
                    label = f'response {content_id}'

                emit(
                    statement_cls,
                    self._content_event(event_type, author, course_id, content_id),
                    doc.get('created_at'),
                    label,
                )

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f"[dry-run] would send {counters['sent']} forum events "
                f"({counters['skipped']} skipped) for kinds={kinds}."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Sent {counters['sent']}: {counters['created']} created, "
                f"{counters['duplicates']} duplicates, {counters['errors']} errors, "
                f"{counters['skipped']} skipped."
            ))

    @staticmethod
    def _content_event(event_type, author_username, course_id, content_id):
        """Tracking event for a thread/response/comment (uid = event.id)."""
        return {
            'event_type': event_type,
            'username': author_username,
            'context': {'course_id': course_id, 'org_id': _org_of(course_id)},
            'event': {'id': content_id},
        }

    @staticmethod
    def _vote_event(voter_username, author_username, course_id, thread_id):
        """
        Tracking event for an up-vote. ForumVoteStatement reads the voter from the
        top-level username (uid = "{thread_id}_{voter}") and awards the thread
        author via event.target_username.
        """
        return {
            'event_type': 'edx.forum.thread.voted',
            'username': voter_username,
            'context': {'course_id': course_id, 'org_id': _org_of(course_id)},
            'event': {'id': thread_id, 'target_username': author_username},
        }


def _org_of(course_id):
    """Best-effort org from a course-v1 key, mirroring BaseCourse.get_org."""
    import re
    if result := re.match(r"^course-v1:([^+]+)", course_id or ''):
        return result.group(1)
    return ''

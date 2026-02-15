"""Load test for critical API endpoints with 50+ simulated users.

Creates realistic parent users with children, courses, conversations,
and notifications, then hammers the dashboard, messages, and notifications
endpoints concurrently.  Reports per-endpoint P50/P95/P99 latency and
exits with code 1 if any endpoint exceeds the threshold.

Usage:
  python -m scripts.load_test                          # default 50 users
  python -m scripts.load_test --users 10 --requests 5  # quick smoke test
  python -m scripts.load_test --skip-teardown           # keep data for inspection
"""
import argparse
import asyncio
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, get_password_hash
from app.db.database import SessionLocal, engine as default_engine, Base
from app.models import (
    User, Teacher, Student, Course, Assignment, Conversation, Message,
    Notification, Task, AuditLog,
)
from app.models.user import UserRole
from app.models.teacher import TeacherType
from app.models.student import parent_students, student_teachers, RelationshipType
from app.models.notification import NotificationType
from app.models.course import student_courses
from app.models.token_blacklist import TokenBlacklist

LOADTEST_PASSWORD = "LoadTest2026!"
EMAIL_PREFIX = "loadtest"
EMAIL_DOMAIN = "classbridge.local"


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Data setup
# ---------------------------------------------------------------------------

def setup_test_data(num_parents: int = 50, database_url: str | None = None) -> list[dict]:
    """Create parent users with full data hierarchies.

    Returns list of dicts with ``id`` and ``email`` for each parent.
    """
    if database_url:
        eng = create_engine(database_url)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    else:
        eng = default_engine
        Session = SessionLocal
    Base.metadata.create_all(bind=eng)
    db = Session()

    try:
        pw = get_password_hash(LOADTEST_PASSWORD)
        t = _now()
        num_teachers = max(1, num_parents // 10)

        # ── Teachers ────────────────────────────────────────
        teacher_users = []
        teachers = []
        for i in range(num_teachers):
            tu = User(
                email=f"{EMAIL_PREFIX}-teacher-{i}@{EMAIL_DOMAIN}",
                full_name=f"LoadTest Teacher {i}",
                role=UserRole.TEACHER,
                hashed_password=pw,
            )
            teacher_users.append(tu)
        db.add_all(teacher_users)
        db.flush()

        for tu in teacher_users:
            tr = Teacher(
                user_id=tu.id,
                school_name="LoadTest Academy",
                department="Testing",
                teacher_type=TeacherType.SCHOOL_TEACHER,
            )
            teachers.append(tr)
        db.add_all(teachers)
        db.flush()

        # ── Courses (3 per teacher) ─────────────────────────
        courses = []
        for ti, tr in enumerate(teachers):
            for ci in range(3):
                c = Course(
                    name=f"LT Course {ti}-{ci}",
                    subject="Testing",
                    teacher_id=tr.id,
                )
                courses.append(c)
        db.add_all(courses)
        db.flush()

        # ── Assignments (4 per course) ──────────────────────
        for c in courses:
            for ai in range(4):
                offset = [-3, 0, 5, 14][ai]
                db.add(Assignment(
                    title=f"LT Assignment {c.id}-{ai}",
                    description="Load test assignment",
                    course_id=c.id,
                    due_date=t + timedelta(days=offset),
                    max_points=100,
                ))
        db.flush()

        # ── Parents with children ───────────────────────────
        parent_users = []
        tokens = []

        for i in range(num_parents):
            # Parent user
            pu = User(
                email=f"{EMAIL_PREFIX}-parent-{i}@{EMAIL_DOMAIN}",
                full_name=f"LoadTest Parent {i}",
                role=UserRole.PARENT,
                hashed_password=pw,
            )
            db.add(pu)
            db.flush()

            # 2 children per parent
            child_students = []
            for ci in range(2):
                su = User(
                    email=f"{EMAIL_PREFIX}-student-{i}-{ci}@{EMAIL_DOMAIN}",
                    full_name=f"LoadTest Student {i}-{ci}",
                    role=UserRole.STUDENT,
                    hashed_password=pw,
                )
                db.add(su)
                db.flush()

                st = Student(
                    user_id=su.id,
                    grade_level=8,
                    school_name="LoadTest Academy",
                )
                db.add(st)
                db.flush()

                # Link parent → student
                db.execute(parent_students.insert().values(
                    parent_id=pu.id,
                    student_id=st.id,
                    relationship_type=RelationshipType.GUARDIAN,
                ))

                # Assign teacher (round-robin)
                teacher_idx = i % num_teachers
                teacher_u = teacher_users[teacher_idx]
                db.execute(student_teachers.insert().values(
                    student_id=st.id,
                    teacher_user_id=teacher_u.id,
                    teacher_name=teacher_u.full_name,
                    teacher_email=teacher_u.email,
                    added_by_user_id=pu.id,
                ))

                # Enroll in that teacher's courses
                teacher_courses = courses[teacher_idx * 3:(teacher_idx + 1) * 3]
                for tc in teacher_courses:
                    db.execute(student_courses.insert().values(
                        student_id=st.id, course_id=tc.id,
                    ))

                child_students.append(st)

            # 2 tasks per parent
            for ti in range(2):
                db.add(Task(
                    created_by_user_id=pu.id,
                    assigned_to_user_id=pu.id,
                    title=f"LT Task {i}-{ti}",
                    description="Load test task",
                    due_date=t + timedelta(days=ti + 1),
                    priority="medium",
                    category="Testing",
                ))

            # 1 conversation with the teacher (3 messages, 1 unread)
            teacher_idx = i % num_teachers
            conv = Conversation(
                participant_1_id=teacher_users[teacher_idx].id,
                participant_2_id=pu.id,
                student_id=child_students[0].id,
                subject=f"About student {i}",
            )
            db.add(conv)
            db.flush()

            for mi in range(3):
                sender = teacher_users[teacher_idx] if mi % 2 == 0 else pu
                db.add(Message(
                    conversation_id=conv.id,
                    sender_id=sender.id,
                    content=f"Load test message {mi}",
                    is_read=(mi < 2),
                    created_at=t - timedelta(hours=3 - mi),
                ))

            # 3 notifications (1 unread, 2 read)
            for ni in range(3):
                db.add(Notification(
                    user_id=pu.id,
                    type=NotificationType.SYSTEM,
                    title=f"LT Notification {i}-{ni}",
                    content="Load test notification",
                    link="/dashboard",
                    read=(ni > 0),
                ))

            parent_users.append(pu)

        db.commit()

        print(f"  Created {num_parents} parents, {num_parents * 2} students, "
              f"{num_teachers} teachers, {len(courses)} courses")
        return [{"id": pu.id, "email": pu.email} for pu in parent_users]

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------

def acquire_tokens(base_url: str, users: list[dict]) -> list[str]:
    """Get valid JWT tokens for each user.

    Tries pre-generating tokens first (fast, works when script and server share
    the same SECRET_KEY).  Falls back to login via the API when keys differ.
    """
    # Try pre-generated token with a probe request
    probe = users[0]
    token = create_access_token(data={"sub": str(probe["id"])})
    resp = httpx.get(
        f"{base_url}/api/notifications/unread-count",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    if resp.status_code != 401:
        # Keys match — pre-generate all tokens (instant)
        print("  Pre-generating tokens (secret keys match)...")
        return [create_access_token(data={"sub": str(u["id"])}) for u in users]

    # Keys differ — login via API (rate-limited to 5/min)
    print("  Logging in via API (secret keys differ — this may take a while)...")
    BATCH = 4  # stay under 5/min limit
    tokens: list[str] = []
    for i in range(0, len(users), BATCH):
        if i > 0:
            wait = 62
            print(f"  Rate limit pause... ({len(tokens)}/{len(users)} logged in)")
            time.sleep(wait)
        batch = users[i : i + BATCH]
        for u in batch:
            for attempt in range(3):
                r = httpx.post(
                    f"{base_url}/api/auth/login",
                    data={"username": u["email"], "password": LOADTEST_PASSWORD},
                    timeout=10.0,
                )
                if r.status_code == 429:
                    time.sleep(62)
                    continue
                r.raise_for_status()
                tokens.append(r.json()["access_token"])
                break
    print(f"  Acquired {len(tokens)} tokens.")
    return tokens


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_test_data(database_url: str | None = None):
    """Delete all loadtest-* data in dependency order."""
    if database_url:
        eng = create_engine(database_url)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    else:
        eng = default_engine
        Session = SessionLocal
    db = Session()

    try:
        # Find all loadtest user IDs
        lt_users = db.query(User).filter(
            User.email.like(f"{EMAIL_PREFIX}-%@{EMAIL_DOMAIN}")
        ).all()
        if not lt_users:
            print("  No loadtest data found.")
            return

        user_ids = [u.id for u in lt_users]
        parent_ids = [u.id for u in lt_users if u.role == UserRole.PARENT]
        teacher_ids = [u.id for u in lt_users if u.role == UserRole.TEACHER]
        student_user_ids = [u.id for u in lt_users if u.role == UserRole.STUDENT]

        # Student record IDs
        student_records = db.query(Student).filter(
            Student.user_id.in_(student_user_ids)
        ).all()
        student_ids = [s.id for s in student_records]

        # Teacher record IDs
        teacher_records = db.query(Teacher).filter(
            Teacher.user_id.in_(teacher_ids)
        ).all()
        teacher_rec_ids = [t.id for t in teacher_records]

        # Course IDs owned by loadtest teachers
        lt_courses = db.query(Course).filter(
            Course.teacher_id.in_(teacher_rec_ids)
        ).all()
        course_ids = [c.id for c in lt_courses]

        # Delete in dependency order — explicitly delete all FK refs
        # since SQLite CASCADE may not fire via ORM bulk delete.
        if user_ids:
            # Conversations where either participant is a loadtest user
            conv_ids = [c.id for c in db.query(Conversation.id).filter(or_(
                Conversation.participant_1_id.in_(user_ids),
                Conversation.participant_2_id.in_(user_ids),
            )).all()]
            if conv_ids:
                db.query(Message).filter(
                    Message.conversation_id.in_(conv_ids)).delete(
                    synchronize_session=False)
                db.query(Conversation).filter(
                    Conversation.id.in_(conv_ids)).delete(
                    synchronize_session=False)
            db.query(Notification).filter(
                Notification.user_id.in_(user_ids)).delete(
                synchronize_session=False)
            db.query(Task).filter(or_(
                Task.created_by_user_id.in_(user_ids),
                Task.assigned_to_user_id.in_(user_ids),
            )).delete(synchronize_session=False)
            # Token blacklist and audit logs reference users
            db.query(TokenBlacklist).filter(
                TokenBlacklist.user_id.in_(user_ids)).delete(
                synchronize_session=False)
            db.query(AuditLog).filter(
                AuditLog.user_id.in_(user_ids)).delete(
                synchronize_session=False)
        if student_ids:
            db.execute(student_courses.delete().where(
                student_courses.c.student_id.in_(student_ids)))
            db.execute(parent_students.delete().where(
                parent_students.c.student_id.in_(student_ids)))
            db.execute(student_teachers.delete().where(
                student_teachers.c.student_id.in_(student_ids)))
        # Also clean student_teachers by teacher_user_id and added_by_user_id
        if user_ids:
            db.execute(student_teachers.delete().where(
                student_teachers.c.teacher_user_id.in_(user_ids)))
            db.execute(student_teachers.delete().where(
                student_teachers.c.added_by_user_id.in_(user_ids)))
        if course_ids:
            db.query(Assignment).filter(
                Assignment.course_id.in_(course_ids)).delete(
                synchronize_session=False)
            db.query(Course).filter(
                Course.id.in_(course_ids)).delete(
                synchronize_session=False)
        if student_ids:
            db.query(Student).filter(
                Student.id.in_(student_ids)).delete(
                synchronize_session=False)
        if teacher_rec_ids:
            db.query(Teacher).filter(
                Teacher.id.in_(teacher_rec_ids)).delete(
                synchronize_session=False)
        if user_ids:
            db.query(User).filter(
                User.id.in_(user_ids)).delete(
                synchronize_session=False)

        db.commit()
        count = len(user_ids)
        print(f"  Cleaned up {count} loadtest users and related data.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

async def _request(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    name: str,
    results: list,
):
    """Fire one GET request, record result. Captures connection errors."""
    start = time.perf_counter()
    try:
        resp = await client.get(url, headers=headers)
        status = resp.status_code
    except (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError):
        status = 503  # treat connection failures as server error
    elapsed = (time.perf_counter() - start) * 1000
    results.append((name, status, elapsed))


async def worker_dashboard(
    base_url: str,
    token: str,
    requests_per_user: int,
    results: list,
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(requests_per_user):
            await _request(
                client, f"{base_url}/api/parent/dashboard",
                headers, "dashboard", results)


async def worker_messages(
    base_url: str,
    token: str,
    requests_per_user: int,
    results: list,
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(requests_per_user):
            await _request(
                client, f"{base_url}/api/messages/conversations",
                headers, "messages", results)


async def worker_notifications(
    base_url: str,
    token: str,
    requests_per_user: int,
    results: list,
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(requests_per_user):
            endpoint = "/api/notifications/" if i % 2 == 0 else "/api/notifications/unread-count"
            await _request(
                client, f"{base_url}{endpoint}",
                headers, "notifications", results)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_load_test(
    base_url: str,
    tokens: list[str],
    requests_per_user: int,
) -> list:
    results: list = []
    tasks = []
    for token in tokens:
        tasks.append(worker_dashboard(base_url, token, requests_per_user, results))
        tasks.append(worker_messages(base_url, token, requests_per_user, results))
        tasks.append(worker_notifications(base_url, token, requests_per_user, results))

    start = time.perf_counter()
    await asyncio.gather(*tasks)
    wall_time = time.perf_counter() - start

    total = len(results)
    rps = total / wall_time if wall_time > 0 else 0
    print(f"\n  Completed {total} requests in {wall_time:.1f}s ({rps:.0f} req/s)\n")
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_results(results: list, threshold_ms: int = 500) -> bool:
    by_endpoint: dict[str, list] = defaultdict(list)
    for name, status_code, elapsed in results:
        by_endpoint[name].append((status_code, elapsed))

    all_pass = True

    print(f"  {'Endpoint':<20} {'Result':>6}  {'Avg':>7}  {'P50':>7}  "
          f"{'P95':>7}  {'P99':>7}  {'Errors':>8}")
    print("  " + "-" * 78)

    for name in sorted(by_endpoint):
        entries = by_endpoint[name]
        latencies = [e for _, e in entries]
        errors = sum(1 for s, _ in entries if s >= 400)

        avg = statistics.mean(latencies)
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[n // 2]
        p95 = sorted_lat[int(n * 0.95)]
        p99 = sorted_lat[int(n * 0.99)]

        passed = p95 < threshold_ms and errors == 0
        if not passed:
            all_pass = False
        tag = "PASS" if passed else "FAIL"

        print(f"  {name:<20} {tag:>6}  {avg:>6.0f}ms  {p50:>6.0f}ms  "
              f"{p95:>6.0f}ms  {p99:>6.0f}ms  {errors:>3}/{len(entries)}")

    print()
    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Load test ClassBridge endpoints with simulated parent users.")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Server base URL (default: http://localhost:8000)")
    parser.add_argument("--users", type=int, default=50,
                        help="Number of simulated parent users (default: 50)")
    parser.add_argument("--requests", type=int, default=10,
                        help="Requests per user per endpoint (default: 10)")
    parser.add_argument("--threshold", type=int, default=500,
                        help="P95 latency threshold in ms (default: 500)")
    parser.add_argument("--skip-setup", action="store_true",
                        help="Skip data setup (reuse existing loadtest data)")
    parser.add_argument("--skip-teardown", action="store_true",
                        help="Keep loadtest data after run")
    parser.add_argument("--database-url", default=None,
                        help="Database URL for setup/teardown (default: from .env)")
    args = parser.parse_args()

    total_requests = args.users * args.requests * 3
    print()
    print("=" * 60)
    print("  ClassBridge Load Test")
    print("=" * 60)
    print(f"  Target:     {args.base_url}")
    print(f"  Users:      {args.users}")
    print(f"  Requests:   {args.requests} per user per endpoint")
    print(f"  Total:      {total_requests} requests across 3 endpoints")
    print(f"  Threshold:  P95 < {args.threshold}ms")
    print("=" * 60)

    # Setup
    if args.skip_setup:
        print("\n[SETUP] Skipped — loading existing data...")
        if args.database_url:
            eng = create_engine(args.database_url)
            Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        else:
            Session = SessionLocal
        db = Session()
        try:
            parents = db.query(User).filter(
                User.email.like(f"{EMAIL_PREFIX}-parent-%@{EMAIL_DOMAIN}")
            ).limit(args.users).all()
            if not parents:
                print("  ERROR: No loadtest parent users found. Run without --skip-setup first.")
                sys.exit(1)
            users_info = [{"id": p.id, "email": p.email} for p in parents]
            print(f"  Found {len(users_info)} existing parent users.")
        finally:
            db.close()
    else:
        print("\n[SETUP] Creating test data...")
        users_info = setup_test_data(args.users, args.database_url)

    print("\n[AUTH] Acquiring tokens...")
    tokens = acquire_tokens(args.base_url, users_info)

    # Load test
    print(f"\n[LOAD TEST] Firing {total_requests} requests...")
    results = asyncio.run(run_load_test(args.base_url, tokens, args.requests))

    # Report
    print("[RESULTS]")
    all_pass = report_results(results, args.threshold)

    # Teardown
    if not args.skip_teardown and not args.skip_setup:
        print("[TEARDOWN] Cleaning up test data...")
        cleanup_test_data(args.database_url)
    elif args.skip_teardown:
        print("[TEARDOWN] Skipped — loadtest data preserved.")

    # Exit code
    if all_pass:
        print("OVERALL: PASS — all endpoints within threshold")
        sys.exit(0)
    else:
        print(f"OVERALL: FAIL — one or more endpoints exceeded {args.threshold}ms P95")
        sys.exit(1)


if __name__ == "__main__":
    main()

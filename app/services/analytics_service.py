"""Analytics aggregation service.

All grade computations join StudentAssignment -> Assignment -> Course
and compute percentage as (sa.grade / assignment.max_points) * 100.
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.analytics import ProgressReport
from app.models.assignment import Assignment, StudentAssignment
from app.models.course import Course, student_courses
from app.models.student import Student

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core query helpers
# ---------------------------------------------------------------------------

def _base_graded_query(db: Session, student_id: int, course_id: int | None = None):
    """Return a query of (StudentAssignment, Assignment, Course) for graded rows."""
    query = (
        db.query(StudentAssignment, Assignment, Course)
        .join(Assignment, StudentAssignment.assignment_id == Assignment.id)
        .join(Course, Assignment.course_id == Course.id)
        .filter(
            StudentAssignment.student_id == student_id,
            StudentAssignment.grade.isnot(None),
            Assignment.max_points.isnot(None),
            Assignment.max_points > 0,
        )
    )
    if course_id:
        query = query.filter(Assignment.course_id == course_id)
    return query


def _total_assignments_query(db: Session, student_id: int) -> int:
    """Count all assignments for courses the student is enrolled in."""
    enrolled_course_ids = (
        db.query(student_courses.c.course_id)
        .filter(student_courses.c.student_id == student_id)
        .subquery()
    )
    return (
        db.query(sa_func.count(Assignment.id))
        .filter(Assignment.course_id.in_(db.query(enrolled_course_ids.c.course_id)))
        .scalar()
    ) or 0


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_graded_assignments(
    db: Session,
    student_id: int,
    course_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated graded assignments with computed percentages."""
    query = _base_graded_query(db, student_id, course_id)
    total = query.count()

    rows = (
        query
        .order_by(
            Assignment.due_date.desc().nullslast(),
            StudentAssignment.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    grades = []
    for sa, assignment, course in rows:
        pct = round((sa.grade / assignment.max_points) * 100, 2)
        grades.append({
            "student_assignment_id": sa.id,
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "course_id": course.id,
            "course_name": course.name,
            "grade": sa.grade,
            "max_points": assignment.max_points,
            "percentage": pct,
            "status": sa.status,
            "submitted_at": sa.submitted_at,
            "due_date": assignment.due_date,
        })

    return grades, total


def compute_summary(db: Session, student_id: int) -> dict:
    """Compute overall average, per-course averages, trend, completion rate."""
    rows = _base_graded_query(db, student_id).all()

    if not rows:
        return {
            "overall_average": 0.0,
            "total_graded": 0,
            "total_assignments": _total_assignments_query(db, student_id),
            "completion_rate": 0.0,
            "course_averages": [],
            "trend": "stable",
        }

    percentages = []
    course_data: dict[int, dict] = {}

    for sa, assignment, course in rows:
        pct = (sa.grade / assignment.max_points) * 100
        percentages.append(pct)

        if course.id not in course_data:
            course_data[course.id] = {
                "course_id": course.id,
                "course_name": course.name,
                "percentages": [],
                "graded_count": 0,
            }
        course_data[course.id]["percentages"].append(pct)
        course_data[course.id]["graded_count"] += 1

    overall_avg = round(sum(percentages) / len(percentages), 2)
    total_assignments = _total_assignments_query(db, student_id)
    total_graded = len(rows)

    # Per-course averages
    course_averages = []
    for cid, cdata in course_data.items():
        total_in_course = (
            db.query(sa_func.count(Assignment.id))
            .filter(Assignment.course_id == cid)
            .scalar()
        ) or 0
        avg_pct = round(sum(cdata["percentages"]) / len(cdata["percentages"]), 2)
        completion = round((cdata["graded_count"] / total_in_course) * 100, 2) if total_in_course else 0.0
        course_averages.append({
            "course_id": cid,
            "course_name": cdata["course_name"],
            "average_percentage": avg_pct,
            "graded_count": cdata["graded_count"],
            "total_count": total_in_course,
            "completion_rate": completion,
        })

    completion_rate = round((total_graded / total_assignments) * 100, 2) if total_assignments else 0.0

    # Compute trend from chronological order
    trend_rows = (
        _base_graded_query(db, student_id)
        .order_by(
            Assignment.due_date.asc().nullslast(),
            StudentAssignment.created_at.asc(),
        )
        .all()
    )
    chrono_pcts = [(sa.grade / a.max_points) * 100 for sa, a, _ in trend_rows]
    trend = determine_trend(chrono_pcts)

    return {
        "overall_average": overall_avg,
        "total_graded": total_graded,
        "total_assignments": total_assignments,
        "completion_rate": completion_rate,
        "course_averages": course_averages,
        "trend": trend,
    }


def compute_trend_points(
    db: Session,
    student_id: int,
    course_id: int | None = None,
    days: int = 90,
) -> tuple[list[dict], str]:
    """Return chronological trend points and overall trend string."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = _base_graded_query(db, student_id, course_id).filter(
        (Assignment.due_date >= cutoff) | (StudentAssignment.created_at >= cutoff)
    )
    rows = query.order_by(
        Assignment.due_date.asc().nullslast(),
        StudentAssignment.created_at.asc(),
    ).all()

    points = []
    pcts = []
    for sa, assignment, course in rows:
        pct = round((sa.grade / assignment.max_points) * 100, 2)
        pcts.append(pct)
        date_val = assignment.due_date or sa.created_at
        points.append({
            "date": date_val.isoformat() if date_val else "",
            "percentage": pct,
            "assignment_title": assignment.title,
            "course_name": course.name,
        })

    return points, determine_trend(pcts)


def determine_trend(percentages: list[float]) -> str:
    """Given chronological percentages, return 'improving'/'declining'/'stable'."""
    if len(percentages) < 3:
        return "stable"
    third = max(1, len(percentages) // 3)
    first_avg = sum(percentages[:third]) / third
    last_avg = sum(percentages[-third:]) / third
    if last_avg > first_avg + 3:
        return "improving"
    elif last_avg < first_avg - 3:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# Weekly report (cached in ProgressReport)
# ---------------------------------------------------------------------------

def _current_week_bounds() -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Sunday 23:59:59) for the current week."""
    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


def get_or_create_weekly_report(db: Session, student_id: int) -> dict:
    """Return cached weekly report or compute a fresh one."""
    start, end = _current_week_bounds()

    existing = (
        db.query(ProgressReport)
        .filter(
            ProgressReport.student_id == student_id,
            ProgressReport.report_type == "weekly",
            ProgressReport.period_start == start,
        )
        .first()
    )

    if existing and existing.generated_at:
        age = datetime.utcnow() - existing.generated_at
        if age < timedelta(hours=24):
            return {
                "id": existing.id,
                "student_id": existing.student_id,
                "report_type": existing.report_type,
                "period_start": existing.period_start,
                "period_end": existing.period_end,
                "data": json.loads(existing.data),
                "generated_at": existing.generated_at,
            }

    # Compute fresh report
    summary = compute_summary(db, student_id)
    points, trend = compute_trend_points(db, student_id, days=7)

    report_data = {
        "overall_average": summary["overall_average"],
        "total_graded": summary["total_graded"],
        "completion_rate": summary["completion_rate"],
        "trend": trend,
        "course_summaries": summary["course_averages"],
        "grades_this_week": len(points),
    }

    data_json = json.dumps(report_data)

    if existing:
        existing.data = data_json
        existing.generated_at = datetime.utcnow()
        existing.period_end = end
    else:
        existing = ProgressReport(
            student_id=student_id,
            report_type="weekly",
            period_start=start,
            period_end=end,
            data=data_json,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return {
        "id": existing.id,
        "student_id": existing.student_id,
        "report_type": existing.report_type,
        "period_start": existing.period_start,
        "period_end": existing.period_end,
        "data": json.loads(existing.data),
        "generated_at": existing.generated_at,
    }


# ---------------------------------------------------------------------------
# AI Insights (on-demand)
# ---------------------------------------------------------------------------

async def generate_ai_insight(
    db: Session,
    student_id: int,
    focus_area: str | None = None,
) -> str:
    """Gather grade data, build prompt, call AI, return markdown insight."""
    from app.services.ai_service import generate_content

    student = db.query(Student).filter(Student.id == student_id).first()
    student_name = student.user.full_name if student and student.user else "Student"

    summary = compute_summary(db, student_id)
    grades, _ = get_graded_assignments(db, student_id, limit=10)

    # Build recent grades text
    recent_lines = []
    for g in grades:
        recent_lines.append(
            f"- {g['assignment_title']} ({g['course_name']}): "
            f"{g['percentage']:.1f}% ({g['grade']}/{g['max_points']})"
        )
    recent_text = "\n".join(recent_lines) if recent_lines else "No graded assignments yet."

    # Build course summary text
    course_lines = []
    for ca in summary["course_averages"]:
        course_lines.append(
            f"- {ca['course_name']}: avg {ca['average_percentage']:.1f}%, "
            f"{ca['graded_count']}/{ca['total_count']} assignments graded"
        )
    course_text = "\n".join(course_lines) if course_lines else "No course data."

    focus_text = f"\nFocus area requested: {focus_area}" if focus_area else ""

    prompt = f"""Analyze the following student's academic performance and provide actionable insights:

Student: {student_name}
Overall Average: {summary['overall_average']:.1f}%
Overall Trend: {summary['trend']}
Completion Rate: {summary['completion_rate']:.1f}%
Total Graded: {summary['total_graded']} of {summary['total_assignments']} assignments
{focus_text}

Courses:
{course_text}

Recent Grades (most recent first):
{recent_text}

Provide:
1. Performance summary (2-3 sentences)
2. Strengths (courses/areas doing well)
3. Areas for improvement
4. Specific actionable recommendations (3-5 items)

Format as Markdown with headers. Be encouraging but honest. Keep it concise."""

    system_prompt = (
        "You are an educational analytics assistant for parents and students. "
        "Provide clear, actionable insights about academic performance. "
        "Be encouraging and constructive."
    )

    return await generate_content(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=1500,
        temperature=0.5,
    )

"""Analytics aggregation service.

Computes performance summaries, subject-level insights, grade trends,
and strengths/weaknesses from GradeRecord data.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.analytics import GradeRecord
from app.models.course import Course

logger = logging.getLogger(__name__)


def get_performance_summary(db: Session, student_id: int) -> dict:
    """Overall performance summary for a student.

    Returns:
        {
            "overall_average": float,
            "total_grades": int,
            "total_courses": int,
            "completion_rate": float,  # % of assignments graded
            "recent_trend": "improving" | "declining" | "stable",
        }
    """
    grades = (
        db.query(GradeRecord)
        .filter(GradeRecord.student_id == student_id)
        .all()
    )

    if not grades:
        return {
            "overall_average": 0.0,
            "total_grades": 0,
            "total_courses": 0,
            "completion_rate": 0.0,
            "recent_trend": "stable",
        }

    percentages = [g.percentage for g in grades]
    course_ids = {g.course_id for g in grades}

    # Recent trend: compare last 30 days vs previous 30 days
    now = datetime.utcnow()
    recent_grades = [g for g in grades if g.recorded_at and g.recorded_at >= now - timedelta(days=30)]
    older_grades = [
        g for g in grades
        if g.recorded_at and now - timedelta(days=60) <= g.recorded_at < now - timedelta(days=30)
    ]

    trend = calculate_trend(
        [g.percentage for g in older_grades],
        [g.percentage for g in recent_grades],
    )

    return {
        "overall_average": round(sum(percentages) / len(percentages), 2),
        "total_grades": len(grades),
        "total_courses": len(course_ids),
        "completion_rate": 100.0,  # all GradeRecords are graded by definition
        "recent_trend": trend,
    }


def get_subject_insights(db: Session, student_id: int) -> list[dict]:
    """Per-course performance breakdown.

    Returns a list of:
        {
            "course_id": int,
            "course_name": str,
            "subject": str | None,
            "average_grade": float,
            "grade_count": int,
            "last_grade": float,
            "trend": "improving" | "declining" | "stable",
        }
    """
    # Aggregate by course
    rows = (
        db.query(
            GradeRecord.course_id,
            sa_func.avg(GradeRecord.percentage).label("avg_pct"),
            sa_func.count(GradeRecord.id).label("cnt"),
        )
        .filter(GradeRecord.student_id == student_id)
        .group_by(GradeRecord.course_id)
        .all()
    )

    if not rows:
        return []

    course_ids = [r.course_id for r in rows]
    courses = {c.id: c for c in db.query(Course).filter(Course.id.in_(course_ids)).all()}

    now = datetime.utcnow()
    insights = []

    for row in rows:
        course = courses.get(row.course_id)

        # Per-course grades for trend + last_grade
        course_grades = (
            db.query(GradeRecord)
            .filter(
                GradeRecord.student_id == student_id,
                GradeRecord.course_id == row.course_id,
            )
            .order_by(GradeRecord.recorded_at.asc())
            .all()
        )

        last_grade = course_grades[-1].percentage if course_grades else 0.0

        recent = [g for g in course_grades if g.recorded_at and g.recorded_at >= now - timedelta(days=30)]
        older = [
            g for g in course_grades
            if g.recorded_at and now - timedelta(days=60) <= g.recorded_at < now - timedelta(days=30)
        ]

        insights.append({
            "course_id": row.course_id,
            "course_name": course.name if course else "Unknown",
            "subject": course.subject if course else None,
            "average_grade": round(float(row.avg_pct), 2),
            "grade_count": row.cnt,
            "last_grade": round(last_grade, 2),
            "trend": calculate_trend(
                [g.percentage for g in older],
                [g.percentage for g in recent],
            ),
        })

    # Sort by average descending (best courses first)
    insights.sort(key=lambda x: x["average_grade"], reverse=True)
    return insights


def get_grade_trends(db: Session, student_id: int, days: int = 90) -> list[dict]:
    """Time-series grade data for charting.

    Returns weekly aggregated data points:
        [{"date": "2026-01-06", "average": 85.5, "count": 3}, ...]
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    grades = (
        db.query(GradeRecord)
        .filter(
            GradeRecord.student_id == student_id,
            GradeRecord.recorded_at >= cutoff,
        )
        .order_by(GradeRecord.recorded_at.asc())
        .all()
    )

    if not grades:
        return []

    # Group by ISO week
    weekly: dict[str, list[float]] = {}
    for g in grades:
        if not g.recorded_at:
            continue
        # Monday of the week
        week_start = g.recorded_at - timedelta(days=g.recorded_at.weekday())
        key = week_start.strftime("%Y-%m-%d")
        weekly.setdefault(key, []).append(g.percentage)

    return [
        {
            "date": key,
            "average": round(sum(vals) / len(vals), 2),
            "count": len(vals),
        }
        for key, vals in sorted(weekly.items())
    ]


def get_course_trends(db: Session, student_id: int, course_id: int, days: int = 90) -> list[dict]:
    """Time-series grade data for a single course.

    Returns individual grade points (not aggregated):
        [{"date": "2026-01-10", "percentage": 85.0, "assignment_title": "..."}, ...]
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    grades = (
        db.query(GradeRecord)
        .filter(
            GradeRecord.student_id == student_id,
            GradeRecord.course_id == course_id,
            GradeRecord.recorded_at >= cutoff,
        )
        .order_by(GradeRecord.recorded_at.asc())
        .all()
    )

    return [
        {
            "date": g.recorded_at.strftime("%Y-%m-%d") if g.recorded_at else None,
            "percentage": round(g.percentage, 2),
            "grade": g.grade,
            "max_grade": g.max_grade,
            "assignment_title": g.assignment.title if g.assignment else None,
        }
        for g in grades
    ]


def get_strengths_weaknesses(db: Session, student_id: int) -> dict:
    """Identify top-performing and struggling courses.

    Returns:
        {
            "strengths": [{"course_name": str, "average_grade": float, "description": str}],
            "weaknesses": [{"course_name": str, "average_grade": float, "description": str}],
        }
    """
    insights = get_subject_insights(db, student_id)

    if not insights:
        return {"strengths": [], "weaknesses": []}

    overall_avg = sum(i["average_grade"] for i in insights) / len(insights)

    strengths = []
    weaknesses = []

    for ins in insights:
        avg = ins["average_grade"]
        name = ins["course_name"]
        trend = ins["trend"]

        if avg >= overall_avg + 5:
            desc = f"Performing well in {name} with {avg:.0f}% average"
            if trend == "improving":
                desc += " and still improving"
            strengths.append({
                "course_id": ins["course_id"],
                "course_name": name,
                "average_grade": avg,
                "trend": trend,
                "description": desc,
            })
        elif avg <= overall_avg - 5:
            desc = f"Struggling in {name} with {avg:.0f}% average"
            if trend == "declining":
                desc += " and trending downward"
            elif trend == "improving":
                desc += " but showing improvement"
            weaknesses.append({
                "course_id": ins["course_id"],
                "course_name": name,
                "average_grade": avg,
                "trend": trend,
                "description": desc,
            })

    return {"strengths": strengths, "weaknesses": weaknesses}


def calculate_trend(older: list[float], recent: list[float]) -> str:
    """Determine trend by comparing two sets of percentages.

    Returns "improving", "declining", or "stable".
    Uses a 3-point threshold to avoid noise.
    """
    if not older or not recent:
        return "stable"

    old_avg = sum(older) / len(older)
    new_avg = sum(recent) / len(recent)
    diff = new_avg - old_avg

    if diff >= 3:
        return "improving"
    elif diff <= -3:
        return "declining"
    return "stable"

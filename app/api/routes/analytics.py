from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.analytics import GradeRecord
from app.models.assignment import Assignment
from app.models.course import Course, student_courses
from app.models.student import Student, parent_students
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.analytics import (
    GradeRecordResponse,
    GradeListResponse,
    GradeSyncResponse,
    AnalyticsDashboardResponse,
    SubjectInsight,
    GradeTrendPoint,
    CourseTrendPoint,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_student_or_403(db: Session, student_id: int, current_user: User) -> Student:
    """Load a student and verify the current user has access."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if current_user.has_role(UserRole.ADMIN):
        return student

    # Student viewing own data
    if current_user.has_role(UserRole.STUDENT) and student.user_id == current_user.id:
        return student

    # Parent viewing linked child
    if current_user.has_role(UserRole.PARENT):
        link = db.query(parent_students).filter(
            parent_students.c.parent_id == current_user.id,
            parent_students.c.student_id == student.id,
        ).first()
        if link:
            return student

    # Teacher viewing student in their course
    if current_user.has_role(UserRole.TEACHER):
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            in_course = (
                db.query(student_courses.c.student_id)
                .join(Course, Course.id == student_courses.c.course_id)
                .filter(
                    student_courses.c.student_id == student.id,
                    Course.teacher_id == teacher.id,
                )
                .first()
            )
            if in_course:
                return student

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this student's grades")


def _resolve_student_id(db: Session, student_id: int | None, current_user: User) -> int:
    """Resolve the student_id — students default to themselves."""
    if student_id:
        return student_id

    if current_user.has_role(UserRole.STUDENT):
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            return student.id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="student_id is required",
    )


def _grade_to_response(gr: GradeRecord) -> dict:
    """Convert GradeRecord to response dict with joined names."""
    return {
        "id": gr.id,
        "student_id": gr.student_id,
        "course_id": gr.course_id,
        "course_name": gr.course.name if gr.course else None,
        "assignment_id": gr.assignment_id,
        "assignment_title": gr.assignment.title if gr.assignment else None,
        "grade": gr.grade,
        "max_grade": gr.max_grade,
        "percentage": gr.percentage,
        "source": gr.source,
        "recorded_at": gr.recorded_at,
        "created_at": gr.created_at,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/grades", response_model=GradeListResponse)
def list_grades(
    student_id: int | None = None,
    course_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List grade records for a student, optionally filtered by course."""
    sid = _resolve_student_id(db, student_id, current_user)
    _get_student_or_403(db, sid, current_user)

    query = db.query(GradeRecord).filter(GradeRecord.student_id == sid)

    if course_id:
        query = query.filter(GradeRecord.course_id == course_id)

    total = query.count()
    grades = (
        query
        .order_by(GradeRecord.recorded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "grades": [_grade_to_response(g) for g in grades],
        "total": total,
    }


@router.post("/sync-grades", response_model=GradeSyncResponse)
def sync_grades(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a manual grade sync from Google Classroom.

    Parents sync their children's grades using their own Google tokens.
    Students sync their own grades.
    """
    from app.services.grade_sync_service import sync_grades_for_student

    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Classroom not connected. Please connect your Google account first.",
        )

    sid = _resolve_student_id(db, student_id, current_user)
    student = _get_student_or_403(db, sid, current_user)

    result = sync_grades_for_student(current_user, student, db)

    synced = result["synced"]
    errors = result["errors"]
    if errors:
        message = f"Synced {synced} grade(s) with {errors} error(s)"
    else:
        message = f"Synced {synced} grade(s) from Google Classroom"

    return {"synced": synced, "errors": errors, "message": message}


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def get_dashboard(
    student_id: int | None = None,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full analytics dashboard payload for a student."""
    from app.services.analytics_service import (
        get_performance_summary,
        get_subject_insights,
        get_grade_trends,
        get_strengths_weaknesses,
    )

    sid = _resolve_student_id(db, student_id, current_user)
    _get_student_or_403(db, sid, current_user)

    return {
        "summary": get_performance_summary(db, sid),
        "subjects": get_subject_insights(db, sid),
        "trends": get_grade_trends(db, sid, days),
        "strengths_weaknesses": get_strengths_weaknesses(db, sid),
    }


@router.get("/subject/{course_id}", response_model=SubjectInsight)
def get_subject_detail(
    course_id: int,
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed analytics for a specific course."""
    from app.services.analytics_service import get_subject_insights

    sid = _resolve_student_id(db, student_id, current_user)
    _get_student_or_403(db, sid, current_user)

    insights = get_subject_insights(db, sid)
    for ins in insights:
        if ins["course_id"] == course_id:
            return ins

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No grade data found for this course",
    )


@router.get("/trends", response_model=list[GradeTrendPoint])
def get_trends(
    student_id: int | None = None,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grade trend time-series (weekly aggregated)."""
    from app.services.analytics_service import get_grade_trends

    sid = _resolve_student_id(db, student_id, current_user)
    _get_student_or_403(db, sid, current_user)

    return get_grade_trends(db, sid, days)


@router.get("/trends/{course_id}", response_model=list[CourseTrendPoint])
def get_course_trends(
    course_id: int,
    student_id: int | None = None,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grade trend time-series for a specific course (individual data points)."""
    from app.services.analytics_service import get_course_trends as _get_course_trends

    sid = _resolve_student_id(db, student_id, current_user)
    _get_student_or_403(db, sid, current_user)

    return _get_course_trends(db, sid, course_id, days)

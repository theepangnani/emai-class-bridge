from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.assignment import Assignment
from app.models.course import Course, student_courses
from app.models.student import Student, parent_students
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.assignment import AssignmentCreate, AssignmentResponse
from app.api.deps import get_current_user, can_access_course

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _get_accessible_course_ids(db: Session, user: User) -> list[int] | None:
    """Return course IDs accessible to the user, or None for admin (all access)."""
    if user.role == UserRole.ADMIN:
        return None  # Admin can see all

    ids: set[int] = set()

    # Courses created by the user
    created = db.query(Course.id).filter(Course.created_by_user_id == user.id).all()
    ids.update(r[0] for r in created)

    # Public courses
    public = db.query(Course.id).filter(Course.is_private == False).all()  # noqa: E712
    ids.update(r[0] for r in public)

    if user.role == UserRole.TEACHER:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        if teacher:
            taught = db.query(Course.id).filter(Course.teacher_id == teacher.id).all()
            ids.update(r[0] for r in taught)

    elif user.role == UserRole.STUDENT:
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            ids.update(c.id for c in student.courses)

    elif user.role == UserRole.PARENT:
        child_sids = [
            r[0] for r in db.query(parent_students.c.student_id).filter(
                parent_students.c.parent_id == user.id
            ).all()
        ]
        if child_sids:
            enrolled = db.query(student_courses.c.course_id).filter(
                student_courses.c.student_id.in_(child_sids)
            ).all()
            ids.update(r[0] for r in enrolled)

    return list(ids)


@router.post("/", response_model=AssignmentResponse)
def create_assignment(
    assignment_data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an assignment. Must have write access to the course."""
    if not can_access_course(db, current_user, assignment_data.course_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this course")

    # Only teacher of the course, course creator, or admin can create assignments
    if not current_user.has_role(UserRole.ADMIN):
        course = db.query(Course).filter(Course.id == assignment_data.course_id).first()
        if course and course.created_by_user_id != current_user.id:
            if current_user.role == UserRole.TEACHER:
                teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
                if not teacher or course.teacher_id != teacher.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only the course teacher or creator can add assignments",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the course teacher or creator can add assignments",
                )

    assignment = Assignment(**assignment_data.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/", response_model=list[AssignmentResponse])
def list_assignments(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assignments scoped to accessible courses."""
    query = db.query(Assignment)

    if course_id:
        if not can_access_course(db, current_user, course_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this course")
        query = query.filter(Assignment.course_id == course_id)
    else:
        accessible = _get_accessible_course_ids(db, current_user)
        if accessible is not None:  # None means admin (all access)
            query = query.filter(Assignment.course_id.in_(accessible))

    return query.all()


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an assignment. Must have access to its course."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if not can_access_course(db, current_user, assignment.course_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this course")

    return assignment

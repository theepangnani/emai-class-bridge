from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.student import Student, parent_students
from app.models.teacher import Teacher
from app.models.course import Course, student_courses
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        google_connected=bool(current_user.google_access_token),
        created_at=current_user.created_at,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a user profile. Access: own profile, admin (all), parent (linked children),
    teacher (students in their courses)."""
    # Own profile — always allowed
    if user_id == current_user.id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    # Admin sees all
    if current_user.role == UserRole.ADMIN:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Parent can see linked children's profiles
    if current_user.role == UserRole.PARENT:
        student = db.query(Student).filter(Student.user_id == user_id).first()
        if student:
            link = db.query(parent_students).filter(
                parent_students.c.parent_id == current_user.id,
                parent_students.c.student_id == student.id,
            ).first()
            if link:
                return user

    # Teacher can see students enrolled in their courses
    if current_user.role == UserRole.TEACHER:
        student = db.query(Student).filter(Student.user_id == user_id).first()
        if student:
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if teacher:
                course_ids = [
                    r[0] for r in db.query(Course.id).filter(Course.teacher_id == teacher.id).all()
                ]
                if course_ids:
                    enrolled = db.query(student_courses).filter(
                        student_courses.c.student_id == student.id,
                        student_courses.c.course_id.in_(course_ids),
                    ).first()
                    if enrolled:
                        return user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

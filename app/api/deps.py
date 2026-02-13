from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: UserRole):
    """Dependency factory that checks the current user has one of the required roles."""
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker


def can_access_course(db: Session, user: User, course_id: int) -> bool:
    """Check if a user has access to a specific course.

    Access is granted when any of the following is true:
      - User is ADMIN
      - User created the course
      - Course is public (not private)
      - User is the assigned teacher
      - User (student) is enrolled
      - User (parent) has a linked child enrolled
    """
    from app.models.course import Course, student_courses
    from app.models.student import Student, parent_students
    from app.models.teacher import Teacher

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if course.created_by_user_id == user.id:
        return True

    if not course.is_private:
        return True

    if user.role == UserRole.TEACHER:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        if teacher and course.teacher_id == teacher.id:
            return True

    if user.role == UserRole.STUDENT:
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            enrolled = db.query(student_courses).filter(
                student_courses.c.student_id == student.id,
                student_courses.c.course_id == course_id,
            ).first()
            if enrolled:
                return True

    if user.role == UserRole.PARENT:
        child_sids = [
            r[0] for r in db.query(parent_students.c.student_id).filter(
                parent_students.c.parent_id == user.id
            ).all()
        ]
        if child_sids:
            enrolled = db.query(student_courses).filter(
                student_courses.c.student_id.in_(child_sids),
                student_courses.c.course_id == course_id,
            ).first()
            if enrolled:
                return True

    return False

"""Task domain service - business logic for task management."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.task import Task
from app.models.student import Student, parent_students
from app.models.teacher import Teacher
from app.models.course import Course, student_courses


class TaskService:
    """Service for task-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def validate_assignment_relationship(
        self, creator: User, assigned_to_user_id: int
    ) -> User:
        """Verify the creator has a valid relationship with the assignee.

        Returns the assignee User object if validation succeeds.
        Raises HTTPException if validation fails.
        """
        assignee = self.db.query(User).filter(User.id == assigned_to_user_id).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Assigned user not found")

        if creator.role == UserRole.PARENT:
            # Parent can assign to linked students
            link = (
                self.db.query(parent_students)
                .join(Student, Student.id == parent_students.c.student_id)
                .filter(
                    parent_students.c.parent_id == creator.id,
                    Student.user_id == assigned_to_user_id,
                )
                .first()
            )
            if not link:
                raise HTTPException(
                    status_code=403,
                    detail="You can only assign tasks to your linked children",
                )

        elif creator.role == UserRole.TEACHER:
            # Teacher can assign to students in their courses
            teacher = (
                self.db.query(Teacher).filter(Teacher.user_id == creator.id).first()
            )
            if not teacher:
                raise HTTPException(status_code=403, detail="Teacher profile not found")
            student = (
                self.db.query(Student)
                .filter(Student.user_id == assigned_to_user_id)
                .first()
            )
            if not student:
                raise HTTPException(
                    status_code=403, detail="Assigned user is not a student"
                )
            # Check student is enrolled in one of teacher's courses
            link = (
                self.db.query(student_courses)
                .join(Course, Course.id == student_courses.c.course_id)
                .filter(
                    Course.teacher_id == teacher.id,
                    student_courses.c.student_id == student.id,
                )
                .first()
            )
            if not link:
                raise HTTPException(
                    status_code=403,
                    detail="Student is not enrolled in any of your courses",
                )

        elif creator.role == UserRole.STUDENT:
            # Student can assign to linked parents
            student = (
                self.db.query(Student).filter(Student.user_id == creator.id).first()
            )
            if not student:
                raise HTTPException(status_code=403, detail="Student profile not found")
            link = (
                self.db.query(parent_students)
                .filter(
                    parent_students.c.student_id == student.id,
                    parent_students.c.parent_id == assigned_to_user_id,
                )
                .first()
            )
            if not link:
                raise HTTPException(
                    status_code=403,
                    detail="You can only assign tasks to your linked parents",
                )

        else:
            # Admin can only create personal tasks
            raise HTTPException(
                status_code=403, detail="You can only create personal tasks"
            )

        return assignee

    def toggle_completion(self, task: Task, user: User, is_completed: bool) -> Task:
        """Toggle task completion and handle auto-archive logic.

        Args:
            task: The task to toggle
            user: The user performing the action
            is_completed: The new completion status

        Returns:
            The updated task
        """
        task.is_completed = is_completed
        task.completed_at = datetime.now(timezone.utc) if is_completed else None
        # Auto-archive on completion, un-archive on un-completion
        task.archived_at = datetime.now(timezone.utc) if is_completed else None
        return task

    def archive_task(self, task: Task, user: User) -> Task:
        """Archive a task (soft delete).

        Args:
            task: The task to archive
            user: The user performing the action (must be creator)

        Returns:
            The archived task

        Raises:
            HTTPException if user is not the creator
        """
        if task.created_by_user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the task creator can archive tasks"
            )

        task.archived_at = datetime.now(timezone.utc)
        return task

    def restore_task(self, task: Task, user: User) -> Task:
        """Restore an archived task.

        Args:
            task: The task to restore
            user: The user performing the action (must be creator)

        Returns:
            The restored task

        Raises:
            HTTPException if user is not the creator or task is not archived
        """
        if task.created_by_user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the task creator can restore tasks"
            )

        if not task.archived_at:
            raise HTTPException(status_code=400, detail="Task is not archived")

        task.archived_at = None
        task.is_completed = False
        task.completed_at = None
        return task

    def get_assignable_users(self, user: User) -> list[dict]:
        """Get users that the current user can assign tasks to.

        Args:
            user: The current user

        Returns:
            List of assignable users with user_id, name, and role
        """
        users = []

        if user.role == UserRole.PARENT:
            # Parent can assign to linked children
            rows = (
                self.db.query(Student, User)
                .join(parent_students, parent_students.c.student_id == Student.id)
                .join(User, User.id == Student.user_id)
                .filter(parent_students.c.parent_id == user.id)
                .all()
            )
            for _, u in rows:
                users.append({"user_id": u.id, "name": u.full_name, "role": u.role.value})

        elif user.role == UserRole.TEACHER:
            teacher = self.db.query(Teacher).filter(Teacher.user_id == user.id).first()
            if teacher:
                rows = (
                    self.db.query(Student, User)
                    .join(student_courses, student_courses.c.student_id == Student.id)
                    .join(Course, Course.id == student_courses.c.course_id)
                    .join(User, User.id == Student.user_id)
                    .filter(Course.teacher_id == teacher.id)
                    .distinct()
                    .all()
                )
                for _, u in rows:
                    users.append({"user_id": u.id, "name": u.full_name, "role": u.role.value})

        elif user.role == UserRole.STUDENT:
            student = self.db.query(Student).filter(Student.user_id == user.id).first()
            if student:
                rows = (
                    self.db.query(User)
                    .join(parent_students, parent_students.c.parent_id == User.id)
                    .filter(parent_students.c.student_id == student.id)
                    .all()
                )
                for u in rows:
                    users.append({"user_id": u.id, "name": u.full_name, "role": u.role.value})

        return users

    def can_view_task(self, task: Task, user: User) -> bool:
        """Check if a user can view a task.

        Args:
            task: The task to check
            user: The user requesting access

        Returns:
            True if user can view the task, False otherwise
        """
        # Creator and assignee always have access
        if task.created_by_user_id == user.id or task.assigned_to_user_id == user.id:
            return True

        # Parents can view tasks assigned to their children
        if user.role == UserRole.PARENT:
            child_user_ids = [
                r[0] for r in self.db.query(Student.user_id)
                .join(parent_students, parent_students.c.student_id == Student.id)
                .filter(parent_students.c.parent_id == user.id)
                .all()
            ]
            if task.assigned_to_user_id in child_user_ids or task.created_by_user_id in child_user_ids:
                return True

        return False

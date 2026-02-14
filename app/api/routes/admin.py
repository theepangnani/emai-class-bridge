import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.utils import escape_like

from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.audit_log import AuditLog
from app.api.deps import require_role
from app.schemas.admin import AdminUserList, AdminStats
from app.schemas.audit import AuditLogResponse, AuditLogList
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=AdminUserList)
def list_users(
    role: UserRole | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all users with optional role filter and search."""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    if search:
        search_term = f"%{escape_like(search)}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return AdminUserList(users=users, total=total)


@router.get("/stats", response_model=AdminStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get platform statistics."""
    total_users = db.query(User).count()

    # Count users who hold each role (checking multi-role 'roles' column)
    users_by_role: dict[str, int] = {}
    for r in UserRole:
        count = db.query(User).filter(
            or_(
                User.roles.contains(r.value),
                # Fallback for users with no roles column set
                (User.role == r) & (User.roles.is_(None) | (User.roles == "")),
            )
        ).count()
        if count:
            users_by_role[r.value] = count

    total_courses = db.query(Course).count()
    total_assignments = db.query(Assignment).count()

    return AdminStats(
        total_users=total_users,
        users_by_role=users_by_role,
        total_courses=total_courses,
        total_assignments=total_assignments,
    )


@router.get("/audit-logs", response_model=AuditLogList)
def list_audit_logs(
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List audit logs with filters. Admin only."""
    query = db.query(AuditLog)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)
    if search:
        search_term = f"%{escape_like(search)}%"
        query = query.filter(AuditLog.details.ilike(search_term))

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    # Resolve user names in bulk
    user_ids = {log.user_id for log in logs if log.user_id}
    user_map = {}
    if user_ids:
        users = db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.full_name for u in users}

    items = [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_name=user_map.get(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogList(items=items, total=total)


class AddRoleRequest(BaseModel):
    role: str


@router.post("/users/{user_id}/add-role", response_model=UserResponse)
def add_role_to_user(
    user_id: int,
    data: AddRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Add a role to a user. Also creates the Teacher/Student profile record if needed."""
    try:
        new_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {data.role}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.has_role(new_role):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User already has the '{data.role}' role")

    # Update roles column
    current_roles = user.get_roles_list()
    current_roles.append(new_role)
    user.set_roles(current_roles)

    # Create profile record if needed
    if new_role == UserRole.TEACHER:
        existing = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        if not existing:
            db.add(Teacher(user_id=user.id))
    elif new_role == UserRole.STUDENT:
        existing = db.query(Student).filter(Student.user_id == user.id).first()
        if not existing:
            db.add(Student(user_id=user.id))

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/remove-role", response_model=UserResponse)
def remove_role_from_user(
    user_id: int,
    data: AddRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Remove a role from a user. Cannot remove their last role."""
    try:
        target_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {data.role}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.has_role(target_role):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User does not have the '{data.role}' role")

    current_roles = user.get_roles_list()
    if len(current_roles) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the user's only role")

    current_roles = [r for r in current_roles if r != target_role]
    user.set_roles(current_roles)

    # If active role was removed, switch to first remaining role
    if user.role == target_role:
        user.role = current_roles[0]

    db.commit()
    db.refresh(user)
    return user

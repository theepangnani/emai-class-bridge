"""
Example: API v1 Structure for Mobile Apps

This shows how to restructure your backend with API versioning.
"""

# ==========================================
# 1. NEW: app/schemas/pagination.py
# ==========================================
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination response for mobile apps"""
    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    @staticmethod
    def create(items: List[T], total: int, skip: int, limit: int):
        return PaginatedResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total
        )

    class Config:
        from_attributes = True


# ==========================================
# 2. NEW: app/schemas/error.py
# ==========================================
from pydantic import BaseModel
from typing import Optional

class ErrorDetail(BaseModel):
    """Structured error response for mobile apps"""
    code: str          # "AUTH_INVALID_TOKEN", "VALIDATION_ERROR", etc.
    message: str       # Human-readable message
    field: Optional[str] = None  # For validation errors

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str    # For debugging in logs


# ==========================================
# 3. NEW: app/models/device_token.py
# ==========================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True, index=True)  # FCM token
    platform = Column(String(10), nullable=False)  # "ios" or "android"
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==========================================
# 4. NEW: app/schemas/device.py
# ==========================================
from pydantic import BaseModel, Field
from datetime import datetime

class DeviceTokenCreate(BaseModel):
    token: str = Field(..., min_length=50, max_length=500)
    platform: str = Field(..., pattern="^(ios|android)$")

class DeviceTokenResponse(BaseModel):
    id: int
    user_id: int
    platform: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# 5. NEW: app/api/v1/routes/devices.py
# ==========================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.device_token import DeviceToken
from app.schemas.device import DeviceTokenCreate, DeviceTokenResponse

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=DeviceTokenResponse)
def register_device(
    device_data: DeviceTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register a device token for push notifications.

    Mobile app calls this after getting FCM token from Firebase.
    """
    # Check if token already exists
    existing = db.query(DeviceToken).filter(
        DeviceToken.token == device_data.token
    ).first()

    if existing:
        # Reactivate if inactive, update user_id if changed
        existing.is_active = True
        existing.user_id = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    # Create new device token
    device = DeviceToken(
        user_id=current_user.id,
        token=device_data.token,
        platform=device_data.platform
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.delete("/unregister")
def unregister_device(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unregister a device token (e.g., on logout).
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.token == token,
        DeviceToken.user_id == current_user.id
    ).first()

    if device:
        device.is_active = False
        db.commit()

    return {"message": "Device unregistered successfully"}


@router.get("/my-devices", response_model=list[DeviceTokenResponse])
def list_my_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all registered devices for current user."""
    devices = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.id,
        DeviceToken.is_active == True
    ).all()
    return devices


# ==========================================
# 6. NEW: app/services/push_notification_service.py
# ==========================================
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.device_token import DeviceToken
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    # Initialize Firebase (do this once in main.py or core/firebase.py)
    # cred = credentials.Certificate("path/to/serviceAccountKey.json")
    # firebase_admin.initialize_app(cred)
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK not installed. Push notifications disabled.")


def send_push_notification(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict] = None
) -> int:
    """
    Send push notification to all devices for a user.

    Args:
        db: Database session
        user_id: User to send notification to
        title: Notification title
        body: Notification body
        data: Optional data payload (e.g., {"type": "assignment", "id": "123"})

    Returns:
        Number of devices notified
    """
    if not FIREBASE_AVAILABLE:
        logger.warning("Push notifications not available (Firebase not configured)")
        return 0

    # Get all active device tokens for user
    devices = db.query(DeviceToken).filter(
        DeviceToken.user_id == user_id,
        DeviceToken.is_active == True
    ).all()

    if not devices:
        logger.info(f"No devices registered for user {user_id}")
        return 0

    tokens = [device.token for device in devices]

    # Create notification
    notification = messaging.Notification(
        title=title,
        body=body
    )

    # Create message
    message = messaging.MulticastMessage(
        notification=notification,
        data=data or {},
        tokens=tokens
    )

    try:
        # Send to all devices
        response = messaging.send_multicast(message)

        # Log results
        logger.info(f"Push notification sent to {response.success_count}/{len(tokens)} devices for user {user_id}")

        # Handle failed tokens (deactivate invalid tokens)
        if response.failure_count > 0:
            failed_tokens = [
                tokens[idx] for idx, resp in enumerate(response.responses)
                if not resp.success
            ]
            db.query(DeviceToken).filter(
                DeviceToken.token.in_(failed_tokens)
            ).update({"is_active": False}, synchronize_session=False)
            db.commit()

        return response.success_count

    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return 0


def send_bulk_push_notification(
    db: Session,
    user_ids: List[int],
    title: str,
    body: str,
    data: Optional[Dict] = None
) -> int:
    """Send push notification to multiple users."""
    total_sent = 0
    for user_id in user_ids:
        total_sent += send_push_notification(db, user_id, title, body, data)
    return total_sent


# ==========================================
# 7. EXAMPLE: Updated courses endpoint with pagination
# ==========================================
from fastapi import Query
from app.schemas.pagination import PaginatedResponse
from app.schemas.course import CourseResponse

@router.get("/v1/courses", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List courses with pagination (mobile-friendly).

    Query params:
    - skip: Offset (default 0)
    - limit: Page size (default 20, max 100)
    """
    # Get user's courses (based on role)
    from app.models.course import Course
    query = db.query(Course)

    # Apply role-based filters
    if current_user.role == UserRole.STUDENT:
        # Get enrolled courses
        from app.models.student import Student
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.join(Course.students).filter(Student.id == student.id)
    elif current_user.role == UserRole.TEACHER:
        # Get teaching courses
        from app.models.teacher import Teacher
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            query = query.filter(Course.teacher_id == teacher.id)

    total = query.count()
    courses = query.offset(skip).limit(limit).all()

    return PaginatedResponse.create(
        items=[CourseResponse.model_validate(c) for c in courses],
        total=total,
        skip=skip,
        limit=limit
    )


# ==========================================
# 8. EXAMPLE: Trigger push notification when assignment created
# ==========================================
from app.services.push_notification_service import send_push_notification

@router.post("/v1/assignments", response_model=AssignmentResponse)
def create_assignment(
    assignment_data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """Create a new assignment and notify students."""
    # Create assignment (existing logic)
    assignment = Assignment(**assignment_data.dict())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # NEW: Send push notifications to enrolled students
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if course and course.students:
        for student in course.students:
            if student.user_id:
                send_push_notification(
                    db=db,
                    user_id=student.user_id,
                    title="📚 New Assignment",
                    body=f"New assignment in {course.name}: {assignment.title}",
                    data={
                        "type": "assignment",
                        "assignment_id": str(assignment.id),
                        "course_id": str(course.id),
                        "deep_link": f"classbridge://assignment/{assignment.id}"
                    }
                )

    return assignment


# ==========================================
# 9. EXAMPLE: File upload endpoint
# ==========================================
from fastapi import UploadFile, File
from app.services.file_storage_service import upload_file_to_cloud

@router.post("/v1/uploads/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload profile picture (mobile-friendly).

    Accepts: JPEG, PNG, HEIC (iOS)
    Max size: 5MB
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/heic"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_FILE_TYPE", "message": "Only JPEG, PNG, and HEIC images allowed"}
        )

    # Validate file size (5MB)
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset
    if size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"code": "FILE_TOO_LARGE", "message": "File must be under 5MB"}
        )

    # Upload to cloud storage (implement this in file_storage_service.py)
    url = await upload_file_to_cloud(
        file=file,
        bucket="classbridge-profile-pictures",
        path=f"users/{current_user.id}/profile.jpg"
    )

    # Update user profile
    current_user.profile_picture_url = url
    db.commit()

    return {
        "url": url,
        "message": "Profile picture uploaded successfully"
    }


# ==========================================
# 10. EXAMPLE: Health check with versioning info
# ==========================================
@router.get("/v1/health")
def health_check():
    """
    Health check endpoint for mobile apps.

    Returns API version info for force-update logic.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "min_supported_version": "1.0.0",  # Mobile app must be >= this version
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "push_notifications": FIREBASE_AVAILABLE,
            "file_uploads": True,
            "offline_sync": False  # Coming soon
        }
    }

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.course_content import CourseContent
from app.models.course import Course
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.course_content import CourseContentCreate, CourseContentUpdate, CourseContentResponse

router = APIRouter(prefix="/course-contents", tags=["Course Contents"])


@router.post("/", response_model=CourseContentResponse, status_code=status.HTTP_201_CREATED)
def create_course_content(
    data: CourseContentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new content item for a course."""
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    content = CourseContent(
        course_id=data.course_id,
        title=data.title,
        description=data.description,
        text_content=data.text_content,
        content_type=data.content_type,
        reference_url=data.reference_url,
        google_classroom_url=data.google_classroom_url,
        created_by_user_id=current_user.id,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


@router.get("/", response_model=list[CourseContentResponse])
def list_course_contents(
    course_id: int = Query(..., description="Filter by course ID"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List content items for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    query = db.query(CourseContent).filter(CourseContent.course_id == course_id)
    if content_type:
        query = query.filter(CourseContent.content_type == content_type.strip().lower())
    return query.order_by(CourseContent.created_at.desc()).all()


@router.get("/{content_id}", response_model=CourseContentResponse)
def get_course_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single content item."""
    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return content


@router.patch("/{content_id}", response_model=CourseContentResponse)
def update_course_content(
    content_id: int,
    data: CourseContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a content item. Only the creator can update."""
    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if content.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can edit content")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(content, field, value)

    db.commit()
    db.refresh(content)
    return content


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a content item. Only the creator can delete."""
    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if content.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can delete content")

    db.delete(content)
    db.commit()

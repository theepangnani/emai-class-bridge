from pydantic import BaseModel
from datetime import datetime


class CourseCreate(BaseModel):
    name: str
    description: str | None = None
    subject: str | None = None
    teacher_id: int | None = None


class CourseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    subject: str | None
    google_classroom_id: str | None
    teacher_id: int | None
    created_by_user_id: int | None = None
    is_private: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

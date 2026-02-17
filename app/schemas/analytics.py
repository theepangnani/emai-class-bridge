from pydantic import BaseModel
from datetime import datetime


class GradeRecordResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    course_name: str | None = None
    assignment_id: int | None
    assignment_title: str | None = None
    grade: float
    max_grade: float
    percentage: float
    source: str
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class GradeListResponse(BaseModel):
    grades: list[GradeRecordResponse]
    total: int


class GradeSyncResponse(BaseModel):
    synced: int
    errors: int
    message: str


# ---------------------------------------------------------------------------
# Analytics dashboard schemas (#470)
# ---------------------------------------------------------------------------

class PerformanceSummary(BaseModel):
    overall_average: float
    total_grades: int
    total_courses: int
    completion_rate: float
    recent_trend: str  # "improving", "declining", "stable"


class SubjectInsight(BaseModel):
    course_id: int
    course_name: str
    subject: str | None = None
    average_grade: float
    grade_count: int
    last_grade: float
    trend: str


class GradeTrendPoint(BaseModel):
    date: str
    average: float
    count: int


class CourseTrendPoint(BaseModel):
    date: str | None
    percentage: float
    grade: float
    max_grade: float
    assignment_title: str | None = None


class StrengthWeaknessItem(BaseModel):
    course_id: int
    course_name: str
    average_grade: float
    trend: str
    description: str


class StrengthsWeaknesses(BaseModel):
    strengths: list[StrengthWeaknessItem]
    weaknesses: list[StrengthWeaknessItem]


class AnalyticsDashboardResponse(BaseModel):
    summary: PerformanceSummary
    subjects: list[SubjectInsight]
    trends: list[GradeTrendPoint]
    strengths_weaknesses: StrengthsWeaknesses

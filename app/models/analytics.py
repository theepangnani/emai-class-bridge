from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ProgressReport(Base):
    """Cached weekly/monthly progress report for a student.

    Stores pre-computed analytics as JSON to avoid repeated
    expensive aggregation queries.  Generated on-demand or
    via scheduled job.
    """

    __tablename__ = "progress_reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False)  # "weekly", "monthly"
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    data = Column(Text, nullable=False)  # JSON string (Text for SQLite compat)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")

    __table_args__ = (
        Index("ix_progress_reports_student_period", "student_id", "period_start"),
        Index("ix_progress_reports_type", "report_type"),
    )

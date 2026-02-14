"""Study guide domain service - business logic for study materials."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.study_guide import StudyGuide
from app.models.user import User
from app.core.utils import escape_like


class StudyService:
    """Service for study guide-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def compute_content_hash(
        self, title: str, guide_type: str, assignment_id: int | None = None
    ) -> str:
        """Compute a hash for duplicate detection based on title + guide_type + assignment_id.

        Args:
            title: The title of the study guide
            guide_type: The type of guide (study_guide, quiz, flashcards)
            assignment_id: Optional assignment ID

        Returns:
            SHA256 hash string
        """
        key = f"{title.strip().lower()}|{guide_type}|{assignment_id or ''}"
        return hashlib.sha256(key.encode()).hexdigest()

    def find_recent_duplicate(
        self, user_id: int, content_hash: str, seconds: int = 60
    ) -> StudyGuide | None:
        """Return an existing study guide if one with the same hash was created recently.

        Args:
            user_id: The user ID to check
            content_hash: The content hash to match
            seconds: Time window in seconds (default 60)

        Returns:
            StudyGuide if duplicate found, None otherwise
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return (
            self.db.query(StudyGuide)
            .filter(
                StudyGuide.user_id == user_id,
                StudyGuide.content_hash == content_hash,
                StudyGuide.created_at >= cutoff,
            )
            .order_by(StudyGuide.created_at.desc())
            .first()
        )

    def get_version_info(self, regenerate_from_id: int, user_id: int) -> tuple[int, int]:
        """Get version info for regeneration.

        Args:
            regenerate_from_id: The ID of the guide being regenerated from
            user_id: The user ID (for validation)

        Returns:
            Tuple of (root_guide_id, next_version)

        Raises:
            HTTPException if original guide not found
        """
        from sqlalchemy import func as sa_func

        original = self.db.query(StudyGuide).filter(
            StudyGuide.id == regenerate_from_id,
            StudyGuide.user_id == user_id,
        ).first()
        if not original:
            raise HTTPException(status_code=404, detail="Original study guide not found")

        # Find the root guide (version 1)
        root_id = original.parent_guide_id if original.parent_guide_id else original.id

        # Find max version in the chain
        max_version = (
            self.db.query(sa_func.max(StudyGuide.version))
            .filter(
                or_(
                    StudyGuide.id == root_id,
                    StudyGuide.parent_guide_id == root_id,
                )
            )
            .scalar()
        ) or 1

        return root_id, max_version + 1

    def check_duplicate(
        self, title: str, guide_type: str, user_id: int, assignment_id: int | None = None
    ) -> dict:
        """Check if a similar study guide already exists before generating.

        Args:
            title: The title to check
            guide_type: The type of guide
            user_id: The user ID
            assignment_id: Optional assignment ID

        Returns:
            Dict with 'exists' (bool), optional 'existing_guide', and optional 'message'
        """
        # Check by assignment_id + guide_type (most specific)
        if assignment_id:
            existing = (
                self.db.query(StudyGuide)
                .filter(
                    StudyGuide.user_id == user_id,
                    StudyGuide.assignment_id == assignment_id,
                    StudyGuide.guide_type == guide_type,
                )
                .order_by(StudyGuide.version.desc())
                .first()
            )
            if existing:
                return {
                    "exists": True,
                    "existing_guide": existing,
                    "message": f"A {guide_type.replace('_', ' ')} already exists for this assignment (v{existing.version})",
                }

        # Check by title + guide_type (fallback)
        if title:
            existing = (
                self.db.query(StudyGuide)
                .filter(
                    StudyGuide.user_id == user_id,
                    StudyGuide.title.ilike(f"%{escape_like(title.strip())}%"),
                    StudyGuide.guide_type == guide_type,
                )
                .order_by(StudyGuide.version.desc())
                .first()
            )
            if existing:
                return {
                    "exists": True,
                    "existing_guide": existing,
                    "message": f'A similar {guide_type.replace("_", " ")} already exists: "{existing.title}" (v{existing.version})',
                }

        return {"exists": False}

    def validate_generation_limits(self, user: User) -> None:
        """Check if user has exceeded generation limits.

        This is a placeholder for future rate limiting logic.
        Currently no limits are enforced beyond the route-level rate limiting.

        Args:
            user: The user to check

        Raises:
            HTTPException if limits exceeded
        """
        # Future: implement per-user daily/monthly generation limits
        pass

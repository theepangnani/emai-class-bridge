import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.study_guide import StudyGuide
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User
from app.schemas.study import (
    StudyGuideCreate,
    StudyGuideResponse,
    QuizGenerateRequest,
    QuizResponse,
    QuizQuestion,
    FlashcardGenerateRequest,
    FlashcardSetResponse,
    Flashcard,
)
from app.api.deps import get_current_user
from app.services.ai_service import generate_study_guide, generate_quiz, generate_flashcards

router = APIRouter(prefix="/study", tags=["Study Tools"])


@router.post("/generate", response_model=StudyGuideResponse)
async def generate_study_guide_endpoint(
    request: StudyGuideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a study guide from an assignment or custom content."""
    # Get source content
    assignment = None
    course = None
    title = request.title or "Study Guide"
    description = request.content or ""

    if request.assignment_id:
        assignment = db.query(Assignment).filter(Assignment.id == request.assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        title = f"Study Guide: {assignment.title}"
        description = assignment.description or ""
        course = assignment.course

    if request.course_id and not course:
        course = db.query(Course).filter(Course.id == request.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

    course_name = course.name if course else "General"
    due_date = str(assignment.due_date) if assignment and assignment.due_date else None

    if not description:
        raise HTTPException(
            status_code=400,
            detail="Please provide assignment_id or content to generate a study guide",
        )

    # Generate study guide using AI
    try:
        content = await generate_study_guide(
            assignment_title=title,
            assignment_description=description,
            course_name=course_name,
            due_date=due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save to database
    study_guide = StudyGuide(
        user_id=current_user.id,
        assignment_id=request.assignment_id,
        course_id=request.course_id or (course.id if course else None),
        title=title,
        content=content,
        guide_type="study_guide",
    )
    db.add(study_guide)
    db.commit()
    db.refresh(study_guide)

    return study_guide


@router.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    request: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a practice quiz from an assignment or custom content."""
    topic = request.topic or "Quiz"
    content = request.content or ""

    if request.assignment_id:
        assignment = db.query(Assignment).filter(Assignment.id == request.assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        topic = assignment.title
        content = assignment.description or ""

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Please provide assignment_id or content to generate a quiz",
        )

    # Generate quiz using AI
    try:
        quiz_json = await generate_quiz(
            topic=topic,
            content=content,
            num_questions=request.num_questions,
        )
        # Parse JSON response
        questions_data = json.loads(quiz_json)
        questions = [QuizQuestion(**q) for q in questions_data]
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse quiz response")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save to database
    study_guide = StudyGuide(
        user_id=current_user.id,
        assignment_id=request.assignment_id,
        course_id=request.course_id,
        title=f"Quiz: {topic}",
        content=quiz_json,
        guide_type="quiz",
    )
    db.add(study_guide)
    db.commit()
    db.refresh(study_guide)

    return QuizResponse(
        id=study_guide.id,
        title=study_guide.title,
        questions=questions,
        guide_type="quiz",
        created_at=study_guide.created_at,
    )


@router.post("/flashcards/generate", response_model=FlashcardSetResponse)
async def generate_flashcards_endpoint(
    request: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate flashcards from an assignment or custom content."""
    topic = request.topic or "Flashcards"
    content = request.content or ""

    if request.assignment_id:
        assignment = db.query(Assignment).filter(Assignment.id == request.assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        topic = assignment.title
        content = assignment.description or ""

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Please provide assignment_id or content to generate flashcards",
        )

    # Generate flashcards using AI
    try:
        cards_json = await generate_flashcards(
            topic=topic,
            content=content,
            num_cards=request.num_cards,
        )
        # Parse JSON response
        cards_data = json.loads(cards_json)
        cards = [Flashcard(**c) for c in cards_data]
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse flashcards response")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save to database
    study_guide = StudyGuide(
        user_id=current_user.id,
        assignment_id=request.assignment_id,
        course_id=request.course_id,
        title=f"Flashcards: {topic}",
        content=cards_json,
        guide_type="flashcards",
    )
    db.add(study_guide)
    db.commit()
    db.refresh(study_guide)

    return FlashcardSetResponse(
        id=study_guide.id,
        title=study_guide.title,
        cards=cards,
        guide_type="flashcards",
        created_at=study_guide.created_at,
    )


@router.get("/guides", response_model=list[StudyGuideResponse])
def list_study_guides(
    guide_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all study guides for the current user."""
    query = db.query(StudyGuide).filter(StudyGuide.user_id == current_user.id)
    if guide_type:
        query = query.filter(StudyGuide.guide_type == guide_type)
    return query.order_by(StudyGuide.created_at.desc()).all()


@router.get("/guides/{guide_id}", response_model=StudyGuideResponse)
def get_study_guide(
    guide_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific study guide."""
    guide = db.query(StudyGuide).filter(
        StudyGuide.id == guide_id,
        StudyGuide.user_id == current_user.id,
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Study guide not found")
    return guide


@router.delete("/guides/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study_guide(
    guide_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a study guide."""
    guide = db.query(StudyGuide).filter(
        StudyGuide.id == guide_id,
        StudyGuide.user_id == current_user.id,
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Study guide not found")
    db.delete(guide)
    db.commit()
    return None

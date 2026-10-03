from typing import Any, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.database import get_database
from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.visual_health import (
    MultimodalAssessmentCreate,
    MultimodalAssessmentResponse,
    VisualAnalysisResponse,
    VisualHealthSummary,
    VisualSurveillanceReviewCreate,
    VisualVeterinaryCaseCreate,
)
from app.services.media_service import get_absolute_media_path
from app.services.visual_health_service import (
    ensure_visual_health_indexes,
    escalate_to_surveillance_review,
    escalate_to_veterinary_case,
    generate_multimodal_assessment,
    get_animal_visual_trend,
    get_multimodal_assessment,
    get_visual_analysis,
    get_visual_health_summary,
    list_visual_analyses,
    list_visual_observations,
    process_image_analysis,
    process_video_analysis,
)

router = APIRouter(
    prefix="/visual-health",
    tags=["Visual Health & Multimodal Intelligence"]
)


@router.on_event("startup")
def startup_event():
    ensure_visual_health_indexes()


@router.post("/analyze-image", response_model=VisualAnalysisResponse)
async def analyze_image(
    animal_id: str = Form(..., description="Target Animal ID or Tag ID"),
    file: UploadFile = File(..., description="Livestock image file (.jpg, .png, .webp)"),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Upload and analyze livestock image for visible health indicators.
    Enforces farmer RBAC ownership and image file constraints.
    """
    content = await file.read()
    return process_image_analysis(
        animal_id=animal_id,
        file_bytes=content,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type or "image/jpeg",
        current_user=current_user,
        db=db
    )


@router.post("/analyze-video", response_model=VisualAnalysisResponse)
async def analyze_video(
    animal_id: str = Form(..., description="Target Animal ID or Tag ID"),
    file: UploadFile = File(..., description="Livestock video file (.mp4, .avi, .mov)"),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Upload and analyze livestock video using controlled frame sampling.
    """
    content = await file.read()
    return process_video_analysis(
        animal_id=animal_id,
        file_bytes=content,
        filename=file.filename or "upload.mp4",
        content_type=file.content_type or "video/mp4",
        current_user=current_user,
        db=db
    )


@router.get("/analyses", response_model=list[VisualAnalysisResponse])
def get_analyses(
    animal_id: Optional[str] = Query(None, description="Filter by animal ID"),
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    List historical visual analyses with RBAC filtering.
    """
    return list_visual_analyses(db, current_user, animal_id=animal_id, farm_id=farm_id, limit=limit)


@router.get("/analyses/{analysis_id}", response_model=VisualAnalysisResponse)
def get_analysis_by_id(
    analysis_id: str,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Get detailed visual analysis report by ID.
    """
    analysis = get_visual_analysis(analysis_id, db)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visual analysis '{analysis_id}' not found."
        )
    return analysis


@router.get("/analyses/{analysis_id}/media")
def get_analysis_media(
    analysis_id: str,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Safely stream the stored media for an analysis with path-traversal protection.
    """
    analysis = get_visual_analysis(analysis_id, db)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual analysis not found."
        )

    # Fetch document from DB to retrieve storage_path
    doc = db.visual_analyses.find_one({"analysis_id": analysis["analysis_id"]})
    if not doc or not doc.get("storage_path"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not registered for this analysis."
        )

    abs_path = get_absolute_media_path(doc["storage_path"])
    if not abs_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found on server storage."
        )

    media_type = doc.get("media_type", "image")
    content_type = "image/jpeg" if media_type == "image" else "video/mp4"
    return FileResponse(abs_path, media_type=content_type, filename=doc.get("filename", "media"))


@router.get("/animal/{animal_id}", response_model=list[VisualAnalysisResponse])
def get_animal_analyses(
    animal_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Retrieve visual analyses for a specific animal.
    """
    return list_visual_analyses(db, current_user, animal_id=animal_id, limit=limit)


@router.get("/farm/{farm_id}", response_model=list[VisualAnalysisResponse])
def get_farm_analyses(
    farm_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Retrieve visual analyses for a specific farm holding.
    """
    return list_visual_analyses(db, current_user, farm_id=farm_id, limit=limit)


@router.get("/observations")
def get_observations(
    animal_id: Optional[str] = Query(None),
    farm_id: Optional[str] = Query(None),
    indicator: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Query extracted visual health indicators and observations.
    """
    return list_visual_observations(
        db=db,
        current_user=current_user,
        animal_id=animal_id,
        farm_id=farm_id,
        indicator=indicator,
        limit=limit
    )


@router.get("/trends/{animal_id}")
def get_trends(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Temporal trajectory analysis comparing consecutive visual analyses.
    """
    return get_animal_visual_trend(animal_id, current_user, db)


@router.post("/multimodal-assessment", response_model=MultimodalAssessmentResponse)
def create_multimodal_assessment(
    payload: MultimodalAssessmentCreate,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Generate unified Multimodal Animal Health Assessment combining:
    Visual observations + IoT telemetry + Disease Intelligence + Surveillance + Preventive records.
    """
    return generate_multimodal_assessment(
        animal_id=payload.animal_id,
        visual_analysis_id=payload.visual_analysis_id,
        current_user=current_user,
        db=db
    )


@router.get("/multimodal/{assessment_id}", response_model=MultimodalAssessmentResponse)
def get_multimodal(
    assessment_id: str,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Retrieve a multimodal assessment by assessment ID.
    """
    res = get_multimodal_assessment(assessment_id, db)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Multimodal assessment '{assessment_id}' not found."
        )
    return res


@router.post("/{analysis_id}/veterinary-case")
def create_vet_case_from_visual(
    analysis_id: str,
    payload: VisualVeterinaryCaseCreate,
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Escalate a visual health analysis to an official clinical case.
    """
    return escalate_to_veterinary_case(
        analysis_id=analysis_id,
        notes=payload.notes,
        priority=payload.priority,
        current_user=current_user,
        db=db
    )


@router.post("/{analysis_id}/surveillance-review")
def create_surveillance_from_visual(
    analysis_id: str,
    payload: VisualSurveillanceReviewCreate,
    current_user: dict = Depends(require_vet_or_admin),
    db: Any = Depends(get_database)
):
    """
    Escalate visual findings into the herd disease surveillance system.
    Only authorized veterinarians and administrators can confirm or log surveillance events.
    """
    return escalate_to_surveillance_review(
        analysis_id=analysis_id,
        notes=payload.notes,
        current_user=current_user,
        db=db
    )


@router.get("/summary", response_model=VisualHealthSummary)
def get_summary(
    current_user: dict = Depends(require_any_authenticated_user),
    db: Any = Depends(get_database)
):
    """
    Get summary KPI metrics for Visual Health.
    """
    return get_visual_health_summary(db, current_user)

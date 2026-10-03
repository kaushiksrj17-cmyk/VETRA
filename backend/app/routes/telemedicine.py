"""
backend/app/routes/telemedicine.py
==================================
VETRA Phase 12 — Telemedicine Consultation & Clinical Collaboration REST Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.telemedicine import (
    AddClinicalNoteRequest,
    ClinicalNoteItem,
    TelemedicineCancelRequest,
    TelemedicineCompleteRequest,
    TelemedicineConsultationCreate,
    TelemedicineConsultationResponse,
    TelemedicineConsultationUpdate,
)
from app.services.telemedicine_service import (
    accept_consultation,
    add_clinical_note,
    cancel_consultation,
    complete_consultation,
    create_consultation,
    get_clinical_notes,
    get_consultation,
    list_consultations,
    start_consultation,
)


router = APIRouter(
    prefix="/telemedicine",
    tags=["Veterinary Telemedicine"]
)


@router.post(
    "/consultations",
    response_model=TelemedicineConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request or schedule telemedicine consultation"
)
def create_consultation_endpoint(
    payload: TelemedicineConsultationCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Initiates a telemedicine consultation request.
    Farmers can request triage for their own livestock; veterinarians can schedule directly.
    """
    try:
        return create_consultation(current_user, payload.model_dump())
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create consultation: {str(e)}")


@router.get(
    "/consultations",
    response_model=list[TelemedicineConsultationResponse],
    summary="List consultations with RBAC filtering"
)
def list_consultations_endpoint(
    farm_id: Optional[str] = Query(None, description="Optional farm filter"),
    animal_id: Optional[str] = Query(None, description="Optional animal filter"),
    veterinarian_id: Optional[str] = Query(None, description="Optional veterinarian filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional consultation status filter"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Lists accessible consultations conforming to farmer/veterinarian RBAC rules."""
    return list_consultations(
        user_info=current_user,
        farm_id=farm_id,
        animal_id=animal_id,
        veterinarian_id=veterinarian_id,
        status=status_filter,
        limit=limit,
        skip=skip
    )


@router.get(
    "/consultations/{consultation_id}",
    response_model=TelemedicineConsultationResponse,
    summary="Get consultation details"
)
def get_consultation_endpoint(
    consultation_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Retrieves full consultation details, clinical notes, and evidence references."""
    try:
        cons = get_consultation(consultation_id, current_user)
        if not cons:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consultation '{consultation_id}' was not found."
            )
        return cons
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put(
    "/consultations/{consultation_id}",
    response_model=TelemedicineConsultationResponse,
    summary="Update consultation scheduling or chief complaint"
)
def update_consultation_endpoint(
    consultation_id: str,
    payload: TelemedicineConsultationUpdate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Updates consultation metadata, scheduled timestamp, or summary."""
    cons = get_consultation(consultation_id, current_user)
    if not cons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation '{consultation_id}' was not found."
        )
    from app.database import get_database
    db = get_database()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    db.telemedicine_consultations.update_one(
        {"consultation_id": cons["consultation_id"]},
        {"$set": update_data}
    )
    return get_consultation(consultation_id, current_user)


@router.post(
    "/consultations/{consultation_id}/accept",
    response_model=TelemedicineConsultationResponse,
    summary="Accept and claim a consultation"
)
def accept_consultation_endpoint(
    consultation_id: str,
    current_user: dict = Depends(require_vet_or_admin)
):
    """Clinician accepts an open consultation request and assigns self."""
    try:
        return accept_consultation(consultation_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/consultations/{consultation_id}/start",
    response_model=TelemedicineConsultationResponse,
    summary="Mark consultation as active/in-progress"
)
def start_consultation_endpoint(
    consultation_id: str,
    current_user: dict = Depends(require_vet_or_admin)
):
    """Transitions consultation state to in_progress."""
    try:
        return start_consultation(consultation_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/consultations/{consultation_id}/complete",
    response_model=TelemedicineConsultationResponse,
    summary="Complete consultation with clinical recommendations"
)
def complete_consultation_endpoint(
    consultation_id: str,
    payload: TelemedicineCompleteRequest,
    current_user: dict = Depends(require_vet_or_admin)
):
    """Concludes consultation and documents veterinary recommendations & follow-up."""
    try:
        return complete_consultation(
            consultation_id=consultation_id,
            user_info=current_user,
            recommendations=payload.recommendations,
            final_assessment=payload.final_assessment,
            follow_up_date=payload.follow_up_date,
            follow_up_reason=payload.follow_up_reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/consultations/{consultation_id}/cancel",
    response_model=TelemedicineConsultationResponse,
    summary="Cancel a consultation"
)
def cancel_consultation_endpoint(
    consultation_id: str,
    payload: TelemedicineCancelRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Cancels consultation with documentation of cancellation reason."""
    try:
        return cancel_consultation(consultation_id, current_user, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/consultations/{consultation_id}/notes",
    response_model=ClinicalNoteItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add clinical or observation note"
)
def add_clinical_note_endpoint(
    consultation_id: str,
    payload: AddClinicalNoteRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Appends a clinical note.
    Veterinarians may author SOAP/assessment notes; farmers may author observations only.
    """
    try:
        return add_clinical_note(consultation_id, current_user, payload.model_dump())
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/consultations/{consultation_id}/notes",
    response_model=list[ClinicalNoteItem],
    summary="Get all clinical notes for consultation"
)
def get_clinical_notes_endpoint(
    consultation_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Retrieves chronological clinical notes and observations."""
    try:
        return get_clinical_notes(consultation_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

"""
backend/app/routes/epidemiological_events.py
============================================
VETRA Phase 13 — Epidemiological Surveillance & Disease Event Routes.

REST endpoints for creating, querying, reviewing, confirming, and dismissing epidemiological events.
Enforces strict RBAC and multi-tenant farm isolation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
    require_admin,
)
from app.schemas.epidemiological_event import (
    EpidemiologicalEventCreate,
    EpidemiologicalEventUpdate,
    EpidemiologicalEventReviewRequest,
    EpidemiologicalEventConfirmRequest,
    EpidemiologicalEventDismissRequest,
    EpidemiologicalEventResponse,
    EpidemiologicalEventType,
    EpidemiologicalEventStatus,
    ReviewState,
    SeverityLevel,
)
from app.database import get_database
from app.services.epidemiological_event_service import epidemiological_event_service

router = APIRouter(
    prefix="/epidemiological-events",
    tags=["Epidemiological Surveillance Events (Phase 13)"]
)


def _check_farm_access_for_event(event: dict, current_user: dict):
    """Restricts farmers strictly to their assigned farm."""
    role = current_user.get("role")
    if role in ["admin", "institutional_officer", "veterinarian"]:
        return
    if role == "farmer":
        db = get_database()
        user_id = str(current_user.get("sub") or current_user.get("id"))
        farms = list(db.farms.find({"owner_id": user_id}))
        owned_farm_ids = {str(f["_id"]) for f in farms}
        for f in farms:
            if f.get("farm_id"):
                owned_farm_ids.add(str(f["farm_id"]))
        if current_user.get("farm_id"):
            owned_farm_ids.add(str(current_user.get("farm_id")))

        event_farm = str(event.get("farm_id"))
        if event_farm not in owned_farm_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-farm surveillance event access is restricted."
            )


@router.post(
    "",
    response_model=EpidemiologicalEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new epidemiological surveillance event"
)
def create_event(
    event_data: EpidemiologicalEventCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    role = current_user.get("role")
    if role not in ["veterinarian", "admin", "institutional_officer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only qualified veterinarians, institutional officers, or administrators can create surveillance events."
        )

    event = epidemiological_event_service.create_event(event_data, current_user)
    return event


@router.get(
    "",
    response_model=List[EpidemiologicalEventResponse],
    summary="List epidemiological events with filters"
)
def list_events(
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    event_type: Optional[EpidemiologicalEventType] = Query(None, description="Filter by event type"),
    status_filter: Optional[EpidemiologicalEventStatus] = Query(None, alias="status", description="Filter by status"),
    review_state: Optional[ReviewState] = Query(None, description="Filter by review state"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_any_authenticated_user)
):
    effective_farm = farm_id
    if current_user.get("role") == "farmer":
        effective_farm = current_user.get("farm_id")
        if not effective_farm:
            return []

    return epidemiological_event_service.list_events(
        farm_id=effective_farm,
        event_type=event_type,
        status=status_filter,
        review_state=review_state,
        severity=severity,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{event_id}",
    response_model=EpidemiologicalEventResponse,
    summary="Get single epidemiological event"
)
def get_event(
    event_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    event = epidemiological_event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")

    _check_farm_access_for_event(event, current_user)
    return event


@router.put(
    "/{event_id}",
    response_model=EpidemiologicalEventResponse,
    summary="Update epidemiological event details"
)
def update_event(
    event_id: str,
    updates: EpidemiologicalEventUpdate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    event = epidemiological_event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")

    role = current_user.get("role")
    if role not in ["veterinarian", "admin", "institutional_officer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to update event.")

    updated = epidemiological_event_service.update_event(event_id, updates, current_user)
    return updated


@router.post(
    "/{event_id}/review",
    response_model=EpidemiologicalEventResponse,
    summary="Submit review on epidemiological event"
)
def review_event(
    event_id: str,
    review_req: EpidemiologicalEventReviewRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    role = current_user.get("role")
    if role not in ["veterinarian", "admin", "institutional_officer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to review event.")

    event = epidemiological_event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")

    updated = epidemiological_event_service.review_event(event_id, review_req, current_user)
    return updated


@router.post(
    "/{event_id}/confirm",
    response_model=EpidemiologicalEventResponse,
    summary="Authoritatively confirm an epidemiological event"
)
def confirm_event(
    event_id: str,
    confirm_req: EpidemiologicalEventConfirmRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    role = current_user.get("role")
    # Strictly require Institutional Officer or Admin for confirmation
    if role not in ["admin", "institutional_officer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Official confirmation of surveillance events requires Institutional Officer or Admin authority."
        )

    event = epidemiological_event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")

    confirmed = epidemiological_event_service.confirm_event(event_id, confirm_req, current_user)
    return confirmed


@router.post(
    "/{event_id}/dismiss",
    response_model=EpidemiologicalEventResponse,
    summary="Dismiss an epidemiological event"
)
def dismiss_event(
    event_id: str,
    dismiss_req: EpidemiologicalEventDismissRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    role = current_user.get("role")
    if role not in ["veterinarian", "admin", "institutional_officer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to dismiss event.")

    event = epidemiological_event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")

    dismissed = epidemiological_event_service.dismiss_event(event_id, dismiss_req, current_user)
    return dismissed

"""
backend/app/routes/veterinary_network.py
========================================
VETRA Phase 12 — Veterinary Network & Directory REST Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.veterinary_network import (
    VeterinaryAvailabilitySummary,
    VeterinaryProfileCreate,
    VeterinaryProfileResponse,
    VeterinaryProfileUpdate,
)
from app.services.veterinary_network_service import (
    create_or_update_profile,
    get_availability_summary,
    get_profile,
    get_regions,
    get_specializations,
    list_profiles,
)


router = APIRouter(
    prefix="/veterinary-network",
    tags=["Veterinary Network & Telemedicine"]
)


@router.post(
    "/profiles",
    response_model=VeterinaryProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or initialize veterinary clinician profile"
)
def register_veterinary_profile(
    payload: VeterinaryProfileCreate,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Registers or updates a verified/pending veterinarian profile.
    Only veterinarians and administrators may create clinician profiles.
    """
    try:
        profile = create_or_update_profile(current_user, payload.model_dump())
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register veterinarian profile: {str(e)}"
        )


@router.get(
    "/profiles",
    response_model=list[VeterinaryProfileResponse],
    summary="Search veterinary clinician directory"
)
def get_veterinary_profiles(
    region: Optional[str] = Query(None, description="Filter by service region"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    species: Optional[str] = Query(None, description="Filter by supported species"),
    availability: Optional[str] = Query(None, description="Filter by availability status"),
    mode: Optional[str] = Query(None, description="Filter by consultation mode"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns filtered directory of veterinary clinicians across network."""
    return list_profiles(
        region=region,
        specialization=specialization,
        species=species,
        availability=availability,
        mode=mode,
        limit=limit,
        skip=skip
    )


@router.get(
    "/availability",
    response_model=VeterinaryAvailabilitySummary,
    summary="Get network-wide veterinary availability summary"
)
def get_network_availability(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Provides real-time counts of available, on-call, and telemedicine-ready clinicians."""
    return get_availability_summary()


@router.get(
    "/specializations",
    response_model=list[str],
    summary="List active veterinary specializations"
)
def list_network_specializations(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns list of distinct veterinary medical specializations."""
    return get_specializations()


@router.get(
    "/regions",
    response_model=list[str],
    summary="List covered service regions"
)
def list_network_regions(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns list of distinct service territories and districts."""
    return get_regions()


@router.get(
    "/profiles/{veterinarian_id}",
    response_model=VeterinaryProfileResponse,
    summary="Get specific veterinarian profile details"
)
def get_veterinarian_profile_by_id(
    veterinarian_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Retrieves full credentials and availability metadata for a clinician."""
    profile = get_profile(veterinarian_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Veterinarian profile '{veterinarian_id}' was not found."
        )
    return profile


@router.put(
    "/profiles/{veterinarian_id}",
    response_model=VeterinaryProfileResponse,
    summary="Update veterinarian profile details"
)
def update_veterinarian_profile_endpoint(
    veterinarian_id: str,
    payload: VeterinaryProfileUpdate,
    current_user: dict = Depends(require_vet_or_admin)
):
    """Updates clinician profile metadata, schedule availability, or supported services."""
    existing = get_profile(veterinarian_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Veterinarian profile '{veterinarian_id}' was not found."
        )

    # Authorization check: only self or admin can edit
    user_id = str(current_user.get("id") or current_user.get("_id") or "")
    if current_user.get("role") != "admin" and existing.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You may only edit your own clinician profile."
        )

    updated_fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated_fields["user_id"] = existing["user_id"]
    updated_fields["veterinarian_id"] = existing["veterinarian_id"]

    return create_or_update_profile(current_user, updated_fields)

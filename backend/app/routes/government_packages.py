"""
backend/app/routes/government_packages.py
=========================================
VETRA Phase 13 — Government Data Packages & Surveillance Export REST Endpoints.

Implements:
- Package compilation & generation
- Multi-format export (JSON, CSV, PDF)
- Safety gate validation
- Institutional review & approval
- Submission execution with strict failsafe blocks
- Adapter and integration status checks
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse

from app.permissions import get_current_user
from app.schemas.government_package import (
    GovernmentDataPackageCreate,
    PackageApprovalRequest,
    PackageSubmitRequest,
    PackageValidationResponse,
)
from app.services.government_data_package import government_data_package_service
from app.services.institutional_adapters import get_all_adapters, get_institutional_adapter

router = APIRouter(prefix="/government-packages", tags=["Government Data Packages"])


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_government_package(
    req: GovernmentDataPackageCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Compiles active surveillance intelligence into a standardized Government Data Package.
    Authorized for institutional officers and administrators.
    """
    user_role = (current_user.get("role") or "").lower()
    if user_role not in ["institutional_officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmers and veterinarians cannot generate government surveillance packages."
        )

    return government_data_package_service.create_package(req, user=current_user)


@router.get("")
def list_government_packages(
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists compiled government data packages.
    Accessible to institutional officers, veterinarians, and administrators.
    """
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmers are restricted from viewing government data packages."
        )

    return government_data_package_service.list_packages(limit=limit)


@router.get("/{package_id}")
def get_government_package(
    package_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves full metadata for a government data package."""
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    pkg = government_data_package_service.get_package(package_id)
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Package {package_id} not found.")
    return pkg


@router.get("/{package_id}/json")
def export_package_json(
    package_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Exports standardized package structure in JSON format."""
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        return government_data_package_service.export_json(package_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{package_id}/csv")
def export_package_csv(
    package_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Exports surveillance metrics in CSV tabular format."""
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        csv_data = government_data_package_service.export_csv(package_id)
        return PlainTextResponse(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={package_id}.csv"}
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{package_id}/pdf")
def export_package_pdf(
    package_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Exports structured PDF document for the government surveillance package."""
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        pdf_bytes = government_data_package_service.export_pdf(package_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={package_id}.pdf"}
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{package_id}/validate", response_model=PackageValidationResponse)
def validate_package_safety_gates(
    package_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluates the 8 mandatory submission safety gates for this package.
    """
    user_role = (current_user.get("role") or "").lower()
    if user_role == "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return government_data_package_service.validate_safety_gates(package_id)


@router.post("/{package_id}/approve")
def approve_government_package(
    package_id: str,
    req: PackageApprovalRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Formal human authorization of a government data package (DRAFT -> APPROVED).
    Requires institutional officer or administrator role.
    """
    try:
        return government_data_package_service.approve_package(
            package_id=package_id,
            notes=req.approval_notes,
            user=current_user
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{package_id}/submit")
def submit_government_package(
    package_id: str,
    req: PackageSubmitRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiates external submission subject to 8 safety gates.
    Blocks with HTTP 400/409 if adapter is NOT_CONFIGURED or safety gates fail.
    """
    try:
        result = government_data_package_service.submit_package(
            package_id=package_id,
            adapter_id=req.adapter_id,
            user=current_user,
            notes=req.submission_notes
        )
        if not result.get("success"):
            return Response(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=str(result),
                media_type="application/json"
            )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# -----------------------------------------------------------------
# Institutional Integration & Adapters Status
# -----------------------------------------------------------------
integration_router = APIRouter(prefix="/institutional-integrations", tags=["Institutional Integrations"])


@integration_router.get("/status")
def get_integration_status(
    current_user: dict = Depends(get_current_user)
):
    """Returns connectivity and configuration status for government surveillance gateways."""
    adapter = get_institutional_adapter()
    return {
        "government_adapter_status": getattr(adapter, "state", "NOT_CONFIGURED"),
        "active_adapter": adapter.get_status(),
        "safety_disclaimer": "All external government integrations default to NOT_CONFIGURED in safe local operation.",
        "support_live_submission": False
    }


@integration_router.get("/adapters")
def list_available_adapters(
    current_user: dict = Depends(get_current_user)
):
    """Lists registered external reporting adapters."""
    adapters = get_all_adapters()
    return [a.get_status() for a in adapters]

"""
VETRA Phase 12 - Institutional Disease Reporting & Government Surveillance Routes

REST endpoints for creating, reviewing, approving, submitting, and exporting institutional reports,
as well as inspecting institutional integration adapters.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse

from app.permissions import (
    require_any_authenticated_user,
    require_role,
    require_vet_or_admin,
)
from app.schemas.institutional_reporting import (
    InstitutionalReportCreate,
    InstitutionalReportUpdate,
    ReportReviewAction,
    ReportApproveAction,
    ReportSubmitAction,
    InstitutionalReportResponse,
    IntegrationStatusResponse,
    ReportType,
    ReportStatus,
    ReportSeverity,
)
from app.services.institutional_reporting_service import institutional_reporting_service
from app.services.institutional_adapters import get_all_adapters, get_adapter

router = APIRouter(
    prefix="/institutional",
    tags=["Institutional Reporting & Disease Surveillance Integration"]
)


def _check_farm_access_for_report(report: dict, current_user: dict):
    """
    Ensure farmer can only view reports for their own farm.
    Institutional officer, veterinarian, and admin have broader institutional access.
    """
    role = current_user.get("role")
    if role in ["admin", "institutional_officer", "veterinarian"]:
        return
    if role == "farmer":
        user_farm = current_user.get("farm_id")
        report_farm = report.get("farm_id")
        if user_farm and report_farm and str(user_farm) != str(report_farm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-farm access is restricted."
            )


@router.post(
    "/reports",
    response_model=InstitutionalReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new institutional disease/surveillance report"
)
def create_report(
    data: InstitutionalReportCreate,
    current_user: dict = Depends(require_role("veterinarian", "institutional_officer", "admin"))
):
    """
    Create a new report in DRAFT state.
    Farmers cannot author institutional reports directly without qualified review.
    """
    try:
        report = institutional_reporting_service.create_report(data, current_user)
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create report: {str(e)}")


@router.get(
    "/reports",
    response_model=List[InstitutionalReportResponse],
    summary="List institutional reports with filtering"
)
def list_reports(
    report_type: Optional[ReportType] = Query(None, description="Filter by report type"),
    report_status: Optional[ReportStatus] = Query(None, alias="status", description="Filter by status"),
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    severity: Optional[ReportSeverity] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List reports according to RBAC.
    Farmers are strictly restricted to their own farm.
    """
    effective_farm_id = farm_id
    if current_user.get("role") == "farmer":
        user_farm = current_user.get("farm_id")
        if not user_farm:
            return []
        effective_farm_id = user_farm

    reports = institutional_reporting_service.list_reports(
        report_type=report_type,
        status=report_status,
        farm_id=effective_farm_id,
        severity=severity,
        skip=skip,
        limit=limit
    )
    return reports


@router.get(
    "/reports/{report_id}",
    response_model=InstitutionalReportResponse,
    summary="Get single institutional report"
)
def get_report(
    report_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Fetch single report by human report_id or MongoDB _id.
    Enforces privacy and cross-farm isolation.
    """
    report = institutional_reporting_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report {report_id} not found.")

    _check_farm_access_for_report(report, current_user)
    return report


@router.put(
    "/reports/{report_id}",
    response_model=InstitutionalReportResponse,
    summary="Update draft institutional report"
)
def update_report(
    report_id: str,
    data: InstitutionalReportUpdate,
    current_user: dict = Depends(require_role("veterinarian", "institutional_officer", "admin"))
):
    """
    Update a report. Only drafts or under_review reports can be modified.
    """
    report = institutional_reporting_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report {report_id} not found.")

    try:
        updated = institutional_reporting_service.update_report(report_id, data, current_user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reports/{report_id}/review",
    response_model=InstitutionalReportResponse,
    summary="Submit report for institutional review"
)
def review_report(
    report_id: str,
    data: Optional[ReportReviewAction] = None,
    current_user: dict = Depends(require_role("veterinarian", "institutional_officer", "admin"))
):
    """
    Transition report from DRAFT to UNDER_REVIEW.
    """
    action = data or ReportReviewAction()
    try:
        updated = institutional_reporting_service.review_report(report_id, action, current_user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reports/{report_id}/approve",
    response_model=InstitutionalReportResponse,
    summary="Approve institutional report (Officer/Admin only)"
)
def approve_report(
    report_id: str,
    data: Optional[ReportApproveAction] = None,
    current_user: dict = Depends(require_role("institutional_officer", "admin"))
):
    """
    Approve an under_review report. Only institutional officers or administrators can approve.
    """
    action = data or ReportApproveAction()
    try:
        updated = institutional_reporting_service.approve_report(report_id, action, current_user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reports/{report_id}/submit",
    response_model=InstitutionalReportResponse,
    summary="Submit approved report to institutional integration adapter"
)
def submit_report(
    report_id: str,
    data: Optional[ReportSubmitAction] = None,
    current_user: dict = Depends(require_role("institutional_officer", "admin"))
):
    """
    Submit an approved report via configured adapter.
    If the adapter is NOT_CONFIGURED, transmission is recorded as simulated/not-configured,
    and NO live government connection is claimed.
    """
    action = data or ReportSubmitAction()
    try:
        updated = institutional_reporting_service.submit_report(report_id, action, current_user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reports/{report_id}/cancel",
    response_model=InstitutionalReportResponse,
    summary="Cancel institutional report"
)
def cancel_report(
    report_id: str,
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    current_user: dict = Depends(require_role("institutional_officer", "admin"))
):
    """
    Cancel an institutional report.
    """
    try:
        cancelled = institutional_reporting_service.cancel_report(report_id, reason, current_user)
        return cancelled
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/reports/{report_id}/status",
    summary="Check report transmission and workflow status"
)
def get_report_status(
    report_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get detailed transmission status, adapter acknowledgment, and workflow timeline.
    """
    report = institutional_reporting_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report {report_id} not found.")

    _check_farm_access_for_report(report, current_user)

    return {
        "report_id": report["report_id"],
        "status": report["status"],
        "approval_status": report.get("approval_status"),
        "approved_by": report.get("approved_by"),
        "approved_at": report.get("approved_at"),
        "submission_details": report.get("submission_details"),
        "audit_trail": report.get("audit_trail", [])
    }


@router.get(
    "/reports/{report_id}/export",
    summary="Export institutional report as JSON or CSV"
)
def export_report(
    report_id: str,
    format: str = Query("json", pattern="^(json|csv)$", description="Export format: json or csv"),
    redact_pii: bool = Query(False, description="Redact farm and owner names for institutional research"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Export institutional report with audit trail and optional PII privacy redaction.
    """
    report = institutional_reporting_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report {report_id} not found.")

    _check_farm_access_for_report(report, current_user)

    try:
        content = institutional_reporting_service.export_report(
            report_id=report_id,
            format=format,
            redact_pii=redact_pii,
            current_user=current_user
        )

        media_type = "application/json" if format == "json" else "text/csv"
        filename = f"{report['report_id']}.{format}"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/integrations",
    summary="List available institutional & government integration adapters"
)
def list_integrations(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List all configured institutional reporting adapters.
    Demonstrates readiness without fabricating live external connections.
    """
    adapters = get_all_adapters()
    return [
        {
            "adapter_id": a.adapter_id,
            "adapter_name": a.adapter_name,
            "system_type": a.system_type,
            "status": a.get_status().get("status"),
            "disclaimer": a.get_status().get("disclaimer"),
            "supports_live_submission": a.get_status().get("supports_live_submission"),
        }
        for a in adapters
    ]


@router.get(
    "/integrations/{adapter_id}/status",
    summary="Inspect status of an institutional integration adapter"
)
def get_integration_status(
    adapter_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get detailed connection and configuration status of a specific integration adapter.
    """
    adapter = get_adapter(adapter_id)
    if not adapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Adapter {adapter_id} not found.")

    return adapter.get_status()

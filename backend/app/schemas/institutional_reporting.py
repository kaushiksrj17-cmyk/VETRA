"""
backend/app/schemas/institutional_reporting.py
==============================================
VETRA Phase 12 — Institutional Health Reporting & Government Surveillance Schemas.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


ReportType = Literal[
    "disease_event",
    "animal_health_event",
    "farm_health_summary",
    "surveillance_summary",
    "veterinary_case_summary",
    "outbreak_candidate_review",
]

ReportStatus = Literal[
    "draft",
    "under_review",
    "approved",
    "submitted",
    "acknowledged",
    "rejected",
    "cancelled",
]

ReportSeverity = Literal[
    "routine",
    "elevated",
    "high",
    "critical",
    "low",
    "moderate",
]

OUTBREAK_CANDIDATE_DISCLAIMER = (
    "INSTITUTIONAL REGULATORY NOTICE: 'outbreak_candidate_review' indicates an investigative dossier "
    "compiled for qualified institutional veterinary review. It does NOT denote a confirmed clinical outbreak."
)


class ReportEvidenceItem(BaseModel):
    evidence_type: str
    reference_id: str
    description: Optional[str] = None
    created_at: Optional[str] = None


class ReportApprovalEvent(BaseModel):
    action: str
    performed_by: str
    performed_by_name: Optional[str] = None
    performed_by_role: Optional[str] = None
    comments: Optional[str] = None
    timestamp: str


class InstitutionalReportCreate(BaseModel):
    report_type: ReportType = "surveillance_summary"
    title: Optional[str] = "Institutional Epidemiological Report"
    farm_id: Optional[str] = None
    animal_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    surveillance_event_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    reporting_organization: Optional[str] = "VETRA Institutional Health Network"
    severity: ReportSeverity = "routine"
    summary: str = Field(..., min_length=5)
    evidence: list[Any] = Field(default_factory=list)
    clinical_notes: Optional[str] = None
    surveillance_context: Optional[dict[str, Any]] = None
    disclaimer: Optional[str] = OUTBREAK_CANDIDATE_DISCLAIMER


class InstitutionalReportUpdate(BaseModel):
    title: Optional[str] = None
    severity: Optional[ReportSeverity] = None
    summary: Optional[str] = None
    clinical_notes: Optional[str] = None
    evidence: Optional[list[Any]] = None


class InstitutionalReviewRequest(BaseModel):
    comments: Optional[str] = None
    reviewer_notes: Optional[str] = None


class InstitutionalApproveRequest(BaseModel):
    comments: Optional[str] = None
    approval_notes: Optional[str] = None
    digital_signature_reference: Optional[str] = None


class InstitutionalSubmitRequest(BaseModel):
    target_authority: Optional[str] = "National Animal Health Reporting Service"
    submission_notes: Optional[str] = None
    submission_remarks: Optional[str] = None
    adapter_id: Optional[str] = None


ReportReviewAction = InstitutionalReviewRequest
ReportApproveAction = InstitutionalApproveRequest
ReportSubmitAction = InstitutionalSubmitRequest


class InstitutionalReportResponse(BaseModel):
    id: str
    report_id: str
    report_type: ReportType
    title: Optional[str] = None
    farm_id: Optional[str] = None
    farm_name: Optional[str] = None
    animal_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    surveillance_event_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    reporting_organization: Optional[str] = None
    reporting_user_id: Optional[str] = None
    reporting_user_name: Optional[str] = None
    reporting_user_role: Optional[str] = None
    severity: ReportSeverity
    status: ReportStatus
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    clinical_notes: Optional[str] = None
    surveillance_context: Optional[dict[str, Any]] = None
    approval_trail: list[ReportApprovalEvent] = Field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_status: Optional[str] = None
    submission_details: Optional[dict[str, Any]] = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    external_submission_id: Optional[str] = None
    external_acknowledgement: Optional[dict[str, Any]] = None
    regulatory_disclaimer: str = OUTBREAK_CANDIDATE_DISCLAIMER
    created_at: str
    submitted_at: Optional[str] = None
    updated_at: str


class InstitutionalIntegrationStatusResponse(BaseModel):
    adapter_name: str
    adapter_state: Literal["NOT_CONFIGURED", "CONFIGURED", "CONNECTED", "ERROR"]
    submission_enabled: bool
    configured_endpoints: dict[str, str]
    last_health_check: str
    safety_notice: str


IntegrationStatusResponse = InstitutionalIntegrationStatusResponse


"""
backend/app/schemas/government_package.py
=========================================
VETRA Phase 13 — Government & Institutional Data Package Schemas.

Defines standardized data packaging structures for epidemiological surveillance exports.
Adheres strictly to the mandate:
"Government-ready export package — not an official submission."
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

GOVERNMENT_PACKAGE_DISCLAIMER = (
    "Government-ready export package — not an official submission. "
    "Generated for authorized institutional review and regulatory data exchange. "
    "Does not constitute an autonomous regulatory filing."
)


class ReportingPeriod(BaseModel):
    start_date: str = Field(..., description="ISO start date of surveillance window")
    end_date: str = Field(..., description="ISO end date of surveillance window")
    period_type: str = Field(default="custom", description="daily, weekly, monthly, quarterly, or custom")


class PackageGeographicAggregation(BaseModel):
    state: str = Field(default="Gujarat")
    district: str = Field(default="Anand")
    sub_district: Optional[str] = None
    total_holdings: int = Field(default=0)
    risk_level: str = Field(default="NOMINAL")


class SpeciesCount(BaseModel):
    species: str
    count: int
    signals_count: int = 0


class EvidenceProvenance(BaseModel):
    iot_telemetry: bool = True
    computer_vision: bool = True
    predictive_ai: bool = True
    veterinary_records: bool = True
    laboratory_records: bool = True
    preventive_care: bool = True


class GovernmentDataPackageCreate(BaseModel):
    reporting_period: ReportingPeriod
    reporting_entity_type: str = Field(
        default="district_surveillance_unit",
        description="Type of entity: district_surveillance_unit, state_veterinary_authority, institutional_monitor"
    )
    title: str = Field(default="Livestock Health Surveillance Package", description="Descriptive title")
    include_events: bool = Field(default=True, description="Whether to include open epidemiological events")
    include_clusters: bool = Field(default=True, description="Whether to include active surveillance clusters")
    mask_pii: bool = Field(default=True, description="Whether to mask farmer PII and holding coordinates")
    notes: Optional[str] = Field(default=None, description="Contextual notes from generating officer")


class PackageApprovalRequest(BaseModel):
    approval_notes: str = Field(default="", description="Institutional officer authorization rationale")


class PackageSubmitRequest(BaseModel):
    adapter_id: str = Field(default="mock_gov_adapter", description="Registered adapter identifier")
    submission_notes: Optional[str] = Field(default=None, description="Filing remarks")


class PackageValidationResponse(BaseModel):
    is_valid: bool
    validation_passed: bool
    package_id: str
    safety_gates_status: Dict[str, bool]
    errors: List[str]
    warnings: List[str]
    timestamp: str


class GovernmentDataPackageResponse(BaseModel):
    package_id: str
    schema_version: str = "1.0.0"
    title: str
    reporting_period: Dict[str, Any]
    reporting_entity_type: str
    generated_at: str
    generated_by: Dict[str, Any]
    review_status: str
    approval_status: str
    approved_by: Optional[Dict[str, Any]] = None
    approved_at: Optional[str] = None
    submission_status: str
    external_submission_id: Optional[str] = None
    affected_animal_count: int
    affected_farm_count: int
    geographic_aggregation: Dict[str, Any]
    species_distribution: List[Dict[str, Any]]
    risk_summaries: Dict[str, Any]
    event_summaries: List[Dict[str, Any]]
    surveillance_summaries: Dict[str, Any]
    laboratory_references: List[Dict[str, Any]]
    veterinary_case_references: List[str]
    evidence_provenance: Dict[str, Any]
    safety_disclaimer: str = GOVERNMENT_PACKAGE_DISCLAIMER
    audit_metadata: Dict[str, Any]

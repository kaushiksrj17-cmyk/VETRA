"""
backend/app/schemas/epidemiological_event.py
============================================
VETRA Phase 13 — Epidemiological Surveillance & Disease Event Schemas.

Provides standardized schemas for event detection, risk scoring, multi-source evidence
correlation, human review workflows, and official institutional confirmation states.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


EpidemiologicalEventType = Literal[
    "unusual_mortality",
    "abnormal_health_cluster",
    "disease_suspect",
    "surveillance_signal",
    "cross_farm_signal",
    "geographic_cluster",
    "persistent_health_anomaly",
    "veterinary_escalation",
]

EpidemiologicalEventStatus = Literal[
    "OPEN",
    "UNDER_REVIEW",
    "CONFIRMED",
    "DISMISSED",
    "RESOLVED",
    "CLOSED",
]

ReviewState = Literal[
    "SIGNAL",
    "SUSPECT",
    "REVIEW_REQUIRED",
    "UNDER_REVIEW",
    "CONFIRMED",
    "DISMISSED",
]

SeverityLevel = Literal[
    "low",
    "moderate",
    "high",
    "critical",
]

EPIDEMIOLOGICAL_EVENT_DISCLAIMER = (
    "VETRA SURVEILLANCE NOTICE: Automated surveillance events represent statistical anomaly "
    "signals or clinical suspects. Confirmation requires authorized human institutional review. "
    "VETRA does not autonomously confirm official disease events."
)
SURVEILLANCE_SAFETY_DISCLAIMER = EPIDEMIOLOGICAL_EVENT_DISCLAIMER


class EvidenceSignal(BaseModel):
    source_type: str = Field(..., description="e.g. iot_telemetry, computer_vision, predictive_ai, veterinary_case, laboratory")
    reference_id: str
    signal_name: str
    severity: SeverityLevel = "moderate"
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    details: Optional[Dict[str, Any]] = None
    detected_at: Optional[str] = None


class ReviewAuditEntry(BaseModel):
    action: str = Field(..., description="e.g. review_started, confirmed, dismissed, comment_added")
    performed_by: str
    performed_by_name: Optional[str] = None
    performed_by_role: str
    comments: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EpidemiologicalEventCreate(BaseModel):
    event_type: EpidemiologicalEventType
    farm_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    animal_ids: List[str] = Field(default_factory=list)
    species: Any = Field(default_factory=lambda: ["cattle"])
    geographic_context: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"district": "Anand", "state": "Gujarat", "country": "India"}
    )
    detected_at: Optional[datetime] = None
    observation_window: str = "7d"
    evidence_sources: List[str] = Field(default_factory=list)
    clinical_signals: List[Any] = Field(default_factory=list)
    surveillance_signals: List[Any] = Field(default_factory=list)
    predictive_signals: List[Any] = Field(default_factory=list)
    laboratory_references: List[str] = Field(default_factory=list)
    visual_references: List[str] = Field(default_factory=list)
    veterinary_case_references: List[str] = Field(default_factory=list)
    risk_score: float = Field(50.0, ge=0.0, le=100.0)
    confidence: float = Field(0.75, ge=0.0, le=1.0)
    severity: SeverityLevel = "moderate"
    status: EpidemiologicalEventStatus = "OPEN"
    review_state: ReviewState = "SIGNAL"
    notes: Optional[str] = None


class EpidemiologicalEventUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    animal_ids: Optional[List[str]] = None
    laboratory_references: Optional[List[str]] = None
    veterinary_case_references: Optional[List[str]] = None
    notes: Optional[str] = None


class EpidemiologicalEventReviewRequest(BaseModel):
    reviewer_notes: Optional[str] = None
    review_notes: Optional[str] = None
    new_review_state: Optional[str] = None
    review_state: Optional[str] = None


class EpidemiologicalEventConfirmRequest(BaseModel):
    confirmation_notes: Optional[str] = None
    confirmation_authority: Optional[str] = None
    official_reference: Optional[str] = None
    containment_measures: Optional[str] = None


class EpidemiologicalEventDismissRequest(BaseModel):
    reason: Optional[str] = None
    dismissal_rationale: Optional[str] = None
    explanatory_notes: Optional[str] = None


class EpidemiologicalEventResponse(BaseModel):
    event_id: str
    event_type: EpidemiologicalEventType
    farm_id: str
    title: str
    summary: str
    animal_ids: List[str]
    species: List[str]
    geographic_context: Dict[str, Any]
    detected_at: str
    observation_window: str
    evidence_sources: List[str]
    clinical_signals: List[Any]
    surveillance_signals: List[Any]
    predictive_signals: List[Any]
    laboratory_references: List[str]
    visual_references: List[str]
    veterinary_case_references: List[str]
    risk_score: float
    confidence: float
    severity: SeverityLevel
    status: EpidemiologicalEventStatus
    review_state: ReviewState
    created_by: Dict[str, Any]
    reviewed_by: Optional[Dict[str, Any]] = None
    confirmed_by: Optional[Dict[str, Any]] = None
    review_history: List[ReviewAuditEntry] = Field(default_factory=list)
    created_at: str
    updated_at: str
    schema_version: str = "1.0.0"
    disclaimer: str = EPIDEMIOLOGICAL_EVENT_DISCLAIMER

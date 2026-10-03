from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


CaseType = Literal[
    "health_alert",
    "preventive_follow_up",
    "routine_checkup",
    "suspected_disease",
    "treatment",
    "vaccination",
    "deworming",
    "other"
]

CasePriority = Literal[
    "critical",
    "high",
    "medium",
    "low"
]

CaseStatus = Literal[
    "open",
    "unassigned",
    "assigned",
    "accepted",
    "in_review",
    "teleconsultation",
    "farm_visit_required",
    "treatment",
    "follow_up",
    "resolved",
    "closed"
]

CaseSource = Literal[
    "alert",
    "ai_assessment",
    "preventive_scheduler",
    "manual",
    "veterinary_visit",
    "predictive_assessment",
    "visual_health",
    "multimodal_health",
    "surveillance",
    "telemedicine"
]


class MedicationItem(BaseModel):
    name: str = Field(..., min_length=1)
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None


class TimelineEvent(BaseModel):
    event: str
    title: str
    description: Optional[str] = None
    performed_by: str
    performed_by_name: Optional[str] = None
    performed_by_role: Optional[str] = None
    timestamp: str


class VeterinaryCaseCreate(BaseModel):
    animal_id: str
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    case_type: CaseType = "routine_checkup"
    priority: CasePriority = "medium"
    source: CaseSource = "manual"
    alert_id: Optional[str] = None
    health_risk_score: Optional[float] = None
    disease_risk_level: Optional[str] = None
    early_warning_level: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    assigned_veterinarian_id: Optional[str] = None
    assigned_veterinarian_name: Optional[str] = None
    clinical_findings: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medications: list[MedicationItem] = Field(default_factory=list)
    recommendations: Optional[str] = None
    follow_up_date: Optional[str] = None


class VeterinaryCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[CasePriority] = None
    clinical_findings: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medications: Optional[list[MedicationItem]] = None
    recommendations: Optional[str] = None
    follow_up_date: Optional[str] = None
    notes: Optional[str] = None


class VeterinaryCaseAssign(BaseModel):
    veterinarian_id: str
    veterinarian_name: Optional[str] = None
    notes: Optional[str] = None


class VeterinaryCaseStatusUpdate(BaseModel):
    status: CaseStatus
    notes: Optional[str] = None


class VeterinaryCaseResolve(BaseModel):
    resolution_summary: Optional[str] = None
    final_diagnosis: Optional[str] = None
    recommendations: Optional[str] = None


class VeterinaryCaseResponse(BaseModel):
    id: str
    case_number: str
    animal_id: str
    farm_id: str
    owner_id: str
    title: str
    description: Optional[str] = None
    case_type: CaseType
    priority: CasePriority
    status: CaseStatus
    source: CaseSource
    alert_id: Optional[str] = None
    health_risk_score: Optional[float] = None
    disease_risk_level: Optional[str] = None
    early_warning_level: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    assigned_veterinarian_id: Optional[str] = None
    assigned_veterinarian_name: Optional[str] = None
    clinical_findings: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medications: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: Optional[str] = None
    follow_up_date: Optional[str] = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None

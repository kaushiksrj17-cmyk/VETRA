"""
backend/app/schemas/telemedicine.py
===================================
VETRA Phase 12 — Telemedicine Consultation & Clinical Notes Schemas.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


ConsultationMode = Literal[
    "telemedicine",
    "video",
    "voice",
    "chat",
    "async_review",
    "farm_visit_scheduled",
]

ConsultationStatus = Literal[
    "requested",
    "scheduled",
    "accepted",
    "in_progress",
    "completed",
    "cancelled",
    "no_show",
    "follow_up_required",
]

TELEMEDICINE_SAFETY_NOTICE = (
    "CLINICAL SAFETY MANDATE: Telemedicine assessment provides prospective and triage decision support. "
    "Telemedicine assessment may be limited when physical examination, laboratory testing, imaging, "
    "or on-site veterinary assessment is required."
)


class ClinicalNoteItem(BaseModel):
    note_id: str
    author_id: str
    author_name: str
    author_role: str
    note_type: str = "veterinary_clinical_note"
    note_text: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    recommendations: Optional[str] = None
    farmer_symptoms: Optional[str] = None
    created_at: str


class AddClinicalNoteRequest(BaseModel):
    note_type: Optional[str] = None
    note_text: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    recommendations: Optional[str] = None
    farmer_symptoms: Optional[str] = None



class TelemedicineConsultationCreate(BaseModel):
    case_id: Optional[str] = None
    animal_id: str
    farm_id: Optional[str] = None
    veterinarian_id: Optional[str] = None
    mode: ConsultationMode = "telemedicine"
    scheduled_at: Optional[str] = None
    chief_complaint: str = Field(..., min_length=3, max_length=500)
    clinical_summary: Optional[str] = None
    visual_evidence_ids: list[str] = Field(default_factory=list)
    health_reading_ids: list[str] = Field(default_factory=list)
    predictive_assessment_ids: list[str] = Field(default_factory=list)
    surveillance_context: Optional[dict[str, Any]] = None


class TelemedicineConsultationUpdate(BaseModel):
    mode: Optional[ConsultationMode] = None
    status: Optional[ConsultationStatus] = None
    scheduled_at: Optional[str] = None
    chief_complaint: Optional[str] = None
    clinical_summary: Optional[str] = None
    recommendations: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_reason: Optional[str] = None


class TelemedicineCompleteRequest(BaseModel):
    recommendations: str = Field(..., min_length=3)
    final_assessment: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_reason: Optional[str] = None


class TelemedicineCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class TelemedicineConsultationResponse(BaseModel):
    id: str
    consultation_id: str
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    animal_id: str
    animal_tag: Optional[str] = None
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    farmer_id: str
    farmer_name: Optional[str] = None
    veterinarian_id: Optional[str] = None
    veterinarian_name: Optional[str] = None
    mode: ConsultationMode
    status: ConsultationStatus
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    chief_complaint: str
    clinical_summary: Optional[str] = None
    visual_evidence_ids: list[str] = Field(default_factory=list)
    health_reading_ids: list[str] = Field(default_factory=list)
    predictive_assessment_ids: list[str] = Field(default_factory=list)
    surveillance_context: Optional[dict[str, Any]] = None
    clinical_notes: list[ClinicalNoteItem] = Field(default_factory=list)
    recommendations: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_reason: Optional[str] = None
    safety_notice: str = TELEMEDICINE_SAFETY_NOTICE
    created_at: str
    updated_at: str

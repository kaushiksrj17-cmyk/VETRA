"""
backend/app/schemas/veterinary_network.py
=========================================
VETRA Phase 12 — Veterinary Telemedicine & Network Subsystem Schemas.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


ConsultationMode = Literal[
    "in_person",
    "telemedicine",
    "farm_visit",
    "emergency",
    "follow_up",
]

AvailabilityStatus = Literal[
    "available",
    "busy",
    "on_call",
    "offline",
]

VerificationStatus = Literal[
    "unverified",
    "pending",
    "verified",
]


class VeterinaryProfileCreate(BaseModel):
    veterinarian_id: Optional[str] = None
    user_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=120)
    registration_reference: Optional[str] = "NOT_PROVIDED"
    specialization: list[str] = Field(default_factory=lambda: ["general_practice"])
    qualifications: Optional[str] = None
    experience_years: int = Field(default=0, ge=0, le=60)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    service_regions: list[str] = Field(default_factory=lambda: ["National"])
    supported_species: list[str] = Field(default_factory=lambda: ["cattle", "buffalo"])
    availability_status: AvailabilityStatus = "available"
    consultation_modes: list[ConsultationMode] = Field(
        default_factory=lambda: ["telemedicine", "farm_visit", "in_person"]
    )
    organization: Optional[str] = "Independent"
    verification_status: VerificationStatus = "unverified"

    @field_validator("specialization", mode="before")
    @classmethod
    def _coerce_specialization(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("qualifications", mode="before")
    @classmethod
    def _coerce_qualifications(cls, v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return v


class VeterinaryProfileUpdate(BaseModel):
    name: Optional[str] = None
    registration_reference: Optional[str] = None
    specialization: Optional[list[str]] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    phone: Optional[str] = None

    @field_validator("specialization", mode="before")
    @classmethod
    def _coerce_specialization(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("qualifications", mode="before")
    @classmethod
    def _coerce_qualifications(cls, v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return v

    email: Optional[EmailStr] = None
    service_regions: Optional[list[str]] = None
    supported_species: Optional[list[str]] = None
    availability_status: Optional[AvailabilityStatus] = None
    consultation_modes: Optional[list[ConsultationMode]] = None
    organization: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None


class VeterinaryProfileResponse(BaseModel):
    id: Optional[str] = None
    veterinarian_id: str
    user_id: str
    name: str
    registration_reference: str
    specialization: list[str]
    qualifications: Optional[str] = None
    experience_years: int
    phone: Optional[str] = None
    email: Optional[str] = None
    service_regions: list[str]
    supported_species: list[str]
    availability_status: AvailabilityStatus
    consultation_modes: list[ConsultationMode]
    organization: Optional[str] = None
    verification_status: VerificationStatus
    active_cases_count: int = 0
    created_at: str
    updated_at: str


class VeterinaryAvailabilitySummary(BaseModel):
    total_veterinarians: int
    available_now: int
    on_call: int
    busy: int
    offline: int
    telemedicine_enabled: int
    regions_covered: list[str]
    specializations: list[str]

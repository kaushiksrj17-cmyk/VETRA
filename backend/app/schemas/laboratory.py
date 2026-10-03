"""
backend/app/schemas/laboratory.py
=================================
VETRA Phase 12 — Laboratory Result References & Diagnostic Reports Schemas.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field


LabResultStatus = Literal[
    "pending",
    "negative",
    "positive",
    "inconclusive",
    "invalid",
    "not_available",
]


class LaboratoryResultCreate(BaseModel):
    case_id: Optional[str] = None
    animal_id: str
    farm_id: Optional[str] = None
    test_name: str = Field(..., min_length=2, max_length=150)
    laboratory_name: Optional[str] = "Veterinary Diagnostic Laboratory"
    sample_type: Optional[str] = "Blood Serum"
    collection_date: Optional[str] = None
    result_status: LabResultStatus = "not_available"
    result_summary: Optional[str] = None
    reference_document: Optional[str] = None
    document_hash: Optional[str] = None
    verified: bool = False


class LaboratoryResultResponse(BaseModel):
    id: str
    result_id: str
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    animal_id: str
    animal_tag: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    test_name: str
    laboratory_name: Optional[str] = None
    sample_type: Optional[str] = None
    collection_date: Optional[str] = None
    result_status: LabResultStatus
    result_summary: Optional[str] = None
    reference_document: Optional[str] = None
    document_hash: Optional[str] = None
    verified: bool
    created_at: str

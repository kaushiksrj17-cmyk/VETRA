from typing import Optional
from pydantic import BaseModel, Field


# ----------------------------------------------------
# Vaccination Schemas
# ----------------------------------------------------
class VaccinationRecordCreate(BaseModel):
    animal_id: str
    vaccine_name: str = Field(..., min_length=2, max_length=100)
    administered_date: str
    next_due_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None


class VaccinationRecordResponse(BaseModel):
    id: str
    animal_id: str
    farm_id: str
    owner_id: str
    vaccine_name: str
    administered_date: str
    next_due_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


# ----------------------------------------------------
# Deworming Schemas
# ----------------------------------------------------
class DewormingRecordCreate(BaseModel):
    animal_id: str
    medicine_name: str = Field(..., min_length=2, max_length=100)
    dosage: str = Field(..., min_length=1, max_length=50)
    administered_date: str
    next_due_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    notes: Optional[str] = None


class DewormingRecordResponse(BaseModel):
    id: str
    animal_id: str
    farm_id: str
    owner_id: str
    medicine_name: str
    dosage: str
    administered_date: str
    next_due_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


# ----------------------------------------------------
# Treatment Schemas
# ----------------------------------------------------
class TreatmentRecordCreate(BaseModel):
    animal_id: str
    condition_diagnosed: str = Field(..., min_length=2, max_length=150)
    medication: str = Field(..., min_length=2, max_length=100)
    dosage: str = Field(..., min_length=1, max_length=50)
    start_date: str
    end_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    alert_id: Optional[str] = None
    outcome: Optional[str] = "ongoing"
    notes: Optional[str] = None


class TreatmentRecordResponse(BaseModel):
    id: str
    animal_id: str
    farm_id: str
    owner_id: str
    condition_diagnosed: str
    medication: str
    dosage: str
    start_date: str
    end_date: Optional[str] = None
    veterinarian_name: Optional[str] = None
    alert_id: Optional[str] = None
    outcome: Optional[str] = "ongoing"
    notes: Optional[str] = None
    created_at: str


# ----------------------------------------------------
# Veterinary Visit Schemas
# ----------------------------------------------------
class VetVisitRecordCreate(BaseModel):
    animal_id: str
    veterinarian_name: str = Field(..., min_length=2, max_length=100)
    visit_date: str
    observations: str = Field(..., min_length=2, max_length=500)
    recommendations: str = Field(..., min_length=2, max_length=500)
    follow_up_date: Optional[str] = None
    alert_id: Optional[str] = None


class VetVisitRecordResponse(BaseModel):
    id: str
    animal_id: str
    farm_id: str
    owner_id: str
    veterinarian_name: str
    visit_date: str
    observations: str
    recommendations: str
    follow_up_date: Optional[str] = None
    alert_id: Optional[str] = None
    created_at: str

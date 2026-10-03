from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_database
from app.permissions import require_any_authenticated_user
from app.schemas.prevention import (
    VaccinationRecordCreate, VaccinationRecordResponse,
    DewormingRecordCreate, DewormingRecordResponse,
    TreatmentRecordCreate, TreatmentRecordResponse,
    VetVisitRecordCreate, VetVisitRecordResponse
)


router = APIRouter(
    prefix="/prevention",
    tags=["Prevention & Veterinary Care"]
)


def _validate_animal_access(db, animal_id: str, current_user: dict):
    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID format."
        )

    animal = db.animals.find_one({"_id": ObjectId(animal_id)})
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    user_id = current_user["sub"]
    user_role = current_user.get("role")
    if user_role == "farmer" and animal.get("owner_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    return animal


# ====================================================
# VACCINATION ENDPOINTS
# ====================================================
@router.post(
    "/vaccinations",
    response_model=VaccinationRecordResponse,
    status_code=status.HTTP_201_CREATED
)
def create_vaccination_record(
    record: VaccinationRecordCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    animal = _validate_animal_access(db, record.animal_id, current_user)

    now = datetime.now(timezone.utc)
    new_doc = {
        "animal_id": record.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": animal["owner_id"],
        "vaccine_name": record.vaccine_name.strip(),
        "administered_date": record.administered_date,
        "next_due_date": record.next_due_date,
        "veterinarian_name": record.veterinarian_name,
        "batch_number": record.batch_number,
        "notes": record.notes,
        "created_at": now
    }

    res = db.vaccinations.insert_one(new_doc)
    new_doc["id"] = str(res.inserted_id)
    new_doc["created_at"] = now.isoformat()
    return VaccinationRecordResponse(**new_doc)


@router.get(
    "/animal/{animal_id}/vaccinations",
    response_model=list[VaccinationRecordResponse]
)
def get_animal_vaccinations(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    _validate_animal_access(db, animal_id, current_user)

    docs = db.vaccinations.find({"animal_id": animal_id}).sort("administered_date", -1)
    results = []
    for d in docs:
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d["created_at"], datetime) else str(d["created_at"])
        results.append(VaccinationRecordResponse(**d))
    return results


# ====================================================
# DEWORMING ENDPOINTS
# ====================================================
@router.post(
    "/deworming",
    response_model=DewormingRecordResponse,
    status_code=status.HTTP_201_CREATED
)
def create_deworming_record(
    record: DewormingRecordCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    animal = _validate_animal_access(db, record.animal_id, current_user)

    now = datetime.now(timezone.utc)
    new_doc = {
        "animal_id": record.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": animal["owner_id"],
        "medicine_name": record.medicine_name.strip(),
        "dosage": record.dosage.strip(),
        "administered_date": record.administered_date,
        "next_due_date": record.next_due_date,
        "veterinarian_name": record.veterinarian_name,
        "notes": record.notes,
        "created_at": now
    }

    res = db.deworming.insert_one(new_doc)
    new_doc["id"] = str(res.inserted_id)
    new_doc["created_at"] = now.isoformat()
    return DewormingRecordResponse(**new_doc)


@router.get(
    "/animal/{animal_id}/deworming",
    response_model=list[DewormingRecordResponse]
)
def get_animal_deworming(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    _validate_animal_access(db, animal_id, current_user)

    docs = db.deworming.find({"animal_id": animal_id}).sort("administered_date", -1)
    results = []
    for d in docs:
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d["created_at"], datetime) else str(d["created_at"])
        results.append(DewormingRecordResponse(**d))
    return results


# ====================================================
# TREATMENT ENDPOINTS
# ====================================================
@router.post(
    "/treatments",
    response_model=TreatmentRecordResponse,
    status_code=status.HTTP_201_CREATED
)
def create_treatment_record(
    record: TreatmentRecordCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    animal = _validate_animal_access(db, record.animal_id, current_user)

    now = datetime.now(timezone.utc)
    new_doc = {
        "animal_id": record.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": animal["owner_id"],
        "condition_diagnosed": record.condition_diagnosed.strip(),
        "medication": record.medication.strip(),
        "dosage": record.dosage.strip(),
        "start_date": record.start_date,
        "end_date": record.end_date,
        "veterinarian_name": record.veterinarian_name,
        "alert_id": record.alert_id,
        "outcome": record.outcome or "ongoing",
        "notes": record.notes,
        "created_at": now
    }

    res = db.treatments.insert_one(new_doc)
    new_doc["id"] = str(res.inserted_id)
    new_doc["created_at"] = now.isoformat()
    return TreatmentRecordResponse(**new_doc)


@router.get(
    "/animal/{animal_id}/treatments",
    response_model=list[TreatmentRecordResponse]
)
def get_animal_treatments(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    _validate_animal_access(db, animal_id, current_user)

    docs = db.treatments.find({"animal_id": animal_id}).sort("start_date", -1)
    results = []
    for d in docs:
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d["created_at"], datetime) else str(d["created_at"])
        results.append(TreatmentRecordResponse(**d))
    return results


# ====================================================
# VETERINARY VISIT ENDPOINTS
# ====================================================
@router.post(
    "/vet-visits",
    response_model=VetVisitRecordResponse,
    status_code=status.HTTP_201_CREATED
)
def create_vet_visit_record(
    record: VetVisitRecordCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    animal = _validate_animal_access(db, record.animal_id, current_user)

    now = datetime.now(timezone.utc)
    new_doc = {
        "animal_id": record.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": animal["owner_id"],
        "veterinarian_name": record.veterinarian_name.strip(),
        "visit_date": record.visit_date,
        "observations": record.observations.strip(),
        "recommendations": record.recommendations.strip(),
        "follow_up_date": record.follow_up_date,
        "alert_id": record.alert_id,
        "created_at": now
    }

    res = db.vet_visits.insert_one(new_doc)
    new_doc["id"] = str(res.inserted_id)
    new_doc["created_at"] = now.isoformat()
    return VetVisitRecordResponse(**new_doc)


@router.get(
    "/animal/{animal_id}/vet-visits",
    response_model=list[VetVisitRecordResponse]
)
def get_animal_vet_visits(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    db = get_database()
    _validate_animal_access(db, animal_id, current_user)

    docs = db.vet_visits.find({"animal_id": animal_id}).sort("visit_date", -1)
    results = []
    for d in docs:
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d["created_at"], datetime) else str(d["created_at"])
        results.append(VetVisitRecordResponse(**d))
    return results


# ====================================================
# PREVENTIVE REMINDERS
# ====================================================
@router.get(
    "/reminders",
    status_code=status.HTTP_200_OK
)
def get_preventive_reminders(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get all upcoming preventive tasks (vaccinations, deworming, follow-ups)
    for the user's livestock.
    """
    db = get_database()
    user_id = current_user["sub"]
    user_role = current_user.get("role")

    query = {}
    if user_role == "farmer":
        query["owner_id"] = user_id

    # Find vaccinations with next_due_date
    vaccs = list(db.vaccinations.find({**query, "next_due_date": {"$ne": None}}).limit(20))
    deworms = list(db.deworming.find({**query, "next_due_date": {"$ne": None}}).limit(20))
    visits = list(db.vet_visits.find({**query, "follow_up_date": {"$ne": None}}).limit(20))

    reminders = []
    for v in vaccs:
        reminders.append({
            "type": "vaccination",
            "title": f"Vaccination Due: {v['vaccine_name']}",
            "due_date": v["next_due_date"],
            "animal_id": v["animal_id"]
        })
    for d in deworms:
        reminders.append({
            "type": "deworming",
            "title": f"Deworming Due: {d['medicine_name']}",
            "due_date": d["next_due_date"],
            "animal_id": d["animal_id"]
        })
    for vs in visits:
        reminders.append({
            "type": "vet_visit",
            "title": f"Vet Follow-up with Dr. {vs['veterinarian_name']}",
            "due_date": vs["follow_up_date"],
            "animal_id": vs["animal_id"]
        })

    return sorted(reminders, key=lambda x: str(x.get("due_date", "")), reverse=False)

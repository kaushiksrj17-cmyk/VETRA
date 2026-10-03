"""
backend/app/services/telemedicine_service.py
============================================
VETRA Phase 12 — Telemedicine Consultation & Clinical Collaboration Service.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid
from bson import ObjectId

from app.database import get_database
from app.schemas.telemedicine import (
    TELEMEDICINE_SAFETY_NOTICE,
    ClinicalNoteItem,
)


def ensure_telemedicine_indexes(db=None):
    """Ensure indexes on the telemedicine_consultations collection."""
    if db is None:
        db = get_database()
    try:
        db.telemedicine_consultations.create_index("consultation_id", unique=True)
        db.telemedicine_consultations.create_index("case_id")
        db.telemedicine_consultations.create_index("animal_id")
        db.telemedicine_consultations.create_index("farm_id")
        db.telemedicine_consultations.create_index("farmer_id")
        db.telemedicine_consultations.create_index("veterinarian_id")
        db.telemedicine_consultations.create_index("status")
        db.telemedicine_consultations.create_index("scheduled_at")
        db.telemedicine_consultations.create_index([("created_at", -1)])
    except Exception:
        pass


def _generate_consultation_id(db) -> str:
    """Generate unique human-readable ID: CONS-YYYY-XXXX."""
    year = datetime.now(timezone.utc).year
    count = db.telemedicine_consultations.count_documents({})
    candidate_num = count + 1
    while True:
        candidate_str = f"CONS-{year}-{candidate_num:04d}"
        if not db.telemedicine_consultations.find_one({"consultation_id": candidate_str}):
            return candidate_str
        candidate_num += 1


def _serialize_consultation(item: dict, db=None) -> dict[str, Any]:
    """Serialize MongoDB consultation document."""
    if not item:
        return {}
    if db is None:
        db = get_database()

    # Look up names for display
    animal_tag = item.get("animal_tag")
    animal_name = item.get("animal_name")
    farm_name = item.get("farm_name")
    farmer_name = item.get("farmer_name")
    case_number = item.get("case_number")

    animal_id = str(item.get("animal_id", ""))
    farm_id = str(item.get("farm_id", ""))
    case_id = str(item.get("case_id", "")) if item.get("case_id") else None

    if not animal_tag and animal_id and ObjectId.is_valid(animal_id):
        anim = db.animals.find_one({"_id": ObjectId(animal_id)})
        if anim:
            animal_tag = anim.get("tag_id")
            animal_name = anim.get("name")
            if not farm_id and anim.get("farm_id"):
                farm_id = str(anim.get("farm_id"))

    if not farm_name and farm_id and ObjectId.is_valid(farm_id):
        f = db.farms.find_one({"_id": ObjectId(farm_id)})
        if f:
            farm_name = f.get("name")

    if case_id and not case_number and ObjectId.is_valid(case_id):
        c = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
        if c:
            case_number = c.get("case_number")

    return {
        "id": str(item.get("_id", "")),
        "consultation_id": item.get("consultation_id", "CONS-UNKNOWN"),
        "case_id": case_id,
        "case_number": case_number,
        "animal_id": animal_id,
        "animal_tag": animal_tag,
        "animal_name": animal_name,
        "farm_id": farm_id,
        "farm_name": farm_name,
        "farmer_id": str(item.get("farmer_id", "")),
        "farmer_name": farmer_name,
        "veterinarian_id": str(item.get("veterinarian_id")) if item.get("veterinarian_id") else None,
        "veterinarian_name": item.get("veterinarian_name"),
        "mode": item.get("mode", "telemedicine"),
        "status": item.get("status", "requested"),
        "scheduled_at": item.get("scheduled_at"),
        "started_at": item.get("started_at"),
        "ended_at": item.get("ended_at"),
        "chief_complaint": item.get("chief_complaint", ""),
        "clinical_summary": item.get("clinical_summary"),
        "visual_evidence_ids": item.get("visual_evidence_ids", []),
        "health_reading_ids": item.get("health_reading_ids", []),
        "predictive_assessment_ids": item.get("predictive_assessment_ids", []),
        "surveillance_context": item.get("surveillance_context"),
        "clinical_notes": item.get("clinical_notes", []),
        "recommendations": item.get("recommendations"),
        "follow_up_date": item.get("follow_up_date"),
        "follow_up_reason": item.get("follow_up_reason"),
        "safety_notice": item.get("safety_notice", TELEMEDICINE_SAFETY_NOTICE),
        "created_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": item.get("updated_at", datetime.now(timezone.utc).isoformat()),
    }


def create_consultation(user_info: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new telemedicine consultation request.
    Farmers can request consultations for their own animals; vets/admins can schedule directly.
    """
    db = get_database()
    ensure_telemedicine_indexes(db)
    now = datetime.now(timezone.utc).isoformat()

    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()
    user_name = user_info.get("full_name") or user_info.get("name") or "User"

    animal_id = payload.get("animal_id")
    if not animal_id or not ObjectId.is_valid(animal_id):
        raise ValueError("Valid animal_id is required.")

    animal = db.animals.find_one({"_id": ObjectId(animal_id)})
    if not animal:
        raise ValueError(f"Animal '{animal_id}' was not found.")

    farm_id = payload.get("farm_id") or str(animal.get("farm_id", ""))
    farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else None

    # Farmer ownership verification: farmers can only request for their own farm
    if user_role == "farmer":
        farmer_farms = list(db.farms.find({"owner_id": user_id}))
        farmer_farm_ids = [str(f["_id"]) for f in farmer_farms]
        if farm_id not in farmer_farm_ids:
            raise PermissionError("Access denied. You may only request consultations for your own livestock.")

    consultation_id = _generate_consultation_id(db)

    # Determine initial status
    init_status = "requested"
    if payload.get("scheduled_at"):
        init_status = "scheduled"
    if payload.get("veterinarian_id") and user_role in ("veterinarian", "admin"):
        init_status = "accepted"

    # Link or auto-create corresponding veterinary case
    case_id = payload.get("case_id")
    case_number = None
    if case_id and ObjectId.is_valid(case_id):
        c = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
        if c:
            case_number = c.get("case_number")
            # Update case status to teleconsultation if active
            db.veterinary_cases.update_one(
                {"_id": ObjectId(case_id)},
                {"$set": {"status": "teleconsultation", "updated_at": now}}
            )

    vet_name = payload.get("veterinarian_name")
    if payload.get("veterinarian_id") and not vet_name:
        v_user = db.users.find_one({"_id": ObjectId(payload["veterinarian_id"])}) if ObjectId.is_valid(payload["veterinarian_id"]) else None
        if v_user:
            vet_name = v_user.get("full_name")

    doc = {
        "consultation_id": consultation_id,
        "case_id": case_id,
        "case_number": case_number,
        "animal_id": animal_id,
        "animal_tag": animal.get("tag_id"),
        "animal_name": animal.get("name"),
        "farm_id": farm_id,
        "farm_name": farm.get("name") if farm else "Farm Facility",
        "farmer_id": user_id if user_role == "farmer" else (farm.get("owner_id", user_id) if farm else user_id),
        "farmer_name": user_name if user_role == "farmer" else "Livestock Owner",
        "veterinarian_id": payload.get("veterinarian_id"),
        "veterinarian_name": vet_name,
        "mode": payload.get("mode", "telemedicine"),
        "status": init_status,
        "scheduled_at": payload.get("scheduled_at"),
        "started_at": None,
        "ended_at": None,
        "chief_complaint": payload["chief_complaint"],
        "clinical_summary": payload.get("clinical_summary"),
        "visual_evidence_ids": payload.get("visual_evidence_ids", []),
        "health_reading_ids": payload.get("health_reading_ids", []),
        "predictive_assessment_ids": payload.get("predictive_assessment_ids", []),
        "surveillance_context": payload.get("surveillance_context"),
        "clinical_notes": [],
        "recommendations": None,
        "follow_up_date": None,
        "follow_up_reason": None,
        "safety_notice": TELEMEDICINE_SAFETY_NOTICE,
        "created_at": now,
        "updated_at": now,
    }

    res = db.telemedicine_consultations.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Audit log
    db.audit_logs.insert_one({
        "action": "consultation_created",
        "user_id": user_id,
        "user_role": user_role,
        "consultation_id": consultation_id,
        "animal_id": animal_id,
        "farm_id": farm_id,
        "status": init_status,
        "timestamp": now,
    })

    return _serialize_consultation(doc, db)


def get_consultation(consultation_id: str, user_info: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Retrieve consultation document with RBAC verification."""
    db = get_database()
    query = {"$or": [{"consultation_id": consultation_id}]}
    if ObjectId.is_valid(consultation_id):
        query["$or"].append({"_id": ObjectId(consultation_id)})

    doc = db.telemedicine_consultations.find_one(query)
    if not doc:
        return None

    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()

    # RBAC: farmers can only see their own consultations
    if user_role == "farmer":
        farmer_id = str(doc.get("farmer_id", ""))
        farm_id = str(doc.get("farm_id", ""))
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        if user_id != farmer_id and farm_id not in farmer_farms:
            raise PermissionError("Access denied. You may only view your own farm consultations.")

    return _serialize_consultation(doc, db)


def list_consultations(
    user_info: dict[str, Any],
    farm_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    veterinarian_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> list[dict[str, Any]]:
    """List consultations with RBAC filtering."""
    db = get_database()
    ensure_telemedicine_indexes(db)

    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()

    query: dict[str, Any] = {}

    if user_role == "farmer":
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        query["$or"] = [{"farmer_id": user_id}, {"farm_id": {"$in": farmer_farms}}]
    elif user_role == "veterinarian":
        if veterinarian_id:
            query["veterinarian_id"] = veterinarian_id
    # Admin and institutional officer can view across farms

    if farm_id and farm_id != "all":
        query["farm_id"] = farm_id
    if animal_id and animal_id != "all":
        query["animal_id"] = animal_id
    if status and status != "all":
        query["status"] = status

    cursor = db.telemedicine_consultations.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [_serialize_consultation(c, db) for c in cursor]


def accept_consultation(consultation_id: str, user_info: dict[str, Any]) -> dict[str, Any]:
    """Accept and claim a requested consultation (Veterinarian / Admin only)."""
    db = get_database()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "Veterinarian"
    now = datetime.now(timezone.utc).isoformat()

    doc = db.telemedicine_consultations.find_one({"consultation_id": consultation_id})
    if not doc and ObjectId.is_valid(consultation_id):
        doc = db.telemedicine_consultations.find_one({"_id": ObjectId(consultation_id)})
    if not doc:
        raise ValueError(f"Consultation '{consultation_id}' not found.")

    db.telemedicine_consultations.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": "accepted",
                "veterinarian_id": user_id,
                "veterinarian_name": user_name,
                "updated_at": now,
            }
        }
    )

    # Update associated case if present
    if doc.get("case_id") and ObjectId.is_valid(doc["case_id"]):
        db.veterinary_cases.update_one(
            {"_id": ObjectId(doc["case_id"])},
            {
                "$set": {
                    "assigned_veterinarian_id": user_id,
                    "assigned_veterinarian_name": user_name,
                    "status": "assigned",
                    "updated_at": now,
                }
            }
        )

    # Audit log
    db.audit_logs.insert_one({
        "action": "consultation_accepted",
        "user_id": user_id,
        "user_role": user_info.get("role", "veterinarian"),
        "consultation_id": doc["consultation_id"],
        "timestamp": now,
    })

    updated = db.telemedicine_consultations.find_one({"_id": doc["_id"]})
    return _serialize_consultation(updated, db)


def start_consultation(consultation_id: str, user_info: dict[str, Any]) -> dict[str, Any]:
    """Transition consultation to in_progress."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()

    doc = db.telemedicine_consultations.find_one({"consultation_id": consultation_id})
    if not doc and ObjectId.is_valid(consultation_id):
        doc = db.telemedicine_consultations.find_one({"_id": ObjectId(consultation_id)})
    if not doc:
        raise ValueError(f"Consultation '{consultation_id}' not found.")

    db.telemedicine_consultations.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": "in_progress",
                "started_at": doc.get("started_at") or now,
                "updated_at": now,
            }
        }
    )
    updated = db.telemedicine_consultations.find_one({"_id": doc["_id"]})
    return _serialize_consultation(updated, db)


def complete_consultation(
    consultation_id: str,
    user_info: dict[str, Any],
    recommendations: str,
    final_assessment: Optional[str] = None,
    follow_up_date: Optional[str] = None,
    follow_up_reason: Optional[str] = None
) -> dict[str, Any]:
    """Complete consultation with clinician recommendations and follow-up."""
    db = get_database()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    now = datetime.now(timezone.utc).isoformat()

    doc = db.telemedicine_consultations.find_one({"consultation_id": consultation_id})
    if not doc and ObjectId.is_valid(consultation_id):
        doc = db.telemedicine_consultations.find_one({"_id": ObjectId(consultation_id)})
    if not doc:
        raise ValueError(f"Consultation '{consultation_id}' not found.")

    status_target = "follow_up_required" if follow_up_date else "completed"

    update_payload = {
        "status": status_target,
        "ended_at": now,
        "recommendations": recommendations,
        "updated_at": now,
    }
    if final_assessment:
        update_payload["clinical_summary"] = final_assessment
    if follow_up_date:
        update_payload["follow_up_date"] = follow_up_date
    if follow_up_reason:
        update_payload["follow_up_reason"] = follow_up_reason

    db.telemedicine_consultations.update_one({"_id": doc["_id"]}, {"$set": update_payload})

    # Update associated case
    if doc.get("case_id") and ObjectId.is_valid(doc["case_id"]):
        case_update: dict[str, Any] = {
            "recommendations": recommendations,
            "updated_at": now,
        }
        if final_assessment:
            case_update["clinical_findings"] = final_assessment
        if follow_up_date:
            case_update["follow_up_date"] = follow_up_date
            case_update["status"] = "follow_up"
        else:
            case_update["status"] = "resolved"
        db.veterinary_cases.update_one({"_id": ObjectId(doc["case_id"])}, {"$set": case_update})

    # Audit log
    db.audit_logs.insert_one({
        "action": "consultation_completed",
        "user_id": user_id,
        "consultation_id": doc["consultation_id"],
        "has_follow_up": bool(follow_up_date),
        "timestamp": now,
    })

    updated = db.telemedicine_consultations.find_one({"_id": doc["_id"]})
    return _serialize_consultation(updated, db)


def cancel_consultation(consultation_id: str, user_info: dict[str, Any], reason: str) -> dict[str, Any]:
    """Cancel a consultation request."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()

    doc = db.telemedicine_consultations.find_one({"consultation_id": consultation_id})
    if not doc and ObjectId.is_valid(consultation_id):
        doc = db.telemedicine_consultations.find_one({"_id": ObjectId(consultation_id)})
    if not doc:
        raise ValueError(f"Consultation '{consultation_id}' not found.")

    db.telemedicine_consultations.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "cancelled", "clinical_summary": f"Cancelled: {reason}", "updated_at": now}}
    )
    updated = db.telemedicine_consultations.find_one({"_id": doc["_id"]})
    return _serialize_consultation(updated, db)


def add_clinical_note(
    consultation_id: str,
    user_info: dict[str, Any],
    note_payload: dict[str, Any]
) -> dict[str, Any]:
    """
    Append a clinical or observation note to a consultation.
    CLINICAL INTEGRITY RULE:
    - Farmers can add 'farmer_observation', 'subjective' history, or 'farmer_symptoms'.
    - Farmers CANNOT add or edit 'assessment', 'recommendations', or 'veterinary_clinical_note'.
    """
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()
    user_name = user_info.get("full_name") or user_info.get("name") or "User"

    doc = db.telemedicine_consultations.find_one({"consultation_id": consultation_id})
    if not doc and ObjectId.is_valid(consultation_id):
        doc = db.telemedicine_consultations.find_one({"_id": ObjectId(consultation_id)})
    if not doc:
        raise ValueError(f"Consultation '{consultation_id}' not found.")

    # Clinical RBAC enforcement
    raw_text = note_payload.get("note_text") or ""
    if user_role == "farmer":
        if note_payload.get("assessment") or note_payload.get("objective"):
            raise PermissionError("Clinical assessments and objective medical findings are reserved strictly for veterinarians.")
        note_type = "farmer_observation"
        assessment = None
        recommendations = None
        subjective = None
        objective = None
        farmer_symptoms = note_payload.get("farmer_symptoms") or raw_text
    else:
        note_type = note_payload.get("note_type") or "veterinary_clinical_note"
        assessment = note_payload.get("assessment")
        recommendations = note_payload.get("recommendations")
        subjective = note_payload.get("subjective") or raw_text
        objective = note_payload.get("objective")
        farmer_symptoms = note_payload.get("farmer_symptoms")

    note_item = {
        "note_id": f"note_{uuid.uuid4().hex[:8]}",
        "author_id": user_id,
        "author_name": user_name,
        "author_role": user_role,
        "note_type": note_type,
        "note_text": raw_text,
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "recommendations": recommendations,
        "farmer_symptoms": farmer_symptoms,
        "created_at": now,
    }

    db.telemedicine_consultations.update_one(
        {"_id": doc["_id"]},
        {
            "$push": {"clinical_notes": note_item},
            "$set": {"updated_at": now}
        }
    )

    # Audit log
    db.audit_logs.insert_one({
        "action": "clinical_note_added",
        "user_id": user_id,
        "user_role": user_role,
        "consultation_id": doc["consultation_id"],
        "note_id": note_item["note_id"],
        "timestamp": now,
    })

    return note_item


def get_clinical_notes(consultation_id: str, user_info: dict[str, Any]) -> list[dict[str, Any]]:
    """Retrieve all clinical notes recorded in a consultation."""
    consultation = get_consultation(consultation_id, user_info)
    if not consultation:
        raise ValueError(f"Consultation '{consultation_id}' not found.")
    return consultation.get("clinical_notes", [])


class TelemedicineService:
    def create_consultation(self, user_info, payload):
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        return create_consultation(user_info, data)

    def get_consultation(self, consultation_id, user_info=None):
        return get_consultation(consultation_id, user_info or {"role": "admin"})

    def list_consultations(self, user_info=None, status=None, case_id=None, animal_id=None, farm_id=None, veterinarian_id=None, skip=0, limit=50):
        return list_consultations(user_info or {"role": "admin"}, status=status, case_id=case_id, animal_id=animal_id, farm_id=farm_id, veterinarian_id=veterinarian_id, limit=limit, skip=skip)

    def accept_consultation(self, consultation_id, user_info, scheduled_at=None, notes=None):
        return accept_consultation(consultation_id, user_info, scheduled_at=scheduled_at, notes=notes)

    def start_consultation(self, consultation_id, user_info):
        return start_consultation(consultation_id, user_info)

    def complete_consultation(self, consultation_id, user_info, **kwargs):
        return complete_consultation(consultation_id, user_info, **kwargs)

    def cancel_consultation(self, consultation_id, user_info, reason=None):
        return cancel_consultation(consultation_id, user_info, reason=reason)

    def add_clinical_note(self, consultation_id, user_info, note_data):
        data = note_data.model_dump() if hasattr(note_data, "model_dump") else note_data
        return add_clinical_note(consultation_id, user_info, data)

    def get_clinical_notes(self, consultation_id, user_info=None):
        return get_clinical_notes(consultation_id, user_info or {"role": "admin"})


telemedicine_service = TelemedicineService()


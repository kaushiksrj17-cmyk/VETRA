from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.veterinary_case import (
    CasePriority,
    CaseStatus,
    CaseType,
    VeterinaryCaseAssign,
    VeterinaryCaseCreate,
    VeterinaryCaseResolve,
    VeterinaryCaseResponse,
    VeterinaryCaseStatusUpdate,
    VeterinaryCaseUpdate,
)


router = APIRouter(
    prefix="/veterinary-cases",
    tags=["Veterinary Case Management"]
)


def ensure_case_indexes():
    """
    Ensure essential MongoDB indexes exist for the veterinary_cases collection.
    """
    try:
        db = get_database()
        db.veterinary_cases.create_index("case_number", unique=True)
        db.veterinary_cases.create_index("animal_id")
        db.veterinary_cases.create_index("farm_id")
        db.veterinary_cases.create_index("owner_id")
        db.veterinary_cases.create_index("assigned_veterinarian_id")
        db.veterinary_cases.create_index("status")
        db.veterinary_cases.create_index("priority")
        db.veterinary_cases.create_index("alert_id")
        db.veterinary_cases.create_index([("created_at", -1)])
    except Exception:
        pass


def _generate_case_number(db) -> str:
    """
    Generate a unique human-readable case number: CASE-YYYY-XXXX.
    """
    year = datetime.now(timezone.utc).year
    count = db.veterinary_cases.count_documents({})
    candidate_num = count + 1

    while True:
        candidate_str = f"CASE-{year}-{candidate_num:04d}"
        if not db.veterinary_cases.find_one({"case_number": candidate_str}):
            return candidate_str
        candidate_num += 1


def serialize_case(item: dict) -> VeterinaryCaseResponse:
    """
    Transform a MongoDB veterinary case document into VeterinaryCaseResponse.
    """
    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")

    updated_at = item.get("updated_at")
    updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at or created_at_str)

    closed_at = item.get("closed_at")
    closed_at_str = closed_at.isoformat() if isinstance(closed_at, datetime) else (str(closed_at) if closed_at else None)

    return VeterinaryCaseResponse(
        id=str(item["_id"]),
        case_number=item.get("case_number", "CASE-UNKNOWN"),
        animal_id=str(item.get("animal_id", "")),
        farm_id=str(item.get("farm_id", "")),
        owner_id=str(item.get("owner_id", "")),
        title=item.get("title", ""),
        description=item.get("description"),
        case_type=item.get("case_type", "routine_checkup"),
        priority=item.get("priority", "medium"),
        status=item.get("status", "open"),
        source=item.get("source", "manual"),
        source_type=item.get("source_type"),
        source_id=item.get("source_id"),
        alert_id=str(item["alert_id"]) if item.get("alert_id") else None,
        health_risk_score=item.get("health_risk_score"),
        disease_risk_level=item.get("disease_risk_level"),
        early_warning_level=item.get("early_warning_level"),
        assigned_veterinarian_id=str(item["assigned_veterinarian_id"]) if item.get("assigned_veterinarian_id") else None,
        assigned_veterinarian_name=item.get("assigned_veterinarian_name"),
        clinical_findings=item.get("clinical_findings"),
        diagnosis=item.get("diagnosis"),
        treatment_plan=item.get("treatment_plan"),
        medications=item.get("medications", []),
        recommendations=item.get("recommendations"),
        follow_up_date=item.get("follow_up_date"),
        timeline=item.get("timeline", []),
        created_at=created_at_str,
        updated_at=updated_at_str,
        closed_at=closed_at_str
    )


@router.post(
    "",
    response_model=VeterinaryCaseResponse,
    status_code=status.HTTP_201_CREATED
)
def create_veterinary_case(
    payload: VeterinaryCaseCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Create a new veterinary case.
    """
    ensure_case_indexes()
    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role", "farmer")
    user_name = current_user.get("full_name") or current_user.get("email", "User")

    # Validate animal
    if not ObjectId.is_valid(payload.animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID format."
        )

    animal = db.animals.find_one({"_id": ObjectId(payload.animal_id)})
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    farm_id = str(animal.get("farm_id", ""))
    owner_id = str(animal.get("owner_id", ""))

    # Farmer permission check: must own the animal
    if user_role == "farmer" and owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create cases for your own animals."
        )

    # Check alert duplicate if alert_id is provided
    if payload.alert_id:
        existing = db.veterinary_cases.find_one({
            "alert_id": payload.alert_id,
            "status": {"$nin": ["resolved", "closed"]}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A veterinary case already exists for this alert ({existing.get('case_number')})."
            )

    now = datetime.now(timezone.utc)
    case_number = _generate_case_number(db)

    # Fetch AI health metrics if not provided
    health_risk_score = payload.health_risk_score
    disease_risk_level = payload.disease_risk_level
    early_warning_level = payload.early_warning_level

    if health_risk_score is None or disease_risk_level is None:
        recent_reading = db.health_readings.find_one(
            {"animal_id": payload.animal_id},
            sort=[("recorded_at", -1)]
        )
        if recent_reading:
            if health_risk_score is None:
                health_risk_score = recent_reading.get("risk_score")
            if disease_risk_level is None:
                disease_risk_level = recent_reading.get("risk_category")

    initial_status = "assigned" if payload.assigned_veterinarian_id else "open"

    timeline_events = [
        {
            "event": "case_created",
            "title": "Case Opened",
            "description": f"Veterinary case opened via {payload.source}. Initial priority: {payload.priority.upper()}.",
            "performed_by": user_id,
            "performed_by_name": user_name,
            "performed_by_role": user_role,
            "timestamp": now.isoformat()
        }
    ]

    if payload.assigned_veterinarian_id:
        timeline_events.append({
            "event": "case_assigned",
            "title": "Case Assigned",
            "description": f"Assigned to {payload.assigned_veterinarian_name or 'Veterinarian'}.",
            "performed_by": user_id,
            "performed_by_name": user_name,
            "performed_by_role": user_role,
            "timestamp": now.isoformat()
        })

    doc = {
        "case_number": case_number,
        "animal_id": payload.animal_id,
        "farm_id": farm_id,
        "owner_id": owner_id,
        "title": payload.title.strip(),
        "description": payload.description.strip() if payload.description else None,
        "case_type": payload.case_type,
        "priority": payload.priority,
        "status": initial_status,
        "source": payload.source,
        "source_type": payload.source_type or payload.source,
        "source_id": payload.source_id or payload.alert_id,
        "alert_id": payload.alert_id,
        "health_risk_score": health_risk_score,
        "disease_risk_level": disease_risk_level,
        "early_warning_level": early_warning_level,
        "assigned_veterinarian_id": payload.assigned_veterinarian_id,
        "assigned_veterinarian_name": payload.assigned_veterinarian_name,
        "clinical_findings": payload.clinical_findings,
        "diagnosis": payload.diagnosis,
        "treatment_plan": payload.treatment_plan,
        "medications": [m.model_dump() for m in payload.medications],
        "recommendations": payload.recommendations,
        "follow_up_date": payload.follow_up_date,
        "timeline": timeline_events,
        "created_at": now,
        "updated_at": now,
        "closed_at": None
    }

    insert_result = db.veterinary_cases.insert_one(doc)
    doc["_id"] = insert_result.inserted_id

    return serialize_case(doc)


@router.get(
    "",
    response_model=list[VeterinaryCaseResponse]
)
def get_veterinary_cases(
    status_filter: Optional[CaseStatus] = Query(default=None, alias="status"),
    priority: Optional[CasePriority] = Query(default=None),
    case_type: Optional[CaseType] = Query(default=None),
    animal_id: Optional[str] = Query(default=None),
    veterinarian_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve veterinary cases matching filters and user permissions.
    """
    ensure_case_indexes()
    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role", "farmer")

    query = {}

    # Farmers only see cases for their owned animals/farms
    if user_role == "farmer":
        query["owner_id"] = user_id

    if status_filter:
        query["status"] = status_filter

    if priority:
        query["priority"] = priority

    if case_type:
        query["case_type"] = case_type

    if animal_id:
        query["animal_id"] = animal_id

    if veterinarian_id:
        query["assigned_veterinarian_id"] = veterinarian_id

    cursor = db.veterinary_cases.find(query).sort("created_at", -1).limit(limit)

    return [serialize_case(doc) for doc in cursor]


@router.get(
    "/animal/{animal_id}",
    response_model=list[VeterinaryCaseResponse]
)
def get_cases_for_animal(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve all veterinary cases for a specific animal.
    """
    ensure_case_indexes()
    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role", "farmer")

    query = {"animal_id": animal_id}
    if user_role == "farmer":
        query["owner_id"] = user_id

    cursor = db.veterinary_cases.find(query).sort("created_at", -1)
    return [serialize_case(doc) for doc in cursor]


@router.get(
    "/veterinarian/{veterinarian_id}",
    response_model=list[VeterinaryCaseResponse]
)
def get_cases_for_veterinarian(
    veterinarian_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve cases assigned to a specific veterinarian.
    """
    ensure_case_indexes()
    db = get_database()

    cursor = db.veterinary_cases.find(
        {"assigned_veterinarian_id": veterinarian_id}
    ).sort("created_at", -1)

    return [serialize_case(doc) for doc in cursor]


@router.get(
    "/veterinarians/list"
)
def list_veterinarians(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List registered veterinarians and administrators for case assignment.
    """
    db = get_database()
    vets = db.users.find(
        {"role": {"$in": ["veterinarian", "admin"]}},
        {"password_hash": 0}
    )
    return [
        {
            "id": str(v["_id"]),
            "full_name": v.get("full_name", "Veterinarian"),
            "email": v.get("email", ""),
            "role": v.get("role", "veterinarian")
        }
        for v in vets
    ]


@router.get(
    "/{case_id}",
    response_model=VeterinaryCaseResponse
)
def get_veterinary_case(
    case_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve a specific veterinary case by ID.
    """
    ensure_case_indexes()
    db = get_database()

    if not ObjectId.is_valid(case_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format."
        )

    case_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veterinary case not found."
        )

    user_id = current_user["sub"]
    user_role = current_user.get("role", "farmer")

    if user_role == "farmer" and str(case_doc.get("owner_id")) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return serialize_case(case_doc)


@router.put(
    "/{case_id}",
    response_model=VeterinaryCaseResponse
)
def update_veterinary_case(
    case_id: str,
    payload: VeterinaryCaseUpdate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Update clinical findings, diagnosis, treatment plan, or notes.
    """
    ensure_case_indexes()
    db = get_database()

    if not ObjectId.is_valid(case_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format."
        )

    case_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veterinary case not found."
        )

    user_id = current_user["sub"]
    user_role = current_user.get("role", "farmer")
    user_name = current_user.get("full_name") or current_user.get("email", "User")

    # Farmer restriction: farmers cannot update clinical fields
    if user_role == "farmer":
        if str(case_doc.get("owner_id")) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
        if (
            payload.clinical_findings is not None
            or payload.diagnosis is not None
            or payload.treatment_plan is not None
            or payload.medications is not None
            or payload.follow_up_date is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Farmers cannot update medical or clinical treatment fields."
            )

    now = datetime.now(timezone.utc)
    update_data = {"updated_at": now}
    timeline_desc = []

    if payload.title is not None:
        update_data["title"] = payload.title.strip()
    if payload.description is not None:
        update_data["description"] = payload.description.strip()
    if payload.priority is not None:
        update_data["priority"] = payload.priority
        timeline_desc.append(f"Priority changed to {payload.priority.upper()}")
    if payload.clinical_findings is not None:
        update_data["clinical_findings"] = payload.clinical_findings
        timeline_desc.append("Clinical findings updated")
    if payload.diagnosis is not None:
        update_data["diagnosis"] = payload.diagnosis
        timeline_desc.append("Diagnosis updated")
    if payload.treatment_plan is not None:
        update_data["treatment_plan"] = payload.treatment_plan
        timeline_desc.append("Treatment plan updated")
    if payload.medications is not None:
        update_data["medications"] = [m.model_dump() for m in payload.medications]
        timeline_desc.append(f"{len(payload.medications)} medication(s) prescribed")
    if payload.recommendations is not None:
        update_data["recommendations"] = payload.recommendations
    if payload.follow_up_date is not None:
        update_data["follow_up_date"] = payload.follow_up_date
        timeline_desc.append(f"Follow-up scheduled for {payload.follow_up_date}")

    if payload.notes:
        timeline_desc.append(f"Note: {payload.notes}")

    timeline_event = {
        "event": "case_updated",
        "title": "Clinical Case Updated",
        "description": "; ".join(timeline_desc) if timeline_desc else "Case details updated.",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "timestamp": now.isoformat()
    }

    db.veterinary_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": update_data,
            "$push": {"timeline": timeline_event}
        }
    )

    updated_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    return serialize_case(updated_doc)


@router.put(
    "/{case_id}/assign",
    response_model=VeterinaryCaseResponse
)
def assign_veterinary_case(
    case_id: str,
    payload: VeterinaryCaseAssign,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Assign a veterinarian to a case. Restricted to Veterinarians and Admins.
    """
    ensure_case_indexes()
    db = get_database()

    if not ObjectId.is_valid(case_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format."
        )

    case_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veterinary case not found."
        )

    vet_name = payload.veterinarian_name
    if not vet_name and ObjectId.is_valid(payload.veterinarian_id):
        vet_user = db.users.find_one({"_id": ObjectId(payload.veterinarian_id)})
        if vet_user:
            vet_name = vet_user.get("full_name") or vet_user.get("email")

    now = datetime.now(timezone.utc)
    new_status = "assigned" if case_doc.get("status") == "open" else case_doc.get("status")

    user_id = current_user["sub"]
    user_name = current_user.get("full_name") or current_user.get("email", "User")
    user_role = current_user.get("role", "veterinarian")

    desc = f"Assigned to {vet_name or payload.veterinarian_id}."
    if payload.notes:
        desc += f" Note: {payload.notes}"

    timeline_event = {
        "event": "case_assigned",
        "title": "Case Assigned",
        "description": desc,
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "timestamp": now.isoformat()
    }

    db.veterinary_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "assigned_veterinarian_id": payload.veterinarian_id,
                "assigned_veterinarian_name": vet_name,
                "status": new_status,
                "updated_at": now
            },
            "$push": {"timeline": timeline_event}
        }
    )

    updated_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    return serialize_case(updated_doc)


@router.put(
    "/{case_id}/status",
    response_model=VeterinaryCaseResponse
)
def update_case_status(
    case_id: str,
    payload: VeterinaryCaseStatusUpdate,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Update the lifecycle status of a veterinary case.
    """
    ensure_case_indexes()
    db = get_database()

    if not ObjectId.is_valid(case_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format."
        )

    case_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veterinary case not found."
        )

    now = datetime.now(timezone.utc)
    user_id = current_user["sub"]
    user_name = current_user.get("full_name") or current_user.get("email", "User")
    user_role = current_user.get("role", "veterinarian")

    update_fields = {
        "status": payload.status,
        "updated_at": now
    }

    if payload.status in ["resolved", "closed"]:
        update_fields["closed_at"] = now

    desc = f"Status changed from {case_doc.get('status', 'unknown').upper()} to {payload.status.upper()}."
    if payload.notes:
        desc += f" Note: {payload.notes}"

    timeline_event = {
        "event": f"status_{payload.status}",
        "title": f"Status: {payload.status.replace('_', ' ').title()}",
        "description": desc,
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "timestamp": now.isoformat()
    }

    db.veterinary_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": update_fields,
            "$push": {"timeline": timeline_event}
        }
    )

    updated_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    return serialize_case(updated_doc)


@router.put(
    "/{case_id}/resolve",
    response_model=VeterinaryCaseResponse
)
def resolve_veterinary_case(
    case_id: str,
    payload: VeterinaryCaseResolve,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Mark a veterinary case as resolved.
    Also resolves linked alert in MongoDB if present.
    """
    ensure_case_indexes()
    db = get_database()

    if not ObjectId.is_valid(case_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format."
        )

    case_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veterinary case not found."
        )

    now = datetime.now(timezone.utc)
    user_id = current_user["sub"]
    user_name = current_user.get("full_name") or current_user.get("email", "User")
    user_role = current_user.get("role", "veterinarian")

    update_fields = {
        "status": "resolved",
        "updated_at": now,
        "closed_at": now
    }

    if payload.final_diagnosis:
        update_fields["diagnosis"] = payload.final_diagnosis.strip()
    if payload.recommendations:
        update_fields["recommendations"] = payload.recommendations.strip()

    desc = payload.resolution_summary or "Case resolved following clinical assessment and intervention."

    timeline_event = {
        "event": "case_resolved",
        "title": "Case Resolved",
        "description": desc,
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "timestamp": now.isoformat()
    }

    db.veterinary_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": update_fields,
            "$push": {"timeline": timeline_event}
        }
    )

    # If linked to an alert, resolve the alert in alerts collection
    alert_id = case_doc.get("alert_id")
    if alert_id and ObjectId.is_valid(alert_id):
        db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "status": "resolved",
                    "resolved_at": now,
                    "resolved_by": user_id
                }
            }
        )

    updated_doc = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
    return serialize_case(updated_doc)

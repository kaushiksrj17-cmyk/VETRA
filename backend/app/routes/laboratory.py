"""
backend/app/routes/laboratory.py
================================
VETRA Phase 12 — Diagnostic Laboratory Results Reference Endpoints.
"""

from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import (
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.laboratory import (
    LaboratoryResultCreate,
    LaboratoryResultResponse,
)


router = APIRouter(
    prefix="/laboratory",
    tags=["Diagnostic Laboratory Results"]
)


def ensure_laboratory_indexes(db=None):
    """Ensure indexes on the laboratory_results collection."""
    if db is None:
        db = get_database()
    try:
        db.laboratory_results.create_index("result_id", unique=True)
        db.laboratory_results.create_index("animal_id")
        db.laboratory_results.create_index("farm_id")
        db.laboratory_results.create_index("case_id")
        db.laboratory_results.create_index("result_status")
        db.laboratory_results.create_index([("created_at", -1)])
    except Exception:
        pass


def _generate_lab_id(db) -> str:
    year = datetime.now(timezone.utc).year
    count = db.laboratory_results.count_documents({})
    candidate_num = count + 1
    while True:
        candidate_str = f"LAB-{year}-{candidate_num:04d}"
        if not db.laboratory_results.find_one({"result_id": candidate_str}):
            return candidate_str
        candidate_num += 1


def _serialize_lab_result(item: dict, db=None) -> dict:
    if not item:
        return {}
    if db is None:
        db = get_database()

    animal_id = str(item.get("animal_id", ""))
    farm_id = str(item.get("farm_id", ""))
    case_id = str(item.get("case_id", "")) if item.get("case_id") else None

    animal_tag = None
    farm_name = None
    case_number = None

    if animal_id and ObjectId.is_valid(animal_id):
        anim = db.animals.find_one({"_id": ObjectId(animal_id)})
        if anim:
            animal_tag = anim.get("tag_id")
            if not farm_id and anim.get("farm_id"):
                farm_id = str(anim.get("farm_id"))

    if farm_id and ObjectId.is_valid(farm_id):
        f = db.farms.find_one({"_id": ObjectId(farm_id)})
        if f:
            farm_name = f.get("name")

    if case_id and ObjectId.is_valid(case_id):
        c = db.veterinary_cases.find_one({"_id": ObjectId(case_id)})
        if c:
            case_number = c.get("case_number")

    return {
        "id": str(item.get("_id", "")),
        "result_id": item.get("result_id", "LAB-UNKNOWN"),
        "case_id": case_id,
        "case_number": case_number,
        "animal_id": animal_id,
        "animal_tag": animal_tag,
        "farm_id": farm_id,
        "farm_name": farm_name,
        "test_name": item.get("test_name", "Diagnostic Screen"),
        "laboratory_name": item.get("laboratory_name", "Veterinary Diagnostic Lab"),
        "sample_type": item.get("sample_type", "Blood Serum"),
        "collection_date": item.get("collection_date"),
        "result_status": item.get("result_status", "not_available"),
        "result_summary": item.get("result_summary"),
        "reference_document": item.get("reference_document"),
        "document_hash": item.get("document_hash"),
        "verified": bool(item.get("verified", False)),
        "created_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
    }


@router.post(
    "/results",
    response_model=LaboratoryResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register diagnostic laboratory test reference"
)
def create_laboratory_result(
    payload: LaboratoryResultCreate,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Registers a laboratory test record.
    Clinical safety: Does not fabricate test results; default is 'not_available' or 'pending'.
    Only licensed clinicians or administrators may document laboratory references.
    """
    db = get_database()
    ensure_laboratory_indexes(db)
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(current_user.get("id") or current_user.get("_id") or current_user.get("sub") or "")

    animal_id = payload.animal_id
    if not ObjectId.is_valid(animal_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid animal ID format.")

    animal = db.animals.find_one({"_id": ObjectId(animal_id)})
    if not animal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Animal not found.")

    farm_id = payload.farm_id or str(animal.get("farm_id", ""))
    result_id = _generate_lab_id(db)

    doc = {
        "result_id": result_id,
        "case_id": payload.case_id,
        "animal_id": animal_id,
        "farm_id": farm_id,
        "test_name": payload.test_name,
        "laboratory_name": payload.laboratory_name,
        "sample_type": payload.sample_type,
        "collection_date": payload.collection_date or now[:10],
        "result_status": payload.result_status,
        "result_summary": payload.result_summary,
        "reference_document": payload.reference_document,
        "document_hash": payload.document_hash,
        "verified": payload.verified,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }

    res = db.laboratory_results.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Audit log
    db.audit_logs.insert_one({
        "action": "laboratory_result_added",
        "user_id": user_id,
        "result_id": result_id,
        "animal_id": animal_id,
        "test_name": payload.test_name,
        "result_status": payload.result_status,
        "timestamp": now,
    })

    return _serialize_lab_result(doc, db)


@router.get(
    "/results",
    response_model=list[LaboratoryResultResponse],
    summary="List laboratory test results with RBAC"
)
def list_laboratory_results(
    animal_id: Optional[str] = Query(None, description="Optional animal ID filter"),
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    case_id: Optional[str] = Query(None, description="Optional case ID filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional result status filter"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Lists laboratory results respecting cross-farm isolation."""
    db = get_database()
    ensure_laboratory_indexes(db)
    user_id = str(current_user.get("id") or current_user.get("_id") or current_user.get("sub") or "")
    user_role = str(current_user.get("role", "farmer")).lower()

    query = {}
    if user_role == "farmer":
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        query["farm_id"] = {"$in": farmer_farms}

    if farm_id and farm_id != "all":
        query["farm_id"] = farm_id
    if animal_id and animal_id != "all":
        query["animal_id"] = animal_id
    if case_id and case_id != "all":
        query["case_id"] = case_id
    if status_filter and status_filter != "all":
        query["result_status"] = status_filter

    cursor = db.laboratory_results.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [_serialize_lab_result(c, db) for c in cursor]


@router.get(
    "/results/{result_id}",
    response_model=LaboratoryResultResponse,
    summary="Get laboratory result details"
)
def get_laboratory_result(
    result_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Retrieves specific laboratory test result record with RBAC validation."""
    db = get_database()
    query = {"$or": [{"result_id": result_id}]}
    if ObjectId.is_valid(result_id):
        query["$or"].append({"_id": ObjectId(result_id)})

    doc = db.laboratory_results.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory result '{result_id}' was not found."
        )

    user_id = str(current_user.get("id") or current_user.get("_id") or current_user.get("sub") or "")
    user_role = str(current_user.get("role", "farmer")).lower()

    if user_role == "farmer":
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        if str(doc.get("farm_id")) not in farmer_farms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You may only view diagnostic results for your own farm."
            )

    return _serialize_lab_result(doc, db)

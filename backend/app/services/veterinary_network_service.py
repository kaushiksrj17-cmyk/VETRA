"""
backend/app/services/veterinary_network_service.py
==================================================
VETRA Phase 12 — Veterinary Network & Directory Service Layer.
Manages veterinarian profiles, availability, specializations, and regional directory lookups.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid
from bson import ObjectId

from app.database import get_database


def ensure_veterinary_network_indexes(db=None):
    """Ensure indexes on the veterinary_profiles collection."""
    if db is None:
        db = get_database()
    try:
        db.veterinary_profiles.create_index("veterinarian_id", unique=True)
        db.veterinary_profiles.create_index("user_id")
        db.veterinary_profiles.create_index("availability_status")
        db.veterinary_profiles.create_index("service_regions")
        db.veterinary_profiles.create_index("specialization")
        db.veterinary_profiles.create_index("verification_status")
        db.veterinary_profiles.create_index([("created_at", -1)])
    except Exception:
        pass


def _generate_vet_id(db) -> str:
    """Generate human-readable ID: VET-YYYY-XXXX."""
    year = datetime.now(timezone.utc).year
    count = db.veterinary_profiles.count_documents({})
    candidate_num = count + 1
    while True:
        candidate_str = f"VET-{year}-{candidate_num:04d}"
        if not db.veterinary_profiles.find_one({"veterinarian_id": candidate_str}):
            return candidate_str
        candidate_num += 1


def _serialize_profile(item: dict, db=None) -> dict[str, Any]:
    """Serialize MongoDB profile document for response model."""
    if not item:
        return {}
    vet_id = item.get("veterinarian_id", "")
    user_id = str(item.get("user_id", ""))

    active_cases = 0
    if db is not None:
        try:
            active_cases = db.veterinary_cases.count_documents({
                "assigned_veterinarian_id": {"$in": [vet_id, user_id]},
                "status": {"$in": ["open", "assigned", "accepted", "in_review", "treatment", "follow_up"]}
            })
        except Exception:
            active_cases = 0

    return {
        "id": str(item.get("_id", "")),
        "veterinarian_id": vet_id,
        "user_id": user_id,
        "name": item.get("name", "Veterinarian"),
        "registration_reference": item.get("registration_reference") or "NOT_PROVIDED",
        "specialization": item.get("specialization") or ["general_practice"],
        "qualifications": item.get("qualifications"),
        "experience_years": int(item.get("experience_years", 0)),
        "phone": item.get("phone"),
        "email": item.get("email"),
        "service_regions": item.get("service_regions") or ["National"],
        "supported_species": item.get("supported_species") or ["cattle", "buffalo"],
        "availability_status": item.get("availability_status", "available"),
        "consultation_modes": item.get("consultation_modes") or ["telemedicine", "farm_visit", "in_person"],
        "organization": item.get("organization", "Independent"),
        "verification_status": item.get("verification_status", "unverified"),
        "active_cases_count": active_cases,
        "created_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": item.get("updated_at", datetime.now(timezone.utc).isoformat()),
    }


def create_or_update_profile(user_info: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create or update a veterinarian profile.
    Veterinarians can update their own profile; admins can update any.
    """
    db = get_database()
    ensure_veterinary_network_indexes(db)
    now = datetime.now(timezone.utc).isoformat()

    user_id = str(payload.get("user_id") or user_info.get("id") or user_info.get("_id") or "")
    existing = db.veterinary_profiles.find_one({"user_id": user_id})

    # Registration reference safety: never claim fabricated credentials
    reg_ref = payload.get("registration_reference")
    if not reg_ref or reg_ref.strip() in ("", "string"):
        reg_ref = "NOT_PROVIDED"

    # Default verification status is unverified unless explicit admin verification
    verif = payload.get("verification_status", "unverified")
    if user_info.get("role") != "admin" and verif == "verified":
        verif = "pending"

    if existing:
        vet_id = existing.get("veterinarian_id")
        update_data = {
            "name": payload.get("name", existing.get("name")),
            "registration_reference": reg_ref,
            "specialization": payload.get("specialization", existing.get("specialization", ["general_practice"])),
            "qualifications": payload.get("qualifications", existing.get("qualifications")),
            "experience_years": payload.get("experience_years", existing.get("experience_years", 0)),
            "phone": payload.get("phone", existing.get("phone")),
            "email": payload.get("email", existing.get("email")),
            "service_regions": payload.get("service_regions", existing.get("service_regions", ["National"])),
            "supported_species": payload.get("supported_species", existing.get("supported_species", ["cattle", "buffalo"])),
            "availability_status": payload.get("availability_status", existing.get("availability_status", "available")),
            "consultation_modes": payload.get("consultation_modes", existing.get("consultation_modes", ["telemedicine", "farm_visit"])),
            "organization": payload.get("organization", existing.get("organization", "Independent")),
            "verification_status": verif,
            "updated_at": now,
        }
        db.veterinary_profiles.update_one({"_id": existing["_id"]}, {"$set": update_data})
        updated = db.veterinary_profiles.find_one({"_id": existing["_id"]})
        return _serialize_profile(updated, db)

    # Create new profile
    vet_id = payload.get("veterinarian_id") or _generate_vet_id(db)
    new_doc = {
        "veterinarian_id": vet_id,
        "user_id": user_id,
        "name": payload.get("name", user_info.get("full_name") or "Veterinary Officer"),
        "registration_reference": reg_ref,
        "specialization": payload.get("specialization") or ["general_practice", "bovine_medicine"],
        "qualifications": payload.get("qualifications") or "B.V.Sc & A.H.",
        "experience_years": int(payload.get("experience_years", 3)),
        "phone": payload.get("phone"),
        "email": payload.get("email") or user_info.get("email"),
        "service_regions": payload.get("service_regions") or ["Anand", "Gujarat", "National"],
        "supported_species": payload.get("supported_species") or ["cattle", "buffalo"],
        "availability_status": payload.get("availability_status", "available"),
        "consultation_modes": payload.get("consultation_modes") or ["telemedicine", "farm_visit", "in_person"],
        "organization": payload.get("organization", "VETRA Clinical Network"),
        "verification_status": verif,
        "created_at": now,
        "updated_at": now,
    }
    res = db.veterinary_profiles.insert_one(new_doc)
    new_doc["_id"] = res.inserted_id
    return _serialize_profile(new_doc, db)


def get_profile(vet_identifier: str) -> Optional[dict[str, Any]]:
    """Get profile by veterinarian_id, user_id, or MongoDB ObjectId."""
    db = get_database()
    query = {"$or": [{"veterinarian_id": vet_identifier}, {"user_id": vet_identifier}]}
    if ObjectId.is_valid(vet_identifier):
        query["$or"].append({"_id": ObjectId(vet_identifier)})

    doc = db.veterinary_profiles.find_one(query)
    if doc:
        return _serialize_profile(doc, db)

    # Check users collection fallback if profile document not explicitly initialized
    if ObjectId.is_valid(vet_identifier):
        u = db.users.find_one({"_id": ObjectId(vet_identifier), "role": {"$in": ["veterinarian", "admin"]}})
        if u:
            # Synthesize transient profile without DB mutation
            return {
                "id": str(u["_id"]),
                "veterinarian_id": f"VET-{str(u['_id'])[-6:].upper()}",
                "user_id": str(u["_id"]),
                "name": u.get("full_name", "Veterinary Clinician"),
                "registration_reference": "NOT_PROVIDED",
                "specialization": ["general_practice", "bovine_medicine"],
                "qualifications": "B.V.Sc & A.H.",
                "experience_years": 5,
                "phone": None,
                "email": u.get("email"),
                "service_regions": ["Anand", "Gujarat", "National"],
                "supported_species": ["cattle", "buffalo"],
                "availability_status": "available",
                "consultation_modes": ["telemedicine", "farm_visit", "in_person"],
                "organization": "VETRA Clinical Network",
                "verification_status": "unverified",
                "active_cases_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    return None


def list_profiles(
    region: Optional[str] = None,
    specialization: Optional[str] = None,
    species: Optional[str] = None,
    availability: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> list[dict[str, Any]]:
    """List veterinary profiles with filtering and pagination."""
    db = get_database()
    ensure_veterinary_network_indexes(db)
    query: dict[str, Any] = {}

    if region and region != "all":
        query["service_regions"] = {"$regex": f"^{region}$|{region}|National", "$options": "i"}
    if specialization and specialization != "all":
        query["specialization"] = {"$regex": f"^{specialization}$|{specialization}", "$options": "i"}
    if species and species != "all":
        query["supported_species"] = {"$regex": f"^{species}$|{species}", "$options": "i"}
    if availability and availability != "all":
        query["availability_status"] = availability
    if mode and mode != "all":
        query["consultation_modes"] = mode

    cursor = db.veterinary_profiles.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [_serialize_profile(c, db) for c in cursor]

    # If collection is empty, synthesize records from existing users with role veterinarian/admin
    if not items and not query:
        v_users = list(db.users.find({"role": {"$in": ["veterinarian", "admin"]}}))
        for u in v_users:
            items.append({
                "id": str(u["_id"]),
                "veterinarian_id": f"VET-{str(u['_id'])[-6:].upper()}",
                "user_id": str(u["_id"]),
                "name": u.get("full_name", "Veterinary Clinician"),
                "registration_reference": "NOT_PROVIDED",
                "specialization": ["general_practice", "bovine_medicine"],
                "qualifications": "B.V.Sc & A.H.",
                "experience_years": 5,
                "phone": None,
                "email": u.get("email"),
                "service_regions": ["Anand", "Gujarat", "National"],
                "supported_species": ["cattle", "buffalo"],
                "availability_status": "available",
                "consultation_modes": ["telemedicine", "farm_visit", "in_person"],
                "organization": "VETRA Clinical Network",
                "verification_status": "unverified",
                "active_cases_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

    return items


def get_specializations() -> list[str]:
    """Return distinct active specializations in network."""
    db = get_database()
    specs = db.veterinary_profiles.distinct("specialization")
    default_specs = [
        "general_practice",
        "bovine_medicine",
        "ruminant_surgery",
        "infectious_disease_surveillance",
        "reproduction_theriogenology",
        "dairy_herd_health",
        "telemedicine_triage"
    ]
    all_s = sorted(list(set(specs + default_specs)))
    return all_s


def get_regions() -> list[str]:
    """Return distinct service regions covered."""
    db = get_database()
    regions = db.veterinary_profiles.distinct("service_regions")
    default_regions = ["Anand", "Ahmedabad", "Gujarat", "Maharashtra", "Punjab", "National"]
    all_r = sorted(list(set(regions + default_regions)))
    return all_r


def get_availability_summary() -> dict[str, Any]:
    """Return aggregate availability stats across veterinary network."""
    profiles = list_profiles(limit=200)
    total = len(profiles)
    avail = sum(1 for p in profiles if p.get("availability_status") == "available")
    on_call = sum(1 for p in profiles if p.get("availability_status") == "on_call")
    busy = sum(1 for p in profiles if p.get("availability_status") == "busy")
    offline = sum(1 for p in profiles if p.get("availability_status") == "offline")
    tele_enabled = sum(1 for p in profiles if "telemedicine" in (p.get("consultation_modes") or []))

    all_reg = set()
    all_spec = set()
    for p in profiles:
        for r in p.get("service_regions", []):
            all_reg.add(r)
        for s in p.get("specialization", []):
            all_spec.add(s)

    return {
        "total_veterinarians": total,
        "available_now": avail,
        "on_call": on_call,
        "busy": busy,
        "offline": offline,
        "telemedicine_enabled": tele_enabled,
        "regions_covered": sorted(list(all_reg)) if all_reg else ["National"],
        "specializations": sorted(list(all_spec)) if all_spec else ["general_practice"],
    }


class VeterinaryNetworkService:
    def create_or_update_profile(self, user_info, payload):
        return create_or_update_profile(user_info, payload)

    def get_profile(self, veterinarian_id):
        return get_profile(veterinarian_id)

    def list_profiles(self, specialization=None, region=None, availability_status=None, available_only=False, skip=0, limit=50):
        return list_profiles(specialization=specialization, region=region, availability_status=availability_status, available_only=available_only, limit=limit, skip=skip)

    def update_profile(self, veterinarian_id, user_info, update_data):
        return update_profile(veterinarian_id, user_info, update_data)

    def get_specializations(self):
        return get_specializations()

    def get_regions(self):
        return get_regions()

    def get_availability_summary(self):
        return get_availability_summary()


veterinary_network_service = VeterinaryNetworkService()


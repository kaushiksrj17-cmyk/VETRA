"""
backend/app/services/epidemiological_event_service.py
=====================================================
VETRA Phase 13 — Epidemiological Surveillance Event Engine & Service.

Manages the lifecycle of epidemiological events: detection signal ingestion,
multi-source evidence correlation, human institutional review, and authoritative confirmation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from bson import ObjectId

from app.database import get_database
from app.schemas.epidemiological_event import (
    EpidemiologicalEventCreate,
    EpidemiologicalEventUpdate,
    EpidemiologicalEventReviewRequest,
    EpidemiologicalEventConfirmRequest,
    EpidemiologicalEventDismissRequest,
    EPIDEMIOLOGICAL_EVENT_DISCLAIMER,
)


class EpidemiologicalEventService:
    """Service managing epidemiological surveillance events."""

    def __init__(self):
        self._indexes_initialized = False

    def _ensure_indexes(self, db):
        if self._indexes_initialized:
            return
        try:
            db.epidemiological_events.create_index("event_id", unique=True)
            db.epidemiological_events.create_index([("farm_id", 1), ("status", 1)])
            db.epidemiological_events.create_index([("event_type", 1), ("review_state", 1)])
            db.epidemiological_events.create_index([("created_at", -1)])
            self._indexes_initialized = True
        except Exception:
            pass

    def _serialize_event(self, doc: dict) -> dict:
        """Serializes MongoDB event document into API-safe dictionary."""
        if not doc:
            return {}
        res = dict(doc)
        if "_id" in res:
            del res["_id"]

        for dt_field in ["detected_at", "created_at", "updated_at"]:
            if isinstance(res.get(dt_field), datetime):
                res[dt_field] = res[dt_field].isoformat()

        res.setdefault("schema_version", "1.0.0")
        res.setdefault("disclaimer", EPIDEMIOLOGICAL_EVENT_DISCLAIMER)
        return res

    def generate_event_id(self, db) -> str:
        """Generates deterministic sequence ID: EPI-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        prefix = f"EPI-{year}-"
        count = db.epidemiological_events.count_documents({"event_id": {"$regex": f"^{prefix}"}})
        for i in range(1, 1000):
            candidate = f"{prefix}{count + i:04d}"
            if not db.epidemiological_events.find_one({"event_id": candidate}):
                return candidate
        return f"{prefix}{uuid.uuid4().hex[:4].upper()}"

    def create_event(
        self,
        event_data: EpidemiologicalEventCreate,
        creator: dict
    ) -> dict:
        """Creates a new epidemiological surveillance event (starts as SIGNAL/OPEN)."""
        db = get_database()
        self._ensure_indexes(db)

        now = datetime.now(timezone.utc)
        event_id = self.generate_event_id(db)

        detected_at = event_data.detected_at or now

        title = event_data.title or f"{event_data.event_type.replace('_', ' ').title()} - Farm {event_data.farm_id}"
        summary = event_data.summary or f"Epidemiological event ({event_data.event_type}) detected at holding {event_data.farm_id}."
        species_val = event_data.species
        if isinstance(species_val, str):
            species_val = [species_val]
        elif not species_val:
            species_val = ["cattle"]

        # Never automatically mark as CONFIRMED on creation
        initial_status = event_data.status
        if initial_status == "CONFIRMED":
            initial_status = "OPEN"
        initial_review = event_data.review_state
        if initial_review == "CONFIRMED":
            initial_review = "SIGNAL"

        doc = {
            "event_id": event_id,
            "event_type": event_data.event_type,
            "farm_id": event_data.farm_id,
            "title": title,
            "summary": summary,
            "animal_ids": event_data.animal_ids or [],
            "species": species_val,
            "geographic_context": event_data.geographic_context or {},
            "detected_at": detected_at,
            "observation_window": event_data.observation_window,
            "evidence_sources": event_data.evidence_sources or [],
            "clinical_signals": event_data.clinical_signals or [],
            "surveillance_signals": event_data.surveillance_signals or [],
            "predictive_signals": event_data.predictive_signals or [],
            "laboratory_references": event_data.laboratory_references or [],
            "visual_references": event_data.visual_references or [],
            "veterinary_case_references": event_data.veterinary_case_references or [],
            "risk_score": float(event_data.risk_score),
            "confidence": float(event_data.confidence),
            "severity": event_data.severity,
            "status": initial_status,
            "review_state": initial_review,
            "created_by": {
                "id": str(creator.get("id") or creator.get("user_id") or "system"),
                "name": creator.get("full_name") or creator.get("name") or "System Operator",
                "role": creator.get("role") or "veterinarian"
            },
            "reviewed_by": None,
            "confirmed_by": None,
            "review_history": [
                {
                    "action": "event_detected",
                    "performed_by": str(creator.get("id") or creator.get("user_id") or "system"),
                    "performed_by_name": creator.get("full_name") or creator.get("name"),
                    "performed_by_role": creator.get("role") or "veterinarian",
                    "comments": f"Surveillance event created via {event_data.event_type}.",
                    "timestamp": now.isoformat()
                }
            ],
            "created_at": now,
            "updated_at": now,
            "schema_version": "1.0.0",
        }

        db.epidemiological_events.insert_one(doc)

        # Audit log entry (strips credentials)
        try:
            db.audit_logs.insert_one({
                "action": "epidemiological_event_created",
                "event_id": event_id,
                "event_type": event_data.event_type,
                "farm_id": event_data.farm_id,
                "severity": event_data.severity,
                "user_id": str(creator.get("id") or creator.get("user_id")),
                "role": creator.get("role"),
                "timestamp": now
            })
        except Exception:
            pass

        return self._serialize_event(doc)

    def get_event(self, event_id: str) -> Optional[dict]:
        """Fetches a single epidemiological event."""
        db = get_database()
        query = {"event_id": event_id}
        if ObjectId.is_valid(event_id):
            query = {"$or": [{"event_id": event_id}, {"_id": ObjectId(event_id)}]}

        doc = db.epidemiological_events.find_one(query)
        return self._serialize_event(doc) if doc else None

    def list_events(
        self,
        farm_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        review_state: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[dict]:
        """Queries epidemiological events with bounded filters."""
        db = get_database()
        query: Dict[str, Any] = {}
        if farm_id:
            query["farm_id"] = farm_id
        if event_type:
            query["event_type"] = event_type
        if status:
            query["status"] = status
        if review_state:
            query["review_state"] = review_state
        if severity:
            query["severity"] = severity

        cursor = db.epidemiological_events.find(query).sort("created_at", -1).skip(skip).limit(min(limit, 100))
        return [self._serialize_event(doc) for doc in cursor]

    def update_event(self, event_id: str, updates: EpidemiologicalEventUpdate, user: dict) -> Optional[dict]:
        """Updates event clinical parameters."""
        db = get_database()
        now = datetime.now(timezone.utc)
        payload = {k: v for k, v in updates.model_dump().items() if v is not None}
        if not payload:
            return self.get_event(event_id)

        payload["updated_at"] = now
        res = db.epidemiological_events.find_one_and_update(
            {"event_id": event_id},
            {"$set": payload},
            return_document=True
        )
        return self._serialize_event(res) if res else None

    def review_event(
        self,
        event_id: str,
        review_req: EpidemiologicalEventReviewRequest,
        reviewer: dict
    ) -> Optional[dict]:
        """Moves event to UNDER_REVIEW and updates review_state."""
        db = get_database()
        now = datetime.now(timezone.utc)

        rev_notes = getattr(review_req, "reviewer_notes", None) or getattr(review_req, "review_notes", None) or "Review conducted."
        new_rev_state = getattr(review_req, "new_review_state", None) or getattr(review_req, "review_state", None) or "UNDER_REVIEW"

        history_item = {
            "action": "review_conducted",
            "performed_by": str(reviewer.get("id") or reviewer.get("user_id")),
            "performed_by_name": reviewer.get("full_name") or reviewer.get("name"),
            "performed_by_role": reviewer.get("role"),
            "comments": rev_notes,
            "timestamp": now.isoformat()
        }

        reviewed_by_info = {
            "id": str(reviewer.get("id") or reviewer.get("user_id")),
            "name": reviewer.get("full_name") or reviewer.get("name"),
            "role": reviewer.get("role"),
            "reviewed_at": now.isoformat()
        }

        updated = db.epidemiological_events.find_one_and_update(
            {"event_id": event_id},
            {
                "$set": {
                    "status": "UNDER_REVIEW",
                    "review_state": new_rev_state,
                    "reviewed_by": reviewed_by_info,
                    "updated_at": now
                },
                "$push": {"review_history": history_item}
            },
            return_document=True
        )

        try:
            db.audit_logs.insert_one({
                "action": "epidemiological_event_reviewed",
                "event_id": event_id,
                "reviewer_id": str(reviewer.get("id") or reviewer.get("user_id")),
                "role": reviewer.get("role"),
                "new_review_state": new_rev_state,
                "timestamp": now
            })
        except Exception:
            pass

        return self._serialize_event(updated) if updated else None

    def confirm_event(
        self,
        event_id: str,
        confirm_req: EpidemiologicalEventConfirmRequest,
        confirmer: dict
    ) -> Optional[dict]:
        """
        Authoritatively confirms an epidemiological event.
        Requires Institutional Officer or Administrator privileges.
        VETRA never confirms events autonomously.
        """
        db = get_database()
        now = datetime.now(timezone.utc)

        conf_authority = getattr(confirm_req, "confirmation_authority", None) or getattr(confirm_req, "official_reference", None) or "Institutional Authority"
        conf_notes = getattr(confirm_req, "confirmation_notes", None) or "Event confirmed."

        confirmed_by_info = {
            "id": str(confirmer.get("id") or confirmer.get("user_id")),
            "name": confirmer.get("full_name") or confirmer.get("name"),
            "role": confirmer.get("role"),
            "official_reference": conf_authority,
            "confirmed_at": now.isoformat()
        }

        history_item = {
            "action": "event_confirmed",
            "performed_by": str(confirmer.get("id") or confirmer.get("user_id")),
            "performed_by_name": confirmer.get("full_name") or confirmer.get("name"),
            "performed_by_role": confirmer.get("role"),
            "comments": conf_notes,
            "timestamp": now.isoformat()
        }

        updated = db.epidemiological_events.find_one_and_update(
            {"event_id": event_id},
            {
                "$set": {
                    "status": "CONFIRMED",
                    "review_state": "CONFIRMED",
                    "confirmed_by": confirmed_by_info,
                    "containment_measures": getattr(confirm_req, "containment_measures", None),
                    "updated_at": now
                },
                "$push": {"review_history": history_item}
            },
            return_document=True
        )

        try:
            db.audit_logs.insert_one({
                "action": "epidemiological_event_confirmed",
                "event_id": event_id,
                "confirmer_id": str(confirmer.get("id") or confirmer.get("user_id")),
                "role": confirmer.get("role"),
                "official_reference": confirm_req.official_reference,
                "timestamp": now
            })
        except Exception:
            pass

        return self._serialize_event(updated) if updated else None

    def dismiss_event(
        self,
        event_id: str,
        dismiss_req: EpidemiologicalEventDismissRequest,
        user: dict
    ) -> Optional[dict]:
        """Dismisses an unconfirmed statistical artifact or resolved signal."""
        db = get_database()
        now = datetime.now(timezone.utc)

        history_item = {
            "action": "event_dismissed",
            "performed_by": str(user.get("id") or user.get("user_id")),
            "performed_by_name": user.get("full_name") or user.get("name"),
            "performed_by_role": user.get("role"),
            "comments": f"Reason: {dismiss_req.reason}. {dismiss_req.explanatory_notes or ''}",
            "timestamp": now.isoformat()
        }

        updated = db.epidemiological_events.find_one_and_update(
            {"event_id": event_id},
            {
                "$set": {
                    "status": "DISMISSED",
                    "updated_at": now
                },
                "$push": {"review_history": history_item}
            },
            return_document=True
        )

        try:
            db.audit_logs.insert_one({
                "action": "epidemiological_event_dismissed",
                "event_id": event_id,
                "user_id": str(user.get("id") or user.get("user_id")),
                "role": user.get("role"),
                "reason": dismiss_req.reason,
                "timestamp": now
            })
        except Exception:
            pass

        return self._serialize_event(updated) if updated else None


epidemiological_event_service = EpidemiologicalEventService()

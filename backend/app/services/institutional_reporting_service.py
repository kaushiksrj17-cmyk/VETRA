"""
backend/app/services/institutional_reporting_service.py
======================================================
VETRA Phase 12 — Institutional Health Reporting & Surveillance Integration Service.
"""

import csv
from datetime import datetime, timezone
import io
import json
from typing import Any, Optional
from bson import ObjectId

from app.database import get_database
from app.schemas.institutional_reporting import (
    OUTBREAK_CANDIDATE_DISCLAIMER,
)
from app.services.institutional_adapters import get_institutional_adapter


def ensure_institutional_indexes(db=None):
    """Ensure indexes on the institutional_reports collection."""
    if db is None:
        db = get_database()
    try:
        db.institutional_reports.create_index("report_id", unique=True)
        db.institutional_reports.create_index("report_type")
        db.institutional_reports.create_index("farm_id")
        db.institutional_reports.create_index("status")
        db.institutional_reports.create_index("severity")
        db.institutional_reports.create_index([("created_at", -1)])
    except Exception:
        pass


def _generate_report_id(db) -> str:
    """Generate unique ID: REP-YYYY-XXXX."""
    year = datetime.now(timezone.utc).year
    count = db.institutional_reports.count_documents({})
    candidate_num = count + 1
    while True:
        candidate_str = f"REP-{year}-{candidate_num:04d}"
        if not db.institutional_reports.find_one({"report_id": candidate_str}):
            return candidate_str
        candidate_num += 1


def _serialize_report(item: dict, db=None) -> dict[str, Any]:
    """Serialize MongoDB report document."""
    if not item:
        return {}
    if db is None:
        db = get_database()

    farm_id = str(item.get("farm_id", "")) if item.get("farm_id") else None
    farm_name = item.get("farm_name")
    if farm_id and not farm_name and ObjectId.is_valid(farm_id):
        f = db.farms.find_one({"_id": ObjectId(farm_id)})
        if f:
            farm_name = f.get("name")

    return {
        "id": str(item.get("_id", "")),
        "report_id": item.get("report_id", "REP-UNKNOWN"),
        "report_type": item.get("report_type", "surveillance_summary"),
        "title": item.get("title", ""),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "animal_ids": item.get("animal_ids", []),
        "case_ids": item.get("case_ids", []),
        "surveillance_event_ids": item.get("surveillance_event_ids", []),
        "source_ids": item.get("source_ids", []),
        "reporting_organization": item.get("reporting_organization", "VETRA Institutional Health Network"),
        "reporting_user_id": str(item.get("reporting_user_id", "")),
        "reporting_user_name": item.get("reporting_user_name", "Officer"),
        "reporting_user_role": item.get("reporting_user_role", "veterinarian"),
        "severity": item.get("severity", "routine"),
        "status": item.get("status", "draft"),
        "summary": item.get("summary", ""),
        "evidence": item.get("evidence", []),
        "clinical_notes": item.get("clinical_notes"),
        "surveillance_context": item.get("surveillance_context"),
        "approval_trail": item.get("approval_trail", []),
        "approved_by": item.get("approved_by") or next((e.get("performed_by_name") or e.get("performed_by") for e in item.get("approval_trail", []) if e.get("action") == "approved"), None),
        "approved_at": item.get("approved_at") or next((e.get("timestamp") for e in item.get("approval_trail", []) if e.get("action") == "approved"), None),
        "approval_status": "approved" if item.get("status") in ("approved", "submitted", "acknowledged") else ("under_review" if item.get("status") == "under_review" else "pending"),
        "submission_details": item.get("submission_details") or item.get("external_acknowledgement"),
        "audit_trail": item.get("audit_trail") or item.get("approval_trail", []),
        "external_submission_id": item.get("external_submission_id"),
        "external_acknowledgement": item.get("external_acknowledgement"),
        "regulatory_disclaimer": OUTBREAK_CANDIDATE_DISCLAIMER,
        "created_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
        "submitted_at": item.get("submitted_at"),
        "updated_at": item.get("updated_at", datetime.now(timezone.utc).isoformat()),
    }


def create_report(user_info: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new institutional report in 'draft' status.
    Only veterinarians, institutional officers, or admins can create reports.
    """
    db = get_database()
    ensure_institutional_indexes(db)
    now = datetime.now(timezone.utc).isoformat()

    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "Reporting Officer"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    if user_role == "farmer":
        raise PermissionError("Farmers cannot author institutional disease surveillance reports.")

    report_id = _generate_report_id(db)

    # Initial approval trail event
    initial_event = {
        "action": "created_draft",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "comments": "Initial report drafted",
        "timestamp": now,
    }

    doc = {
        "report_id": report_id,
        "report_type": payload.get("report_type", "surveillance_summary"),
        "title": payload["title"],
        "farm_id": payload.get("farm_id"),
        "animal_ids": payload.get("animal_ids", []),
        "case_ids": payload.get("case_ids", []),
        "surveillance_event_ids": payload.get("surveillance_event_ids", []),
        "source_ids": payload.get("source_ids", []),
        "reporting_organization": payload.get("reporting_organization") or "VETRA Institutional Health Network",
        "reporting_user_id": user_id,
        "reporting_user_name": user_name,
        "reporting_user_role": user_role,
        "severity": payload.get("severity", "routine"),
        "status": "draft",
        "summary": payload["summary"],
        "evidence": payload.get("evidence", []),
        "clinical_notes": payload.get("clinical_notes"),
        "surveillance_context": payload.get("surveillance_context"),
        "approval_trail": [initial_event],
        "external_submission_id": None,
        "external_acknowledgement": None,
        "regulatory_disclaimer": OUTBREAK_CANDIDATE_DISCLAIMER,
        "created_at": now,
        "submitted_at": None,
        "updated_at": now,
    }

    res = db.institutional_reports.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Audit log
    db.audit_logs.insert_one({
        "action": "report_created",
        "user_id": user_id,
        "report_id": report_id,
        "report_type": doc["report_type"],
        "severity": doc["severity"],
        "timestamp": now,
    })

    return _serialize_report(doc, db)


def get_report(report_id: str, user_info: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Get report by ID with RBAC."""
    db = get_database()
    query = {"$or": [{"report_id": report_id}]}
    if ObjectId.is_valid(report_id):
        query["$or"].append({"_id": ObjectId(report_id)})

    doc = db.institutional_reports.find_one(query)
    if not doc:
        return None

    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()

    if user_role == "farmer":
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        if str(doc.get("farm_id")) not in farmer_farms:
            raise PermissionError("Access denied. You may only view reports concerning your own farm.")

    return _serialize_report(doc, db)


def list_reports(
    user_info: dict[str, Any],
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    farm_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> list[dict[str, Any]]:
    """List institutional reports with RBAC."""
    db = get_database()
    ensure_institutional_indexes(db)
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_role = str(user_info.get("role", "farmer")).lower()

    query: dict[str, Any] = {}
    if user_role == "farmer":
        farmer_farms = [str(f["_id"]) for f in db.farms.find({"owner_id": user_id})]
        query["farm_id"] = {"$in": farmer_farms}

    if report_type and report_type != "all":
        query["report_type"] = report_type
    if status and status != "all":
        query["status"] = status
    if farm_id and farm_id != "all":
        query["farm_id"] = farm_id

    cursor = db.institutional_reports.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [_serialize_report(c, db) for c in cursor]


def update_report(report_id: str, user_info: dict[str, Any], update_data: dict[str, Any]) -> dict[str, Any]:
    """Update draft report metadata."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    doc = db.institutional_reports.find_one({"report_id": report_id})
    if not doc and ObjectId.is_valid(report_id):
        doc = db.institutional_reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise ValueError(f"Report '{report_id}' was not found.")

    if doc.get("status") in ("approved", "submitted"):
        raise PermissionError("Cannot modify a report that has already been approved or submitted.")

    clean_payload = {k: v for k, v in update_data.items() if v is not None}
    clean_payload["updated_at"] = now
    db.institutional_reports.update_one({"_id": doc["_id"]}, {"$set": clean_payload})

    updated = db.institutional_reports.find_one({"_id": doc["_id"]})
    return _serialize_report(updated, db)


def review_report(report_id: str, user_info: dict[str, Any], comments: Optional[str] = None) -> dict[str, Any]:
    """Transition report to under_review."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "Reviewer"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    doc = db.institutional_reports.find_one({"report_id": report_id})
    if not doc and ObjectId.is_valid(report_id):
        doc = db.institutional_reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise ValueError(f"Report '{report_id}' was not found.")

    event = {
        "action": "under_review",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "comments": comments or "Case dossier placed under clinical review",
        "timestamp": now,
    }

    db.institutional_reports.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"status": "under_review", "updated_at": now},
            "$push": {"approval_trail": event}
        }
    )

    db.audit_logs.insert_one({
        "action": "report_reviewed",
        "user_id": user_id,
        "report_id": doc["report_id"],
        "timestamp": now,
    })

    updated = db.institutional_reports.find_one({"_id": doc["_id"]})
    return _serialize_report(updated, db)


def approve_report(report_id: str, user_info: dict[str, Any], comments: Optional[str] = None) -> dict[str, Any]:
    """Approve report for institutional dissemination."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "Approving Officer"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    if user_role == "farmer":
        raise PermissionError("Farmers cannot authorize institutional surveillance reports.")

    doc = db.institutional_reports.find_one({"report_id": report_id})
    if not doc and ObjectId.is_valid(report_id):
        doc = db.institutional_reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise ValueError(f"Report '{report_id}' was not found.")

    event = {
        "action": "approved",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "comments": comments or "Approved for institutional dispatch",
        "timestamp": now,
    }

    db.institutional_reports.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"status": "approved", "updated_at": now},
            "$push": {"approval_trail": event}
        }
    )

    db.audit_logs.insert_one({
        "action": "report_approved",
        "user_id": user_id,
        "report_id": doc["report_id"],
        "timestamp": now,
    })

    updated = db.institutional_reports.find_one({"_id": doc["_id"]})
    return _serialize_report(updated, db)


def submit_report(
    report_id: str,
    user_info: dict[str, Any],
    target_authority: Optional[str] = None,
    submission_notes: Optional[str] = None
) -> dict[str, Any]:
    """
    Submits an approved report to the institutional adapter.
    REPORT INTEGRITY: Must be 'approved' prior to submission.
    """
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "Officer"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    if user_role == "farmer":
        raise PermissionError("Farmers cannot submit institutional reports.")

    doc = db.institutional_reports.find_one({"report_id": report_id})
    if not doc and ObjectId.is_valid(report_id):
        doc = db.institutional_reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise ValueError(f"Report '{report_id}' was not found.")

    if doc.get("status") != "approved":
        raise ValueError(f"Cannot submit report in status '{doc.get('status')}'. Report must be 'approved' first.")

    adapter = get_institutional_adapter()
    sub_res = adapter.submit(doc)

    event = {
        "action": "submitted",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "comments": submission_notes or f"Transmitted via adapter (State: {adapter.state})",
        "timestamp": now,
    }

    db.institutional_reports.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": "submitted",
                "submitted_at": now,
                "external_submission_id": sub_res.get("submission_id"),
                "external_acknowledgement": sub_res,
                "updated_at": now,
            },
            "$push": {"approval_trail": event}
        }
    )

    db.audit_logs.insert_one({
        "action": "report_submitted",
        "user_id": user_id,
        "report_id": doc["report_id"],
        "submission_id": sub_res.get("submission_id"),
        "adapter_state": adapter.state,
        "timestamp": now,
    })

    updated = db.institutional_reports.find_one({"_id": doc["_id"]})
    return _serialize_report(updated, db)


def cancel_report(report_id: str, user_info: dict[str, Any], reason: str) -> dict[str, Any]:
    """Revoke or cancel a report."""
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user_info.get("id") or user_info.get("_id") or user_info.get("sub") or "")
    user_name = user_info.get("full_name") or user_info.get("name") or "User"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    doc = db.institutional_reports.find_one({"report_id": report_id})
    if not doc and ObjectId.is_valid(report_id):
        doc = db.institutional_reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise ValueError(f"Report '{report_id}' was not found.")

    event = {
        "action": "cancelled",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "comments": f"Cancelled: {reason}",
        "timestamp": now,
    }

    db.institutional_reports.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"status": "cancelled", "updated_at": now},
            "$push": {"approval_trail": event}
        }
    )

    db.audit_logs.insert_one({
        "action": "report_cancelled",
        "user_id": user_id,
        "report_id": doc["report_id"],
        "reason": reason,
        "timestamp": now,
    })

    updated = db.institutional_reports.find_one({"_id": doc["_id"]})
    return _serialize_report(updated, db)


def export_report(report_id: str, user_info: dict[str, Any], export_format: str = "json") -> dict[str, Any]:
    """Export report content in JSON or CSV format without exposing private credentials."""
    report = get_report(report_id, user_info)
    if not report:
        raise ValueError(f"Report '{report_id}' was not found.")

    if export_format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Report ID", report.get("report_id")])
        writer.writerow(["Report Type", report.get("report_type")])
        writer.writerow(["Title", report.get("title")])
        writer.writerow(["Severity", report.get("severity")])
        writer.writerow(["Status", report.get("status")])
        writer.writerow(["Reporting Organization", report.get("reporting_organization")])
        writer.writerow(["Reporting Officer", report.get("reporting_user_name")])
        writer.writerow(["Created At", report.get("created_at")])
        writer.writerow(["Submitted At", report.get("submitted_at") or "Not Submitted"])
        writer.writerow(["Clinical Summary", report.get("summary")])
        writer.writerow(["Regulatory Disclaimer", report.get("regulatory_disclaimer")])
        csv_str = output.getvalue()
        return {
            "report_id": report["report_id"],
            "format": "csv",
            "content": csv_str,
            "filename": f"{report['report_id']}_export.csv",
        }

    # Default JSON format
    return {
        "report_id": report["report_id"],
        "format": "json",
        "content": json.dumps(report, indent=2),
        "filename": f"{report['report_id']}_export.json",
    }


class InstitutionalReportingService:
    def create_report(self, data, current_user):
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        return create_report(current_user, payload)

    def get_report(self, report_id: str, current_user: Optional[dict] = None):
        user_info = current_user or {"role": "admin"}
        return get_report(report_id, user_info)

    def list_reports(self, report_type=None, status=None, farm_id=None, severity=None, skip=0, limit=50, current_user=None):
        user_info = current_user or {"role": "admin"}
        return list_reports(user_info, report_type=report_type, status=status, farm_id=farm_id, limit=limit, skip=skip)

    def update_report(self, report_id: str, data, current_user):
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        return update_report(report_id, current_user, payload)

    def review_report(self, report_id: str, action, current_user):
        comments = getattr(action, "reviewer_notes", None) or getattr(action, "comments", None) or str(action)
        return review_report(report_id, current_user, comments=comments)

    def approve_report(self, report_id: str, action, current_user):
        comments = getattr(action, "approval_notes", None) or getattr(action, "comments", None) or str(action)
        return approve_report(report_id, current_user, comments=comments)

    def submit_report(self, report_id: str, action, current_user):
        target = getattr(action, "target_authority", None) or "National Animal Health Reporting Service"
        notes = getattr(action, "submission_notes", None) or getattr(action, "submission_remarks", None)
        return submit_report(report_id, current_user, target_authority=target, submission_notes=notes)

    def cancel_report(self, report_id: str, reason, current_user):
        return cancel_report(report_id, current_user, reason=reason or "Cancelled by user")

    def export_report(self, report_id: str, format: str = "json", redact_pii: bool = False, current_user: Optional[dict] = None):
        user_info = current_user or {"role": "admin"}
        rep = get_report(report_id, user_info)
        if not rep:
            raise ValueError(f"Report '{report_id}' was not found.")
        rep_copy = dict(rep)
        if redact_pii:
            rep_copy["farm_id"] = "[REDACTED_FARM_IDENTITY]"
            rep_copy["farm_name"] = "[REDACTED_FARM_NAME]"
            rep_copy["reporting_user_name"] = "[REDACTED_USER]"
            rep_copy["reporting_user_id"] = "[REDACTED_ID]"
            rep_copy["reporting_user"] = "[REDACTED_USER]"

        if format.lower() == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["report_id", "report_type", "farm_id", "severity", "status", "summary"])
            writer.writerow([
                rep_copy.get("report_id"),
                rep_copy.get("report_type"),
                rep_copy.get("farm_id"),
                rep_copy.get("severity"),
                rep_copy.get("status"),
                rep_copy.get("summary")
            ])
            return out.getvalue()
        return json.dumps(rep_copy, indent=2)


institutional_reporting_service = InstitutionalReportingService()


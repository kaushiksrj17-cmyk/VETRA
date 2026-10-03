import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.services.media_service import (
    compute_sha256,
    get_absolute_media_path,
    save_media_file,
    validate_media_upload,
)
from app.services.websocket_manager import manager
from ai_engine.computer_vision import CLINICAL_SAFETY_DISCLAIMER, get_visual_analyzer
from ai_engine.disease_intelligence import assess_disease_risk
from ai_engine.multimodal_health import (
    compare_temporal_visual_analyses,
    compute_multimodal_health_assessment,
)


def ensure_visual_health_indexes():
    """
    Ensure essential MongoDB indexes exist for visual health collections.
    Safe and non-destructive.
    """
    try:
        db = get_database()
        db.visual_analyses.create_index("analysis_id", unique=True, sparse=True)
        db.visual_analyses.create_index("animal_id")
        db.visual_analyses.create_index("farm_id")
        db.visual_analyses.create_index("media_hash")
        db.visual_analyses.create_index([("created_at", -1)])
        db.visual_analyses.create_index("visual_risk_score")

        db.visual_observations.create_index("analysis_id")
        db.visual_observations.create_index("animal_id")
        db.visual_observations.create_index("farm_id")
        db.visual_observations.create_index("indicator")
        db.visual_observations.create_index([("timestamp", -1)])

        db.multimodal_assessments.create_index("assessment_id", unique=True, sparse=True)
        db.multimodal_assessments.create_index("animal_id")
        db.multimodal_assessments.create_index("farm_id")
        db.multimodal_assessments.create_index([("created_at", -1)])
        db.multimodal_assessments.create_index("combined_risk")
    except Exception:
        pass


def _verify_animal_access(animal_id: str, current_user: dict, db: Any) -> dict[str, Any]:
    """
    Verify animal existence and enforce farmer ownership RBAC.
    """
    query = {"_id": ObjectId(animal_id)} if ObjectId.is_valid(animal_id) else {"_id": animal_id}
    animal = db.animals.find_one(query)
    if not animal and not ObjectId.is_valid(animal_id):
        animal = db.animals.find_one({"tag_id": animal_id})

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal '{animal_id}' not found."
        )

    # Farmer data isolation check
    user_role = current_user.get("role")
    user_id = current_user.get("sub")
    if user_role == "farmer":
        farm_id = str(animal.get("farm_id", ""))
        farm_query = {"_id": ObjectId(farm_id)} if ObjectId.is_valid(farm_id) else {"_id": farm_id}
        farm = db.farms.find_one(farm_query)
        if not farm or str(farm.get("owner_id")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only analyze animals belonging to your holdings."
            )

    return animal


def serialize_visual_analysis(item: dict) -> dict[str, Any]:
    """
    Transform MongoDB visual analysis document into JSON-serializable dictionary.
    """
    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")

    return {
        "id": str(item["_id"]),
        "analysis_id": item.get("analysis_id", f"VA-{str(item['_id'])[:8]}"),
        "animal_id": str(item.get("animal_id")),
        "animal_tag": item.get("animal_tag"),
        "animal_name": item.get("animal_name"),
        "farm_id": str(item.get("farm_id", "")),
        "farm_name": item.get("farm_name"),
        "media_type": item.get("media_type", "image"),
        "filename": item.get("filename", "unknown"),
        "media_hash": item.get("media_hash", ""),
        "file_size_bytes": int(item.get("file_size_bytes", 0)),
        "animal_detected": item.get("animal_detected", "cattle"),
        "detection_confidence": float(item.get("detection_confidence", 0.90)),
        "observations": item.get("observations", []),
        "visual_risk_score": float(item.get("visual_risk_score", 0.0)),
        "risk_category": item.get("risk_category", "LOW"),
        "model_name": item.get("model_name", "VETRA-VisualEngine"),
        "model_version": item.get("model_version", "v1.0"),
        "processing_time_ms": float(item.get("processing_time_ms", 0.0)),
        "requires_veterinary_review": bool(item.get("requires_veterinary_review", False)),
        "review_status": item.get("review_status", "pending"),
        "veterinary_case_id": item.get("veterinary_case_id"),
        "explanation": item.get("explanation", ""),
        "created_at": created_at_str,
        "clinical_safety_notice": item.get("clinical_safety_notice", CLINICAL_SAFETY_DISCLAIMER)
    }


def serialize_multimodal_assessment(item: dict) -> dict[str, Any]:
    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")

    return {
        "id": str(item["_id"]),
        "assessment_id": item.get("assessment_id", f"MM-{str(item['_id'])[:8]}"),
        "animal_id": str(item.get("animal_id")),
        "animal_tag": item.get("animal_tag"),
        "animal_name": item.get("animal_name"),
        "farm_id": str(item.get("farm_id", "")),
        "farm_name": item.get("farm_name"),
        "visual_analysis_id": str(item.get("visual_analysis_id")) if item.get("visual_analysis_id") else None,
        "visual_score": float(item.get("visual_score", 0.0)),
        "telemetry_score": float(item.get("telemetry_score", 0.0)),
        "disease_risk": float(item.get("disease_risk", 0.0)),
        "preventive_risk": float(item.get("preventive_risk", 0.0)),
        "surveillance_risk": float(item.get("surveillance_risk", 0.0)),
        "combined_risk": float(item.get("combined_risk", 0.0)),
        "risk_category": item.get("risk_category", "LOW"),
        "contributing_factors": item.get("contributing_factors", []),
        "visual_telemetry_consistency": item.get("visual_telemetry_consistency", "nominal"),
        "explanation": item.get("explanation", ""),
        "recommended_action": item.get("recommended_action", ""),
        "veterinary_review_required": bool(item.get("veterinary_review_required", False)),
        "veterinary_case_id": item.get("veterinary_case_id"),
        "created_at": created_at_str,
        "clinical_safety_notice": item.get("clinical_safety_notice", CLINICAL_SAFETY_DISCLAIMER)
    }


def process_image_analysis(
    animal_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    current_user: dict,
    db: Any
) -> dict[str, Any]:
    """
    Validate, save, and analyze an uploaded livestock image.
    """
    # 1. Validation
    is_valid, media_type, err = validate_media_upload(filename, file_bytes, content_type)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    if media_type != "image":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected image file format.")

    # 2. Access control
    animal = _verify_animal_access(animal_id, current_user, db)
    farm_id = str(animal.get("farm_id", ""))
    farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
    farm_name = farm.get("name", "Holding") if farm else "Holding"

    # 3. Secure File Saving
    rel_path, abs_path, media_hash = save_media_file(file_bytes, filename, "image")

    # 4. Computer Vision Analysis
    analyzer = get_visual_analyzer()
    animal_context = {
        "species": animal.get("species", "Cattle"),
        "tag_id": animal.get("tag_id"),
        "name": animal.get("name")
    }

    # Gather latest telemetry reading for context if available
    latest_reading = db.health_readings.find_one(
        {"animal_id": str(animal["_id"])},
        sort=[("timestamp", -1)]
    )
    if latest_reading:
        animal_context["latest_telemetry_status"] = latest_reading.get("status", "normal")
        animal_context["latest_temp"] = latest_reading.get("temperature_c")
        animal_context["latest_resp"] = latest_reading.get("respiratory_rate")

    cv_result = analyzer.analyze_image(file_bytes, animal_context=animal_context)

    # 5. Database Document Generation
    now = datetime.now(timezone.utc)
    count = db.visual_analyses.count_documents({})
    analysis_id = f"VA-{now.year}-{(count + 1):04d}"

    doc = {
        "analysis_id": analysis_id,
        "animal_id": str(animal["_id"]),
        "animal_tag": animal.get("tag_id"),
        "animal_name": animal.get("name"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "media_type": "image",
        "filename": filename,
        "storage_path": rel_path,
        "media_hash": media_hash,
        "file_size_bytes": len(file_bytes),
        "animal_detected": cv_result["animal_detected"],
        "detection_confidence": cv_result["detection_confidence"],
        "observations": cv_result["observations"],
        "visual_risk_score": cv_result["visual_risk_score"],
        "risk_category": cv_result["risk_category"],
        "model_name": cv_result["model_name"],
        "model_version": cv_result["model_version"],
        "processing_time_ms": cv_result["processing_time_ms"],
        "requires_veterinary_review": cv_result["requires_veterinary_review"],
        "review_status": "pending",
        "veterinary_case_id": None,
        "explanation": cv_result["explanation"],
        "created_at": now,
        "clinical_safety_notice": cv_result["clinical_safety_notice"]
    }

    result = db.visual_analyses.insert_one(doc)
    doc["_id"] = result.inserted_id

    # 6. Save observations to visual_observations collection
    for obs in cv_result["observations"]:
        db.visual_observations.insert_one({
            "observation_id": obs["observation_id"],
            "analysis_id": analysis_id,
            "animal_id": str(animal["_id"]),
            "animal_tag": animal.get("tag_id"),
            "farm_id": farm_id,
            "indicator": obs["indicator"],
            "description": obs["description"],
            "confidence": obs["confidence"],
            "confidence_level": obs["confidence_level"],
            "severity": obs["severity"],
            "timestamp": now,
            "source": obs["source"]
        })

    # 7. Alert Integration with duplicate suppression (Step 17)
    if cv_result["risk_category"] in ["CRITICAL", "HIGH"]:
        alert_key = f"vis_alert_{analysis_id}"
        existing_alert = db.alerts.find_one({"visual_analysis_id": analysis_id, "status": "active"})
        if not existing_alert:
            db.alerts.insert_one({
                "animal_id": str(animal["_id"]),
                "farm_id": farm_id,
                "owner_id": farm.get("owner_id", "") if farm else "",
                "device_id": "COMPUTER_VISION_SYSTEM",
                "alert_type": "visual_health_signal",
                "severity": "critical" if cv_result["risk_category"] == "CRITICAL" else "high",
                "title": f"Visual Health Signal: {animal.get('tag_id') or 'Animal'}",
                "message": f"Elevated visual risk ({cv_result['visual_risk_score']:.0f}/100) detected on {animal.get('name') or animal.get('tag_id')}. Veterinary examination recommended.",
                "triggered_by": ["computer_vision_engine"],
                "status": "active",
                "visual_analysis_id": analysis_id,
                "created_at": now,
                "acknowledged_at": None,
                "resolved_at": None
            })

    # 8. WebSocket broadcast
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "visual_health_update",
                "action": "analyzed",
                "analysis_id": analysis_id,
                "animal_tag": animal.get("tag_id"),
                "visual_risk_score": cv_result["visual_risk_score"],
                "risk_category": cv_result["risk_category"]
            }))
    except Exception:
        pass

    return serialize_visual_analysis(doc)


def process_video_analysis(
    animal_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    current_user: dict,
    db: Any
) -> dict[str, Any]:
    """
    Validate, save, and analyze an uploaded video via controlled frame sampling.
    """
    is_valid, media_type, err = validate_media_upload(filename, file_bytes, content_type)
    if not is_valid or media_type != "video":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Expected supported video format (.mp4, .avi, .mov)."
        )

    animal = _verify_animal_access(animal_id, current_user, db)
    farm_id = str(animal.get("farm_id", ""))
    farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
    farm_name = farm.get("name", "Holding") if farm else "Holding"

    rel_path, abs_path, media_hash = save_media_file(file_bytes, filename, "video")

    analyzer = get_visual_analyzer()
    animal_context = {
        "species": animal.get("species", "Cattle"),
        "tag_id": animal.get("tag_id"),
        "name": animal.get("name")
    }

    try:
        cv_result = analyzer.analyze_video(abs_path, animal_context=animal_context, max_samples=10)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis processing error: {str(e)}"
        )

    now = datetime.now(timezone.utc)
    count = db.visual_analyses.count_documents({})
    analysis_id = f"VA-{now.year}-{(count + 1):04d}"

    doc = {
        "analysis_id": analysis_id,
        "animal_id": str(animal["_id"]),
        "animal_tag": animal.get("tag_id"),
        "animal_name": animal.get("name"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "media_type": "video",
        "filename": filename,
        "storage_path": rel_path,
        "media_hash": media_hash,
        "file_size_bytes": len(file_bytes),
        "duration_sec": cv_result["duration_sec"],
        "total_frames_sampled": cv_result["total_frames_sampled"],
        "animal_detected": animal.get("species", "cattle").lower(),
        "detection_confidence": 0.92,
        "observations": cv_result["observations_detected"],
        "observation_frequency": cv_result["observation_frequency"],
        "temporal_consistency": cv_result["temporal_consistency"],
        "visual_risk_score": cv_result["visual_risk_score"],
        "risk_category": cv_result["risk_category"],
        "model_name": cv_result["model_name"],
        "model_version": cv_result["model_version"],
        "processing_time_ms": cv_result["processing_time_ms"],
        "requires_veterinary_review": cv_result["requires_veterinary_review"],
        "review_status": "pending",
        "veterinary_case_id": None,
        "explanation": cv_result["explanation"],
        "created_at": now,
        "clinical_safety_notice": cv_result["clinical_safety_notice"]
    }

    result = db.visual_analyses.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Broadcast via WebSocket
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "visual_health_update",
                "action": "video_analyzed",
                "analysis_id": analysis_id,
                "temporal_consistency": cv_result["temporal_consistency"],
                "visual_risk_score": cv_result["visual_risk_score"]
            }))
    except Exception:
        pass

    return serialize_visual_analysis(doc)


def generate_multimodal_assessment(
    animal_id: str,
    visual_analysis_id: Optional[str],
    current_user: dict,
    db: Any
) -> dict[str, Any]:
    """
    Synthesize visual, IoT telemetry, disease screening, surveillance, and preventive
    indicators into a unified Multimodal Health Assessment.
    """
    animal = _verify_animal_access(animal_id, current_user, db)
    aid = str(animal["_id"])
    farm_id = str(animal.get("farm_id", ""))

    farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
    farm_name = farm.get("name", "Holding") if farm else "Holding"

    # 1. Visual Analysis Data
    visual_analysis = None
    if visual_analysis_id:
        v_query = {"analysis_id": visual_analysis_id}
        if ObjectId.is_valid(visual_analysis_id):
            v_query = {"$or": [{"_id": ObjectId(visual_analysis_id)}, {"analysis_id": visual_analysis_id}]}
        visual_analysis = db.visual_analyses.find_one(v_query)

    if not visual_analysis:
        visual_analysis = db.visual_analyses.find_one(
            {"animal_id": aid},
            sort=[("created_at", -1)]
        )

    # 2. IoT Telemetry Health Data
    from app.services.alert_engine import evaluate_health_risk
    latest_reading = db.health_readings.find_one(
        {"animal_id": aid},
        sort=[("timestamp", -1)]
    )
    if latest_reading:
        risk_eval = evaluate_health_risk(
            temperature_c=latest_reading.get("temperature_c", 38.5),
            heart_rate_bpm=latest_reading.get("heart_rate_bpm", 70),
            activity_level=latest_reading.get("activity_level", 100),
            rumination_level=latest_reading.get("rumination_level", 450),
            respiratory_rate=latest_reading.get("respiratory_rate", 24)
        )
        health_risk_score = 75.0 if risk_eval["overall_risk"] == "critical" else (
            50.0 if risk_eval["overall_risk"] == "high" else (
                25.0 if risk_eval["overall_risk"] == "medium" else 10.0
            )
        )
        telemetry_risk_data = {
            "health_risk_score": health_risk_score,
            "latest_temp": latest_reading.get("temperature_c"),
            "latest_resp": latest_reading.get("respiratory_rate"),
            "latest_activity": latest_reading.get("activity_level"),
            "latest_rumination": latest_reading.get("rumination_level"),
        }
    else:
        telemetry_risk_data = {"health_risk_score": 10.0, "latest_temp": 38.5, "latest_resp": 24.0, "latest_activity": 100.0}

    # 3. Disease Intelligence Data
    features = {
        "temp_deviation": abs(latest_reading.get("temperature_c", 38.5) - 38.5) if latest_reading else 0.0,
        "hr_deviation": abs(latest_reading.get("heart_rate_bpm", 70) - 70) if latest_reading else 0.0,
        "resp_deviation": abs(latest_reading.get("respiratory_rate", 24) - 24) if latest_reading else 0.0,
        "activity_reduction_pct": max(0.0, (100.0 - latest_reading.get("activity_level", 100.0))) if latest_reading else 0.0,
        "rumination_reduction_pct": max(0.0, (450.0 - latest_reading.get("rumination_level", 450.0)) / 4.5) if latest_reading else 0.0,
        "temp_rate_of_change": 0.0
    }
    disease_intelligence_data = assess_disease_risk(features)

    # 4. Herd Surveillance Risk Data
    from app.services.farm_risk_engine import compute_farm_disease_risk
    surveillance_risk_data = compute_farm_disease_risk(farm or {"_id": farm_id}, db) if farm else {"risk_score": 10.0}

    # 5. Preventive Status Data
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d")
    overdue_tasks = list(db.preventive_tasks.find({
        "animal_id": aid,
        "status": "pending",
        "due_date": {"$lt": now_str}
    }))
    preventive_status_data = {"overdue_tasks_count": len(overdue_tasks)}

    # 6. Execute Multimodal Engine
    assessment = compute_multimodal_health_assessment(
        animal_data=animal,
        visual_analysis=visual_analysis,
        telemetry_risk_data=telemetry_risk_data,
        disease_intelligence_data=disease_intelligence_data,
        surveillance_risk_data=surveillance_risk_data,
        preventive_status_data=preventive_status_data
    )
    assessment["farm_name"] = farm_name

    # Save to MongoDB
    insert_doc = dict(assessment)
    insert_doc["created_at"] = now
    res = db.multimodal_assessments.insert_one(insert_doc)
    insert_doc["_id"] = res.inserted_id

    # Alert generation if combined risk is critical
    if assessment["risk_category"] in ["CRITICAL", "HIGH"]:
        existing_alert = db.alerts.find_one({"multimodal_assessment_id": assessment["assessment_id"], "status": "active"})
        if not existing_alert:
            db.alerts.insert_one({
                "animal_id": aid,
                "farm_id": farm_id,
                "owner_id": farm.get("owner_id", "") if farm else "",
                "device_id": "MULTIMODAL_ENGINE",
                "alert_type": "multimodal_health_signal",
                "severity": "critical" if assessment["risk_category"] == "CRITICAL" else "high",
                "title": f"Multimodal Health Concern: {animal.get('tag_id') or 'Animal'}",
                "message": f"Multimodal risk ({assessment['combined_risk']:.0f}/100) flagged. Directional consistency: {assessment['visual_telemetry_consistency']}.",
                "triggered_by": ["multimodal_health_engine"],
                "status": "active",
                "multimodal_assessment_id": assessment["assessment_id"],
                "created_at": now,
                "acknowledged_at": None,
                "resolved_at": None
            })

    # WebSocket broadcast
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "multimodal_health_update",
                "assessment_id": assessment["assessment_id"],
                "animal_tag": animal.get("tag_id"),
                "combined_risk": assessment["combined_risk"],
                "risk_category": assessment["risk_category"]
            }))
    except Exception:
        pass

    return serialize_multimodal_assessment(insert_doc)


def get_visual_analysis(analysis_id: str, db: Any) -> Optional[dict[str, Any]]:
    query = {"analysis_id": analysis_id}
    if ObjectId.is_valid(analysis_id):
        query = {"$or": [{"_id": ObjectId(analysis_id)}, {"analysis_id": analysis_id}]}
    doc = db.visual_analyses.find_one(query)
    return serialize_visual_analysis(doc) if doc else None


def get_multimodal_assessment(assessment_id: str, db: Any) -> Optional[dict[str, Any]]:
    query = {"assessment_id": assessment_id}
    if ObjectId.is_valid(assessment_id):
        query = {"$or": [{"_id": ObjectId(assessment_id)}, {"assessment_id": assessment_id}]}
    doc = db.multimodal_assessments.find_one(query)
    return serialize_multimodal_assessment(doc) if doc else None


def list_visual_observations(
    db: Any,
    current_user: dict,
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    indicator: Optional[str] = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    user_role = current_user.get("role")
    user_id = current_user.get("sub")

    if user_role == "farmer":
        farms = list(db.farms.find({"owner_id": user_id}))
        if not farms and ObjectId.is_valid(user_id):
            farms = list(db.farms.find({"owner_id": ObjectId(user_id)}))
        farmer_fids = [str(f["_id"]) for f in farms]
        query["farm_id"] = {"$in": farmer_fids}

    if farm_id:
        query["farm_id"] = farm_id
    if animal_id:
        query["animal_id"] = animal_id
    if indicator:
        query["indicator"] = indicator

    cursor = db.visual_observations.find(query).sort("timestamp", -1).limit(limit)
    res = []
    for doc in cursor:
        ts = doc.get("timestamp")
        res.append({
            "id": str(doc["_id"]),
            "observation_id": doc.get("observation_id"),
            "analysis_id": doc.get("analysis_id"),
            "animal_id": str(doc.get("animal_id")),
            "animal_tag": doc.get("animal_tag"),
            "farm_id": str(doc.get("farm_id")),
            "indicator": doc.get("indicator"),
            "description": doc.get("description"),
            "confidence": float(doc.get("confidence", 0.0)),
            "confidence_level": doc.get("confidence_level", "Moderate"),
            "severity": doc.get("severity", "medium"),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
            "source": doc.get("source", "computer_vision_engine")
        })
    return res


def list_visual_analyses(
    db: Any,
    current_user: dict,
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    user_role = current_user.get("role")
    user_id = current_user.get("sub")

    if user_role == "farmer":
        farms = list(db.farms.find({"owner_id": user_id}))
        if not farms and ObjectId.is_valid(user_id):
            farms = list(db.farms.find({"owner_id": ObjectId(user_id)}))
        farmer_fids = [str(f["_id"]) for f in farms]
        query["farm_id"] = {"$in": farmer_fids}

    if farm_id:
        query["farm_id"] = farm_id
    if animal_id:
        query["animal_id"] = animal_id

    cursor = db.visual_analyses.find(query).sort("created_at", -1).limit(limit)
    return [serialize_visual_analysis(doc) for doc in cursor]


def get_animal_visual_trend(animal_id: str, current_user: dict, db: Any) -> dict[str, Any]:
    """
    Retrieve chronological comparison of visual analyses for an animal.
    """
    _verify_animal_access(animal_id, current_user, db)
    analyses = list(db.visual_analyses.find({"animal_id": animal_id}).sort("created_at", 1))
    if not analyses:
        return {
            "animal_id": animal_id,
            "trajectory": "no_data",
            "explanation": "No visual analyses recorded for this animal yet.",
            "changes": [],
            "persistent_indicators": []
        }

    if len(analyses) == 1:
        latest = analyses[0]
        obs_names = [o["indicator"] for o in latest.get("observations", [])]
        return {
            "animal_id": animal_id,
            "earlier_analysis_id": str(latest.get("analysis_id")),
            "latest_analysis_id": str(latest.get("analysis_id")),
            "earlier_date": str(latest.get("created_at")),
            "latest_date": str(latest.get("created_at")),
            "trajectory": "baseline",
            "score_delta": 0.0,
            "persistent_indicators": obs_names,
            "new_indicators": [],
            "resolved_indicators": [],
            "changes": [],
            "explanation": f"Single baseline assessment recorded (Score: {latest.get('visual_risk_score', 0):.0f}/100)."
        }

    earlier = analyses[-2]
    latest = analyses[-1]
    return compare_temporal_visual_analyses(earlier, latest)


def escalate_to_veterinary_case(
    analysis_id: str,
    notes: Optional[str],
    priority: Optional[str],
    current_user: dict,
    db: Any
) -> dict[str, Any]:
    """
    Escalate a visual health analysis to an official clinical case in veterinary_cases collection.
    """
    v_analysis = db.visual_analyses.find_one({"$or": [{"analysis_id": analysis_id}, {"_id": ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else None}]})
    if not v_analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual analysis not found.")

    aid = str(v_analysis["animal_id"])
    animal = db.animals.find_one({"_id": ObjectId(aid)}) if ObjectId.is_valid(aid) else db.animals.find_one({"_id": aid})
    fid = str(v_analysis["farm_id"])
    farm = db.farms.find_one({"_id": ObjectId(fid)}) if ObjectId.is_valid(fid) else db.farms.find_one({"_id": fid})

    from app.routes.veterinary_cases import _generate_case_number

    now = datetime.now(timezone.utc)
    case_number = _generate_case_number(db)

    risk_score = v_analysis.get("visual_risk_score", 0.0)
    assigned_priority = priority or ("critical" if risk_score >= 70 else ("high" if risk_score >= 45 else "medium"))

    case_doc = {
        "case_number": case_number,
        "title": f"Visual Health Referral: {v_analysis.get('animal_tag') or 'Animal'}",
        "description": notes or f"Referral originating from visual analysis {v_analysis.get('analysis_id')}. {v_analysis.get('explanation')}",
        "case_type": "suspected_disease",
        "priority": assigned_priority,
        "status": "open",
        "animal_id": aid,
        "farm_id": fid,
        "owner_id": farm.get("owner_id", "") if farm else "",
        "created_by": current_user.get("sub", ""),
        "creator_role": current_user.get("role", "farmer"),
        "assigned_veterinarian_id": None,
        "visual_analysis_id": v_analysis.get("analysis_id"),
        "clinical_findings": [f"Visual Risk: {risk_score}/100 ({v_analysis.get('risk_category')})"],
        "suspected_conditions": [o["indicator"] for o in v_analysis.get("observations", [])],
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
        "resolution_notes": None
    }

    res = db.veterinary_cases.insert_one(case_doc)
    case_doc["_id"] = res.inserted_id

    # Update visual analysis record
    db.visual_analyses.update_one(
        {"_id": v_analysis["_id"]},
        {"$set": {"review_status": "escalated_to_case", "veterinary_case_id": case_number, "updated_at": now}}
    )

    return {
        "case_number": case_number,
        "case_id": str(case_doc["_id"]),
        "status": "open",
        "priority": assigned_priority,
        "analysis_id": v_analysis.get("analysis_id"),
        "message": f"Clinical case {case_number} created successfully from visual analysis."
    }


def escalate_to_surveillance_review(
    analysis_id: str,
    notes: Optional[str],
    current_user: dict,
    db: Any
) -> dict[str, Any]:
    """
    Escalate a visual health finding into a herd disease surveillance event.
    """
    v_analysis = db.visual_analyses.find_one({"$or": [{"analysis_id": analysis_id}, {"_id": ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else None}]})
    if not v_analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual analysis not found.")

    from app.services.surveillance_service import create_disease_event

    obs = v_analysis.get("observations", [])
    symptoms = [o["description"] for o in obs]
    dominant_ind = obs[0]["indicator"] if obs else "visual_anomaly"

    event_payload = {
        "farm_id": str(v_analysis["farm_id"]),
        "animal_id": str(v_analysis["animal_id"]),
        "disease_name": f"Visual Syndromic Indicator ({dominant_ind.replace('_', ' ').title()})",
        "disease_category": "visual_surveillance",
        "symptoms": symptoms,
        "observed_signs": [dominant_ind],
        "severity": "high" if v_analysis.get("visual_risk_score", 0) >= 50 else "medium",
        "confidence": 0.75,
        "source": "ai_detection",
        "notes": notes or f"Surveillance event escalated from Visual Analysis {v_analysis.get('analysis_id')}."
    }

    created_event = create_disease_event(event_payload, current_user, db)
    return {
        "event_number": created_event["event_number"],
        "event_id": created_event["id"],
        "disease_name": created_event["disease_name"],
        "message": f"Disease surveillance event {created_event['event_number']} initiated from visual health analysis."
    }


def get_visual_health_summary(db: Any, current_user: dict) -> dict[str, Any]:
    """
    Summary KPI metrics for Visual Health dashboard and Command Center.
    """
    user_role = current_user.get("role")
    user_id = current_user.get("sub")
    query = {}

    if user_role == "farmer":
        farms = list(db.farms.find({"owner_id": user_id}))
        if not farms and ObjectId.is_valid(user_id):
            farms = list(db.farms.find({"owner_id": ObjectId(user_id)}))
        farmer_fids = [str(f["_id"]) for f in farms]
        query["farm_id"] = {"$in": farmer_fids}

    total_analyses = db.visual_analyses.count_documents(query)
    distinct_animals = len(db.visual_analyses.distinct("animal_id", query))
    total_observations = db.visual_observations.count_documents(query)

    high_risk_query = dict(query)
    high_risk_query["risk_category"] = {"$in": ["HIGH", "CRITICAL"]}
    high_risk = db.visual_analyses.count_documents(high_risk_query)

    pending_query = dict(query)
    pending_query["review_status"] = "pending"
    pending_query["requires_veterinary_review"] = True
    pending_reviews = db.visual_analyses.count_documents(pending_query)

    mm_query = dict(query)
    total_mm = db.multimodal_assessments.count_documents(mm_query)

    # Dominant visual indicators
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$indicator", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_signals = [{"indicator": doc["_id"], "count": doc["count"]} for doc in db.visual_observations.aggregate(pipeline)]

    return {
        "total_analyses": total_analyses,
        "animals_assessed": distinct_animals,
        "total_observations": total_observations,
        "high_risk_analyses": high_risk,
        "pending_reviews": pending_reviews,
        "multimodal_assessments_count": total_mm,
        "dominant_visual_signals": top_signals
    }

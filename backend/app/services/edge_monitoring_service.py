import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import time
from typing import Any, Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.schemas.edge_device import (
    EdgeInferenceEventCreate,
    EdgeInferenceEventResponse,
)
from app.services.camera_ingestion import (
    STATUS_CONNECTED,
    compute_frame_hash,
    get_camera_stream_adapter,
)
from app.services.websocket_manager import manager
from ai_engine.edge_inference import get_edge_inference_adapter
from ai_engine.multimodal_health import (
    compare_temporal_visual_analyses,
    compute_multimodal_health_assessment,
)


ALERT_COOLDOWN_MINUTES = 30


def ensure_edge_monitoring_indexes():
    """
    Ensure essential MongoDB indexes exist for edge monitoring events.
    Safe and non-destructive.
    """
    try:
        db = get_database()
        db.edge_events.create_index("event_id", unique=True)
        db.edge_events.create_index("camera_id")
        db.edge_events.create_index("edge_device_id")
        db.edge_events.create_index("animal_id")
        db.edge_events.create_index("farm_id")
        db.edge_events.create_index("frame_hash")
        db.edge_events.create_index([("captured_at", -1)])
        db.edge_events.create_index([("created_at", -1)])
        db.edge_events.create_index([("edge_device_id", 1), ("camera_id", 1), ("frame_hash", 1)])
    except Exception:
        pass


def is_alert_in_cooldown(
    db: Any,
    camera_id: str,
    animal_id: Optional[str],
    alert_type: str,
    cooldown_minutes: int = ALERT_COOLDOWN_MINUTES
) -> bool:
    """
    Prevent alert fatigue and duplicate storms.
    Checks if an alert for the same camera/animal/type was created within cooldown window.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
    query: dict[str, Any] = {
        "alert_type": alert_type,
        "camera_id": camera_id,
        "created_at": {"$gte": cutoff_time}
    }
    if animal_id:
        query["animal_id"] = str(animal_id)

    existing = db.alerts.find_one(query)
    return existing is not None


def process_edge_event(
    payload: EdgeInferenceEventCreate,
    current_user: Optional[dict] = None
) -> EdgeInferenceEventResponse:
    """
    High-throughput, safe ingestion endpoint for edge inference events.
    Executes deduplication, bounded health updates, alert evaluation with cooldown,
    disease surveillance evaluation, and real-time WebSocket distribution.
    """
    db = get_database()
    ensure_edge_monitoring_indexes()

    # 1. Validate camera exists
    camera = db.cameras.find_one({"camera_id": payload.camera_id})
    if not camera:
        return EdgeInferenceEventResponse(
            accepted=False,
            event_id=payload.frame_id,
            deduplicated=False,
            reason=f"Camera '{payload.camera_id}' does not exist in registry."
        )

    farm_id = str(camera.get("farm_id", ""))
    farm_name = camera.get("farm_name", "")
    animal_id = payload.animal_id or camera.get("animal_id")

    # 2. Event Deduplication Check
    dup_query = {
        "$or": [
            {"event_id": payload.frame_id},
            {
                "edge_device_id": payload.edge_device_id,
                "camera_id": payload.camera_id,
                "frame_hash": payload.frame_hash
            }
        ]
    }
    existing_evt = db.edge_events.find_one(dup_query)
    if existing_evt:
        return EdgeInferenceEventResponse(
            accepted=True,
            event_id=str(existing_evt.get("event_id", payload.frame_id)),
            deduplicated=True,
            reason="Duplicate event suppressed (identical frame hash / frame ID already processed).",
            visual_risk_score=float(existing_evt.get("visual_risk_score", 0.0))
        )

    # 3. Create unique event ID
    now = datetime.now(timezone.utc)
    event_id = f"EVT-{now.strftime('%Y%m%d%H%M%S')}-{payload.frame_hash[:8]}"

    # 4. Insert edge event record into MongoDB
    event_doc = {
        "event_id": event_id,
        "edge_device_id": payload.edge_device_id,
        "camera_id": payload.camera_id,
        "camera_name": camera.get("camera_name", "Camera"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "animal_id": str(animal_id) if animal_id else None,
        "captured_at": payload.captured_at,
        "frame_id": payload.frame_id,
        "frame_hash": payload.frame_hash,
        "model_name": payload.model_name,
        "model_version": payload.model_version,
        "observations": payload.observations,
        "visual_risk_score": float(payload.visual_risk_score),
        "confidence": float(payload.confidence),
        "processing_latency_ms": float(payload.processing_latency_ms),
        "created_at": now
    }
    db.edge_events.insert_one(event_doc)

    # 5. Bounded update to Camera and Edge Device stats
    db.cameras.update_one(
        {"camera_id": payload.camera_id},
        {
            "$set": {
                "last_seen": now.isoformat(),
                "last_inference_at": now.isoformat(),
                "status": "online",
                "updated_at": now
            },
            "$inc": {"inference_count": 1}
        }
    )
    if payload.edge_device_id:
        db.edge_devices.update_one(
            {"edge_device_id": payload.edge_device_id},
            {
                "$set": {
                    "last_inference_at": now.isoformat(),
                    "updated_at": now
                },
                "$inc": {"inference_count": 1}
            }
        )

    # 6. Automated Alert Evaluation with 30-min Cooldown
    alert_triggered = False
    created_alert_id = None

    # Determine candidate alert
    candidate_alert_type = None
    severity = "medium"
    alert_title = ""
    alert_msg = ""

    obs = payload.observations or {}
    posture = obs.get("posture")
    v_score = payload.visual_risk_score

    if v_score >= 0.75:
        candidate_alert_type = "visual_health_risk"
        severity = "critical" if v_score >= 0.85 else "high"
        alert_title = "Elevated Visual Health Risk Detected"
        alert_msg = f"Camera {camera.get('camera_name')} detected elevated visual risk score ({v_score:.2f})."
    elif posture and str(posture).lower() in ["abnormal", "severely_compromised", "recumbent"]:
        candidate_alert_type = "repeated_abnormal_posture"
        severity = "high"
        alert_title = "Abnormal Animal Posture / Recumbency"
        alert_msg = f"Camera {camera.get('camera_name')} observed persistent abnormal posture or prolonged recumbency."
    elif obs.get("feeding_inactivity"):
        candidate_alert_type = "feeding_inactivity"
        severity = "medium"
        alert_title = "Feeding Area Inactivity Observed"
        alert_msg = f"Prolonged inactivity detected in feeding zone for monitored group."

    # Check alert cooldown
    if candidate_alert_type:
        in_cooldown = is_alert_in_cooldown(db, payload.camera_id, animal_id, candidate_alert_type)
        if not in_cooldown:
            # Find owner of the farm to route the alert
            farm_doc = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
            owner_id = str(farm_doc.get("owner_id", "")) if farm_doc else "system"

            new_alert = {
                "owner_id": owner_id,
                "animal_id": str(animal_id) if animal_id else None,
                "alert_type": candidate_alert_type,
                "severity": severity,
                "title": alert_title,
                "message": alert_msg,
                "status": "active",
                "camera_id": payload.camera_id,
                "edge_device_id": payload.edge_device_id,
                "edge_event_id": event_id,
                "created_at": now,
                "updated_at": now
            }
            res = db.alerts.insert_one(new_alert)
            alert_triggered = True
            created_alert_id = str(res.inserted_id)

            # Broadcast alert over WebSocket
            try:
                asyncio.create_task(
                    manager.broadcast({
                        "type": "visual_alert",
                        "alert_id": created_alert_id,
                        "alert_type": candidate_alert_type,
                        "severity": severity,
                        "camera_id": payload.camera_id,
                        "title": alert_title,
                        "message": alert_msg,
                        "timestamp": now.isoformat()
                    })
                )
            except Exception:
                pass

    # 7. Disease Surveillance Signal Evaluation
    surveillance_signal = False
    if v_score >= 0.70:
        surveillance_signal = True
        # Record observation in disease_observations for Phase 8 surveillance cluster engine
        db.disease_observations.insert_one({
            "farm_id": farm_id,
            "animal_id": str(animal_id) if animal_id else None,
            "camera_id": payload.camera_id,
            "indicator": "visual_concern_detected",
            "value": v_score,
            "confidence": payload.confidence,
            "timestamp": now,
            "created_at": now
        })

    # 8. Veterinary Case Escalation
    # If visual risk is critically high (>= 0.85), escalate to veterinary workflow if no open case
    if v_score >= 0.85 and animal_id:
        existing_case = db.veterinary_cases.find_one({
            "animal_id": str(animal_id),
            "status": {"$in": ["open", "in_progress"]}
        })
        if not existing_case:
            case_year = now.year
            case_count = db.veterinary_cases.count_documents({}) + 1
            case_num = f"CASE-{case_year}-{case_count:04d}"

            farm_doc = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
            owner_id = str(farm_doc.get("owner_id", "")) if farm_doc else "system"

            new_case = {
                "case_number": case_num,
                "animal_id": str(animal_id),
                "farm_id": farm_id,
                "owner_id": owner_id,
                "title": f"Visual Triage Escalation - {camera.get('camera_name')}",
                "description": f"Automated escalation from camera edge inference. Visual concern score: {v_score:.2f}.",
                "case_type": "emergency" if v_score >= 0.90 else "illness",
                "priority": "high",
                "status": "open",
                "source": "visual_analysis",
                "alert_id": created_alert_id,
                "health_risk_score": int(v_score * 100),
                "clinical_findings": f"Observations from edge camera: {obs.get('key_findings', ['Visual concern observed'])}",
                "recommendations": "Conduct physical clinical examination to evaluate visual observations.",
                "timeline": [
                    {
                        "action": "Case Escalated via Edge Computer Vision",
                        "timestamp": now.isoformat(),
                        "notes": f"Triggered by camera {payload.camera_id} with risk score {v_score:.2f}."
                    }
                ],
                "created_at": now,
                "updated_at": now
            }
            db.veterinary_cases.insert_one(new_case)

    # 9. Real-Time WebSocket Broadcast of Inference Event
    try:
        asyncio.create_task(
            manager.broadcast({
                "type": "visual_inference",
                "event_id": event_id,
                "camera_id": payload.camera_id,
                "camera_name": camera.get("camera_name"),
                "animal_id": str(animal_id) if animal_id else None,
                "visual_risk_score": payload.visual_risk_score,
                "observations": payload.observations,
                "alert_triggered": alert_triggered,
                "timestamp": now.isoformat()
            })
        )
    except Exception:
        pass

    return EdgeInferenceEventResponse(
        accepted=True,
        event_id=event_id,
        deduplicated=False,
        visual_risk_score=payload.visual_risk_score,
        alert_triggered=alert_triggered,
        alert_id=created_alert_id,
        surveillance_signal=surveillance_signal
    )


def capture_and_analyze_camera_frame(
    camera_id: str,
    current_user: dict
) -> dict[str, Any]:
    """
    On-demand capture and live inference pipeline:
    Camera -> Frame Sampling -> Validation -> Hash -> Edge Inference ->
    Multimodal Synthesis -> Alert & Escalation -> Response.
    """
    db = get_database()
    camera = db.cameras.find_one({"camera_id": camera_id})
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    # Ingestion adapter
    adapter = get_camera_stream_adapter(camera)
    status_code, frame_arr = adapter.read_frame()

    if status_code != STATUS_CONNECTED or frame_arr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Camera capture failed with status: {status_code}"
        )

    # Acquire snapshot bytes for hashing
    _, snapshot_bytes = adapter.get_snapshot()
    if snapshot_bytes is None:
        snapshot_bytes = b"fallback-frame-bytes"
    frame_hash = compute_frame_hash(snapshot_bytes)

    # Fetch animal context if assigned
    animal_doc = None
    animal_context = None
    animal_id = camera.get("animal_id")
    if animal_id:
        a_query = {"_id": ObjectId(animal_id)} if ObjectId.is_valid(str(animal_id)) else {"_id": animal_id}
        animal_doc = db.animals.find_one(a_query)
        if not animal_doc and not ObjectId.is_valid(str(animal_id)):
            animal_doc = db.animals.find_one({"tag_id": animal_id})
        if animal_doc:
            animal_context = {
                "species": animal_doc.get("species", "cattle"),
                "breed": animal_doc.get("breed"),
                "age_months": animal_doc.get("age_months"),
                "gender": animal_doc.get("gender"),
            }

    # Execute Edge Inference Adapter
    edge_adapter = get_edge_inference_adapter()
    inference_result = edge_adapter.infer(frame_arr, animal_context=animal_context)

    # Build EdgeInferenceEventCreate
    now = datetime.now(timezone.utc)
    event_payload = EdgeInferenceEventCreate(
        edge_device_id=camera.get("edge_device_id") or "EDGE-LOCAL-01",
        camera_id=camera_id,
        animal_id=str(animal_doc["_id"]) if animal_doc else None,
        captured_at=now.isoformat(),
        frame_id=f"FRM-{camera_id}-{int(time.time()*1000)}",
        frame_hash=frame_hash,
        model_name=inference_result.get("model_name", "VETRA-EdgeVision"),
        model_version=inference_result.get("model_version", "v1.0"),
        observations=inference_result.get("observations", {}),
        visual_risk_score=inference_result.get("visual_risk_score", 0.0),
        confidence=inference_result.get("confidence", 0.85),
        processing_latency_ms=inference_result.get("processing_latency_ms", 45.0)
    )

    event_response = process_edge_event(event_payload, current_user)

    # Execute Multimodal Health Integration if animal is linked
    multimodal_result = None
    if animal_doc:
        telemetry = db.health_readings.find_one(
            {"animal_id": str(animal_doc["_id"])},
            sort=[("timestamp", -1)]
        )
        multimodal_result = compute_multimodal_health_assessment(
            animal_data=animal_doc,
            visual_analysis={"visual_risk_score": inference_result["visual_risk_score"] * 100.0},
            telemetry_risk_data={"health_risk_score": 20.0} if telemetry else None,
            disease_intelligence_data=None,
            surveillance_risk_data=None,
            preventive_status_data=None
        )

    return {
        "camera_id": camera_id,
        "camera_name": camera.get("camera_name"),
        "frame_hash": frame_hash,
        "inference": inference_result,
        "event_response": event_response.model_dump(),
        "multimodal": multimodal_result,
        "timestamp": now.isoformat()
    }


def get_camera_recent_events(
    camera_id: Optional[str] = None,
    limit: int = 20
) -> list[dict[str, Any]]:
    """Retrieve recent bounded edge events for a camera or across cameras."""
    db = get_database()
    query: dict[str, Any] = {}
    if camera_id:
        query["camera_id"] = camera_id

    cursor = db.edge_events.find(query).sort("created_at", -1).limit(min(limit, 100))
    events = []
    for doc in cursor:
        events.append({
            "id": str(doc["_id"]),
            "event_id": doc.get("event_id"),
            "edge_device_id": doc.get("edge_device_id"),
            "camera_id": doc.get("camera_id"),
            "camera_name": doc.get("camera_name"),
            "animal_id": doc.get("animal_id"),
            "captured_at": doc.get("captured_at"),
            "frame_hash": doc.get("frame_hash"),
            "visual_risk_score": doc.get("visual_risk_score", 0.0),
            "confidence": doc.get("confidence", 0.85),
            "processing_latency_ms": doc.get("processing_latency_ms", 0.0),
            "observations": doc.get("observations", {}),
            "created_at": doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at"))
        })
    return events

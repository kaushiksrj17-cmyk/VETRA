import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.schemas.camera import (
    CameraCreate,
    CameraStatus,
    CameraUpdate,
    redact_stream_url,
)
from app.services.camera_ingestion import (
    STATUS_CONNECTED,
    get_camera_stream_adapter,
)
from app.services.websocket_manager import manager


def ensure_camera_indexes():
    """
    Ensure essential MongoDB indexes exist for the cameras collection.
    Safe and non-destructive.
    """
    try:
        db = get_database()
        db.cameras.create_index("camera_id", unique=True)
        db.cameras.create_index("farm_id")
        db.cameras.create_index("animal_id")
        db.cameras.create_index("status")
        db.cameras.create_index("edge_device_id")
        db.cameras.create_index([("created_at", -1)])
        db.cameras.create_index([("last_seen", -1)])
    except Exception:
        pass


def _verify_farm_access(farm_id: str, current_user: dict, db: Any) -> dict[str, Any]:
    """Verify farm existence and farmer ownership permissions."""
    query = {"_id": ObjectId(farm_id)} if ObjectId.is_valid(farm_id) else {"_id": farm_id}
    farm = db.farms.find_one(query)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{farm_id}' not found."
        )

    user_role = current_user.get("role")
    user_id = str(current_user.get("sub", ""))
    if user_role == "farmer":
        owner_id = str(farm.get("owner_id", ""))
        if owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access cameras for your own farm."
            )
    return farm


def serialize_camera(item: dict, db: Optional[Any] = None) -> dict[str, Any]:
    """
    Transform MongoDB camera document into a sanitized, JSON-serializable dictionary.
    CRITICAL: Never exposes raw credentials or RTSP passwords.
    """
    if db is None:
        db = get_database()

    farm_id = str(item.get("farm_id", ""))
    farm_name = item.get("farm_name")
    if not farm_name and farm_id:
        f_query = {"_id": ObjectId(farm_id)} if ObjectId.is_valid(farm_id) else {"_id": farm_id}
        f_doc = db.farms.find_one(f_query)
        if f_doc:
            farm_name = f_doc.get("farm_name") or f_doc.get("name")

    animal_id = item.get("animal_id")
    animal_tag = item.get("animal_tag")
    if animal_id and not animal_tag:
        a_query = {"_id": ObjectId(animal_id)} if ObjectId.is_valid(str(animal_id)) else {"_id": animal_id}
        a_doc = db.animals.find_one(a_query)
        if a_doc:
            animal_tag = a_doc.get("tag_id")

    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")
    updated_at = item.get("updated_at")
    updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at or "")

    last_seen = item.get("last_seen")
    last_seen_str = last_seen.isoformat() if isinstance(last_seen, datetime) else (str(last_seen) if last_seen else None)

    last_frame_at = item.get("last_frame_at")
    last_frame_at_str = last_frame_at.isoformat() if isinstance(last_frame_at, datetime) else (str(last_frame_at) if last_frame_at else None)

    last_inf_at = item.get("last_inference_at")
    last_inf_at_str = last_inf_at.isoformat() if isinstance(last_inf_at, datetime) else (str(last_inf_at) if last_inf_at else None)

    # Sanitize stream URL - passwords redacted!
    redacted_url = redact_stream_url(item.get("stream_url_reference", ""))

    return {
        "id": str(item["_id"]),
        "camera_id": str(item.get("camera_id")),
        "camera_name": item.get("camera_name", "Camera"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "animal_id": str(animal_id) if animal_id else None,
        "animal_tag": animal_tag,
        "pen_id": item.get("pen_id"),
        "camera_type": item.get("camera_type", "stationary_pen"),
        "connection_type": item.get("connection_type", "mock"),
        "stream_url_reference": redacted_url or "mock://stream",
        "edge_device_id": item.get("edge_device_id"),
        "status": item.get("status", "unknown"),
        "enabled": bool(item.get("enabled", True)),
        "last_seen": last_seen_str,
        "last_frame_at": last_frame_at_str,
        "last_inference_at": last_inf_at_str,
        "fps_target": float(item.get("fps_target", 25.0)),
        "sampling_interval_seconds": float(item.get("sampling_interval_seconds", 5.0)),
        "resolution": item.get("resolution", "1920x1080"),
        "location_label": item.get("location_label", ""),
        "created_at": created_at_str,
        "updated_at": updated_at_str,
    }


def create_camera(payload: CameraCreate, current_user: dict) -> dict[str, Any]:
    """Register a new camera in the inventory with RBAC validation."""
    db = get_database()
    ensure_camera_indexes()

    farm = _verify_farm_access(payload.farm_id, current_user, db)

    # Validate animal belongs to farm if animal_id given
    animal_tag = None
    if payload.animal_id:
        a_query = {"_id": ObjectId(payload.animal_id)} if ObjectId.is_valid(payload.animal_id) else {"_id": payload.animal_id}
        animal = db.animals.find_one(a_query)
        if not animal and not ObjectId.is_valid(payload.animal_id):
            animal = db.animals.find_one({"tag_id": payload.animal_id})
        if not animal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Animal '{payload.animal_id}' not found."
            )
        animal_farm = str(animal.get("farm_id", ""))
        if animal_farm != str(farm["_id"]) and animal_farm != payload.farm_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Animal '{payload.animal_id}' does not belong to farm '{payload.farm_id}'."
            )
        animal_tag = animal.get("tag_id")

    # Generate unique camera_id
    cam_count = db.cameras.count_documents({})
    camera_id = f"CAM-{datetime.now(timezone.utc).year}-{cam_count + 1:04d}"
    while db.cameras.find_one({"camera_id": camera_id}):
        cam_count += 1
        camera_id = f"CAM-{datetime.now(timezone.utc).year}-{cam_count + 1:04d}"

    now = datetime.now(timezone.utc)
    initial_status: CameraStatus = "online" if payload.connection_type == "mock" else "unknown"

    camera_doc = {
        "camera_id": camera_id,
        "camera_name": payload.camera_name,
        "farm_id": payload.farm_id,
        "farm_name": farm.get("farm_name") or farm.get("name"),
        "animal_id": payload.animal_id,
        "animal_tag": animal_tag,
        "pen_id": payload.pen_id,
        "camera_type": payload.camera_type,
        "connection_type": payload.connection_type,
        # Store stream reference securely
        "stream_url_reference": payload.stream_url_reference,
        "edge_device_id": payload.edge_device_id,
        "enabled": payload.enabled,
        "status": initial_status,
        "fps_target": payload.fps_target,
        "sampling_interval_seconds": payload.sampling_interval_seconds,
        "resolution": payload.resolution,
        "location_label": payload.location_label,
        "last_seen": now.isoformat() if initial_status == "online" else None,
        "last_frame_at": now.isoformat() if initial_status == "online" else None,
        "last_inference_at": None,
        "consecutive_failures": 0,
        "frames_received": 0,
        "frames_dropped": 0,
        "inference_count": 0,
        "average_inference_latency_ms": 0.0,
        "created_by": str(current_user.get("sub", "")),
        "created_at": now,
        "updated_at": now,
    }

    insert_result = db.cameras.insert_one(camera_doc)
    camera_doc["_id"] = insert_result.inserted_id

    # Broadcast camera registration over WebSocket
    try:
        asyncio.create_task(
            manager.broadcast({
                "type": "camera_registered",
                "camera_id": camera_id,
                "camera_name": payload.camera_name,
                "farm_id": payload.farm_id,
                "status": initial_status,
                "timestamp": now.isoformat(),
            })
        )
    except Exception:
        pass

    return serialize_camera(camera_doc, db)


def get_cameras(
    current_user: dict,
    farm_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    camera_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Query cameras respecting RBAC and optional filters."""
    db = get_database()
    query: dict[str, Any] = {}

    user_role = current_user.get("role")
    user_id = str(current_user.get("sub", ""))

    if user_role == "farmer":
        farmer_farms = list(db.farms.find({"owner_id": user_id}, {"_id": 1}))
        farm_ids = [str(f["_id"]) for f in farmer_farms]
        if farm_id:
            if farm_id not in farm_ids:
                return []
            query["farm_id"] = farm_id
        else:
            query["farm_id"] = {"$in": farm_ids}
    elif farm_id:
        query["farm_id"] = farm_id

    if animal_id:
        query["animal_id"] = animal_id
    if status_filter:
        query["status"] = status_filter
    if camera_type:
        query["camera_type"] = camera_type

    cursor = db.cameras.find(query).sort("created_at", -1)
    return [serialize_camera(doc, db) for doc in cursor]


def get_camera_by_id(camera_id: str, current_user: dict) -> dict[str, Any]:
    """Retrieve a single camera by ID with ownership verification."""
    db = get_database()
    query = {"camera_id": camera_id}
    if ObjectId.is_valid(camera_id):
        query = {"$or": [{"camera_id": camera_id}, {"_id": ObjectId(camera_id)}]}

    doc = db.cameras.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    # RBAC check
    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    return serialize_camera(doc, db)


def update_camera(camera_id: str, payload: CameraUpdate, current_user: dict) -> dict[str, Any]:
    """Update camera configuration and metadata."""
    db = get_database()
    query = {"camera_id": camera_id}
    if ObjectId.is_valid(camera_id):
        query = {"$or": [{"camera_id": camera_id}, {"_id": ObjectId(camera_id)}]}

    doc = db.cameras.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    update_fields: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if payload.camera_name is not None:
        update_fields["camera_name"] = payload.camera_name
    if payload.animal_id is not None:
        update_fields["animal_id"] = payload.animal_id
    if payload.pen_id is not None:
        update_fields["pen_id"] = payload.pen_id
    if payload.camera_type is not None:
        update_fields["camera_type"] = payload.camera_type
    if payload.connection_type is not None:
        update_fields["connection_type"] = payload.connection_type
    if payload.stream_url_reference is not None:
        update_fields["stream_url_reference"] = payload.stream_url_reference
    if payload.edge_device_id is not None:
        update_fields["edge_device_id"] = payload.edge_device_id
    if payload.enabled is not None:
        update_fields["enabled"] = payload.enabled
    if payload.status is not None:
        update_fields["status"] = payload.status
    if payload.fps_target is not None:
        update_fields["fps_target"] = payload.fps_target
    if payload.sampling_interval_seconds is not None:
        update_fields["sampling_interval_seconds"] = payload.sampling_interval_seconds
    if payload.resolution is not None:
        update_fields["resolution"] = payload.resolution
    if payload.location_label is not None:
        update_fields["location_label"] = payload.location_label

    db.cameras.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    updated_doc = db.cameras.find_one({"_id": doc["_id"]})
    return serialize_camera(updated_doc, db)


def delete_camera(camera_id: str, current_user: dict) -> dict[str, Any]:
    """
    Soft-delete / disable camera per Phase 10 non-destructive safety guidelines.
    Sets enabled=False and status='disabled'.
    """
    db = get_database()
    query = {"camera_id": camera_id}
    if ObjectId.is_valid(camera_id):
        query = {"$or": [{"camera_id": camera_id}, {"_id": ObjectId(camera_id)}]}

    doc = db.cameras.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    now = datetime.now(timezone.utc)
    db.cameras.update_one(
        {"_id": doc["_id"]},
        {"$set": {"enabled": False, "status": "disabled", "updated_at": now}}
    )
    return {"message": f"Camera '{camera_id}' disabled successfully.", "status": "disabled"}


def test_camera_connection(camera_id: str, current_user: dict) -> dict[str, Any]:
    """Test camera live connectivity, verify stream, and update bounded health metrics."""
    db = get_database()
    doc = db.cameras.find_one({"camera_id": camera_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    adapter = get_camera_stream_adapter(doc)
    start_t = time.perf_counter()
    status_code, frame_bytes = adapter.get_snapshot()
    latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

    now = datetime.now(timezone.utc)
    if status_code == STATUS_CONNECTED and frame_bytes is not None:
        new_status = "online"
        db.cameras.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": new_status,
                    "last_seen": now.isoformat(),
                    "last_frame_at": now.isoformat(),
                    "consecutive_failures": 0,
                    "updated_at": now,
                },
                "$inc": {"frames_received": 1},
            },
        )
        return {
            "camera_id": camera_id,
            "connected": True,
            "status": "online",
            "latency_ms": latency_ms,
            "message": "Camera stream responsive and frame captured.",
            "frame_captured": True,
            "resolution": doc.get("resolution", "1920x1080"),
        }
    else:
        new_status = "offline" if status_code == "offline" else "degraded"
        db.cameras.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {"status": new_status, "updated_at": now},
                "$inc": {"consecutive_failures": 1, "frames_dropped": 1},
            },
        )
        return {
            "camera_id": camera_id,
            "connected": False,
            "status": new_status,
            "latency_ms": latency_ms,
            "message": f"Connection check failed: {status_code}",
            "frame_captured": False,
            "resolution": None,
        }


def get_camera_snapshot(camera_id: str, current_user: dict) -> Tuple[bytes, str]:
    """Capture a single on-demand still snapshot from the camera stream."""
    db = get_database()
    doc = db.cameras.find_one({"camera_id": camera_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    if not doc.get("enabled", True) or doc.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot capture snapshot: camera is disabled."
        )

    adapter = get_camera_stream_adapter(doc)
    status_code, snapshot_bytes = adapter.get_snapshot()

    now = datetime.now(timezone.utc)
    if status_code != STATUS_CONNECTED or snapshot_bytes is None:
        db.cameras.update_one(
            {"_id": doc["_id"]},
            {"$inc": {"consecutive_failures": 1}, "$set": {"status": "degraded", "updated_at": now}}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Camera stream unavailable: {status_code}"
        )

    # Bounded update of last seen and frames received
    db.cameras.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"last_seen": now.isoformat(), "last_frame_at": now.isoformat(), "updated_at": now},
            "$inc": {"frames_received": 1},
        }
    )

    return snapshot_bytes, "image/jpeg"


def get_camera_health(camera_id: str, current_user: dict) -> dict[str, Any]:
    """Calculate and return operational health metrics for a camera."""
    db = get_database()
    doc = db.cameras.find_one({"camera_id": camera_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    status_val = doc.get("status", "unknown")
    failures = int(doc.get("consecutive_failures", 0))
    enabled = bool(doc.get("enabled", True))

    if not enabled or status_val == "disabled":
        tier = "DISABLED"
        msg = "Camera administratively disabled."
    elif status_val == "online" and failures == 0:
        tier = "HEALTHY"
        msg = "Camera operational and responsive."
    elif status_val == "degraded" or (failures > 0 and failures < 5):
        tier = "DEGRADED"
        msg = f"Camera experiencing degraded stream performance ({failures} failures)."
    else:
        tier = "OFFLINE"
        msg = "Camera offline or unreachable."

    frames_rec = int(doc.get("frames_received", 0))
    frames_drop = int(doc.get("frames_dropped", 0))
    total_frames = frames_rec + frames_drop
    uptime_pct = round((frames_rec / total_frames * 100.0) if total_frames > 0 else 100.0, 1)

    return {
        "camera_id": camera_id,
        "camera_name": doc.get("camera_name", "Camera"),
        "status": status_val,
        "health_tier": tier,
        "last_seen": doc.get("last_seen"),
        "last_frame_at": doc.get("last_frame_at"),
        "last_inference_at": doc.get("last_inference_at"),
        "consecutive_failures": failures,
        "frames_received": frames_rec,
        "frames_dropped": frames_drop,
        "inference_count": int(doc.get("inference_count", 0)),
        "average_inference_latency_ms": float(doc.get("average_inference_latency_ms", 0.0)),
        "uptime_estimate_pct": uptime_pct,
        "connection_message": msg,
    }


def get_camera_summary(current_user: dict) -> dict[str, Any]:
    """Aggregate high-level camera health and count metrics."""
    db = get_database()
    query: dict[str, Any] = {}

    user_role = current_user.get("role")
    user_id = str(current_user.get("sub", ""))

    if user_role == "farmer":
        farmer_farms = list(db.farms.find({"owner_id": user_id}, {"_id": 1}))
        farm_ids = [str(f["_id"]) for f in farmer_farms]
        query["farm_id"] = {"$in": farm_ids}

    cameras = list(db.cameras.find(query))
    total = len(cameras)
    online = sum(1 for c in cameras if c.get("status") == "online")
    degraded = sum(1 for c in cameras if c.get("status") == "degraded")
    offline = sum(1 for c in cameras if c.get("status") == "offline")
    disabled = sum(1 for c in cameras if not c.get("enabled", True) or c.get("status") == "disabled")

    by_type: dict[str, int] = {}
    by_conn: dict[str, int] = {}
    for c in cameras:
        ct = c.get("camera_type", "stationary_pen")
        by_type[ct] = by_type.get(ct, 0) + 1
        cn = c.get("connection_type", "mock")
        by_conn[cn] = by_conn.get(cn, 0) + 1

    return {
        "total_cameras": total,
        "online_cameras": online,
        "degraded_cameras": degraded,
        "offline_cameras": offline,
        "disabled_cameras": disabled,
        "by_type": by_type,
        "by_connection": by_conn,
    }

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.schemas.edge_device import (
    EdgeDeviceCreate,
    EdgeDeviceHeartbeat,
    EdgeDeviceUpdate,
)
from app.services.websocket_manager import manager


def ensure_edge_device_indexes():
    """
    Ensure essential MongoDB indexes exist for the edge_devices collection.
    Safe and non-destructive.
    """
    try:
        db = get_database()
        db.edge_devices.create_index("edge_device_id", unique=True)
        db.edge_devices.create_index("farm_id")
        db.edge_devices.create_index("device_type")
        db.edge_devices.create_index("status")
        db.edge_devices.create_index([("created_at", -1)])
        db.edge_devices.create_index([("last_heartbeat", -1)])
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
                detail="Access denied: You can only manage edge devices for your own farm."
            )
    return farm


def serialize_edge_device(item: dict, db: Optional[Any] = None) -> dict[str, Any]:
    """Serialize MongoDB edge device doc into a standardized dictionary."""
    if db is None:
        db = get_database()

    farm_id = str(item.get("farm_id", ""))
    farm_name = item.get("farm_name")
    if not farm_name and farm_id:
        f_query = {"_id": ObjectId(farm_id)} if ObjectId.is_valid(farm_id) else {"_id": farm_id}
        f_doc = db.farms.find_one(f_query)
        if f_doc:
            farm_name = f_doc.get("farm_name") or f_doc.get("name")

    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")
    updated_at = item.get("updated_at")
    updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at or "")

    last_hb = item.get("last_heartbeat")
    last_hb_str = last_hb.isoformat() if isinstance(last_hb, datetime) else (str(last_hb) if last_hb else None)

    last_inf = item.get("last_inference_at")
    last_inf_str = last_inf.isoformat() if isinstance(last_inf, datetime) else (str(last_inf) if last_inf else None)

    return {
        "id": str(item["_id"]),
        "edge_device_id": str(item.get("edge_device_id")),
        "device_name": item.get("device_name", "Edge Node"),
        "device_type": item.get("device_type", "mini_pc"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "status": item.get("status", "offline"),
        "ip_address": item.get("ip_address"),
        "software_version": item.get("software_version", "1.0.0"),
        "model_version": item.get("model_version", "v1.0"),
        "last_heartbeat": last_hb_str,
        "last_inference_at": last_inf_str,
        "cpu_usage_pct": item.get("cpu_usage_pct"),
        "memory_usage_pct": item.get("memory_usage_pct"),
        "temperature_celsius": item.get("temperature_celsius"),
        "camera_ids": item.get("camera_ids", []),
        "capabilities": item.get("capabilities", []),
        "created_at": created_at_str,
        "updated_at": updated_at_str,
    }


def create_edge_device(payload: EdgeDeviceCreate, current_user: dict) -> dict[str, Any]:
    """Register a new edge device node."""
    db = get_database()
    ensure_edge_device_indexes()

    farm = _verify_farm_access(payload.farm_id, current_user, db)

    dev_count = db.edge_devices.count_documents({})
    edge_device_id = f"EDGE-{datetime.now(timezone.utc).year}-{dev_count + 1:04d}"
    while db.edge_devices.find_one({"edge_device_id": edge_device_id}):
        dev_count += 1
        edge_device_id = f"EDGE-{datetime.now(timezone.utc).year}-{dev_count + 1:04d}"

    now = datetime.now(timezone.utc)
    doc = {
        "edge_device_id": edge_device_id,
        "device_name": payload.device_name,
        "device_type": payload.device_type,
        "farm_id": payload.farm_id,
        "farm_name": farm.get("farm_name") or farm.get("name"),
        "status": payload.status,
        "ip_address": payload.ip_address,
        "software_version": payload.software_version,
        "model_version": payload.model_version,
        "last_heartbeat": now.isoformat() if payload.status == "online" else None,
        "last_inference_at": None,
        "cpu_usage_pct": 12.5 if payload.status == "online" else None,
        "memory_usage_pct": 28.0 if payload.status == "online" else None,
        "temperature_celsius": 42.0 if payload.status == "online" else None,
        "camera_ids": payload.camera_ids,
        "capabilities": payload.capabilities,
        "created_by": str(current_user.get("sub", "")),
        "created_at": now,
        "updated_at": now,
    }

    insert_result = db.edge_devices.insert_one(doc)
    doc["_id"] = insert_result.inserted_id

    # Broadcast edge device registration
    try:
        asyncio.create_task(
            manager.broadcast({
                "type": "edge_device_registered",
                "edge_device_id": edge_device_id,
                "device_name": payload.device_name,
                "farm_id": payload.farm_id,
                "status": payload.status,
                "timestamp": now.isoformat(),
            })
        )
    except Exception:
        pass

    return serialize_edge_device(doc, db)


def get_edge_devices(
    current_user: dict,
    farm_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Query edge devices with farmer data isolation and filters."""
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

    if device_type:
        query["device_type"] = device_type
    if status_filter:
        query["status"] = status_filter

    cursor = db.edge_devices.find(query).sort("created_at", -1)
    return [serialize_edge_device(doc, db) for doc in cursor]


def get_edge_device_by_id(device_id: str, current_user: dict) -> dict[str, Any]:
    """Retrieve an edge device by ID."""
    db = get_database()
    query = {"edge_device_id": device_id}
    if ObjectId.is_valid(device_id):
        query = {"$or": [{"edge_device_id": device_id}, {"_id": ObjectId(device_id)}]}

    doc = db.edge_devices.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge device '{device_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    return serialize_edge_device(doc, db)


def update_edge_device(device_id: str, payload: EdgeDeviceUpdate, current_user: dict) -> dict[str, Any]:
    """Update edge device parameters."""
    db = get_database()
    query = {"edge_device_id": device_id}
    if ObjectId.is_valid(device_id):
        query = {"$or": [{"edge_device_id": device_id}, {"_id": ObjectId(device_id)}]}

    doc = db.edge_devices.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge device '{device_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    update_fields: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if payload.device_name is not None:
        update_fields["device_name"] = payload.device_name
    if payload.device_type is not None:
        update_fields["device_type"] = payload.device_type
    if payload.farm_id is not None:
        _verify_farm_access(payload.farm_id, current_user, db)
        update_fields["farm_id"] = payload.farm_id
    if payload.ip_address is not None:
        update_fields["ip_address"] = payload.ip_address
    if payload.software_version is not None:
        update_fields["software_version"] = payload.software_version
    if payload.model_version is not None:
        update_fields["model_version"] = payload.model_version
    if payload.camera_ids is not None:
        update_fields["camera_ids"] = payload.camera_ids
    if payload.capabilities is not None:
        update_fields["capabilities"] = payload.capabilities
    if payload.status is not None:
        update_fields["status"] = payload.status

    db.edge_devices.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    updated_doc = db.edge_devices.find_one({"_id": doc["_id"]})
    return serialize_edge_device(updated_doc, db)


def record_heartbeat(device_id: str, payload: EdgeDeviceHeartbeat, current_user: dict) -> dict[str, Any]:
    """Ingest edge node heartbeat telemetry."""
    db = get_database()
    doc = db.edge_devices.find_one({"edge_device_id": device_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge device '{device_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    now = datetime.now(timezone.utc)
    update_fields: dict[str, Any] = {
        "last_heartbeat": now.isoformat(),
        "status": "online",
        "updated_at": now,
    }
    if payload.software_version:
        update_fields["software_version"] = payload.software_version
    if payload.model_version:
        update_fields["model_version"] = payload.model_version
    if payload.cpu_usage_pct is not None:
        update_fields["cpu_usage_pct"] = payload.cpu_usage_pct
    if payload.memory_usage_pct is not None:
        update_fields["memory_usage_pct"] = payload.memory_usage_pct
    if payload.temperature_celsius is not None:
        update_fields["temperature_celsius"] = payload.temperature_celsius

    db.edge_devices.update_one({"_id": doc["_id"]}, {"$set": update_fields})

    # Broadcast heartbeat status via WebSocket
    try:
        asyncio.create_task(
            manager.broadcast({
                "type": "edge_device_heartbeat",
                "edge_device_id": device_id,
                "status": "online",
                "cpu_usage_pct": payload.cpu_usage_pct,
                "memory_usage_pct": payload.memory_usage_pct,
                "temperature_celsius": payload.temperature_celsius,
                "timestamp": now.isoformat(),
            })
        )
    except Exception:
        pass

    return {
        "edge_device_id": device_id,
        "status": "online",
        "heartbeat_received_at": now.isoformat(),
        "buffered_events_reported": payload.buffered_events_count or 0,
    }


def get_edge_device_health(device_id: str, current_user: dict) -> dict[str, Any]:
    """Calculate and return health tier for an edge device."""
    db = get_database()
    doc = db.edge_devices.find_one({"edge_device_id": device_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge device '{device_id}' not found."
        )

    farm_id = str(doc.get("farm_id", ""))
    _verify_farm_access(farm_id, current_user, db)

    status_val = doc.get("status", "offline")
    last_hb = doc.get("last_heartbeat")
    hb_age_sec: Optional[float] = None
    if last_hb:
        try:
            hb_dt = datetime.fromisoformat(last_hb) if isinstance(last_hb, str) else last_hb
            hb_age_sec = max(0.0, (datetime.now(timezone.utc) - hb_dt).total_seconds())
        except Exception:
            pass

    # Tier evaluation
    cpu = doc.get("cpu_usage_pct")
    temp = doc.get("temperature_celsius")
    if status_val == "disabled":
        tier = "DISABLED"
        summary = "Device disabled."
    elif hb_age_sec is not None and hb_age_sec > 180:
        tier = "OFFLINE"
        summary = f"Heartbeat missed (last seen {int(hb_age_sec)}s ago)."
    elif (cpu and cpu > 90.0) or (temp and temp > 80.0):
        tier = "DEGRADED"
        summary = "Device under high thermal or CPU load."
    elif status_val == "online":
        tier = "HEALTHY"
        summary = "Edge node healthy and reporting normal telemetry."
    else:
        tier = "OFFLINE"
        summary = "Device offline or status unknown."

    # Active cameras count
    cams = doc.get("camera_ids", [])

    return {
        "edge_device_id": device_id,
        "device_name": doc.get("device_name", "Edge Node"),
        "status": status_val,
        "health_tier": tier,
        "last_heartbeat": last_hb,
        "heartbeat_age_seconds": hb_age_sec,
        "cpu_usage_pct": cpu,
        "memory_usage_pct": doc.get("memory_usage_pct"),
        "temperature_celsius": temp,
        "active_camera_count": len(cams),
        "inference_count": int(doc.get("inference_count", 0)),
        "health_summary": summary,
    }


def get_edge_device_summary(current_user: dict) -> dict[str, Any]:
    """Aggregate summary statistics for edge devices."""
    db = get_database()
    query: dict[str, Any] = {}

    user_role = current_user.get("role")
    user_id = str(current_user.get("sub", ""))

    if user_role == "farmer":
        farmer_farms = list(db.farms.find({"owner_id": user_id}, {"_id": 1}))
        farm_ids = [str(f["_id"]) for f in farmer_farms]
        query["farm_id"] = {"$in": farm_ids}

    devices = list(db.edge_devices.find(query))
    total = len(devices)
    online = sum(1 for d in devices if d.get("status") == "online")
    degraded = sum(1 for d in devices if d.get("status") == "degraded")
    offline = sum(1 for d in devices if d.get("status") == "offline")
    disabled = sum(1 for d in devices if d.get("status") == "disabled")

    by_type: dict[str, int] = {}
    for d in devices:
        dt = d.get("device_type", "mini_pc")
        by_type[dt] = by_type.get(dt, 0) + 1

    return {
        "total_devices": total,
        "online_devices": online,
        "degraded_devices": degraded,
        "offline_devices": offline,
        "disabled_devices": disabled,
        "by_type": by_type,
    }

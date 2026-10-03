from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import require_farmer, require_any_authenticated_user
from app.services.websocket_manager import manager
from app.services.alert_engine import evaluate_health_risk
from app.schemas.health import (
    HealthReadingCreate,
    HealthReadingResponse
)


router = APIRouter(
    prefix="/health-readings",
    tags=["Health Monitoring"]
)

# Cooldown period (in seconds) to prevent duplicate alert spam for the same condition
ALERT_COOLDOWN_SECONDS = 300


@router.post(
    "",
    response_model=HealthReadingResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_health_reading(
    reading: HealthReadingCreate,
    current_user: dict = Depends(require_farmer)
):
    """
    Store a health reading for an animal owned
    by the authenticated farmer, evaluate health risks,
    generate alerts if abnormalities are found,
    and broadcast updates in real time via WebSockets.
    """

    db = get_database()

    user_id = current_user["sub"]

    # --------------------------------------------------------
    # Validate animal ID
    # --------------------------------------------------------

    if not ObjectId.is_valid(reading.animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    # --------------------------------------------------------
    # Find the animal
    # --------------------------------------------------------

    animal = db.animals.find_one({
        "_id": ObjectId(reading.animal_id),
        "owner_id": user_id
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    # --------------------------------------------------------
    # Create timestamps
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    recorded_at = (
        reading.recorded_at
        if reading.recorded_at
        else now
    )

    # --------------------------------------------------------
    # Create database document
    # --------------------------------------------------------

    new_reading = {
        "animal_id": reading.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": user_id,
        "device_id": reading.device_id,
        "temperature_c": reading.temperature_c,
        "heart_rate_bpm": reading.heart_rate_bpm,
        "activity_level": reading.activity_level,
        "rumination_level": reading.rumination_level,
        "respiratory_rate": reading.respiratory_rate,
        "source": reading.source,
        "recorded_at": recorded_at,
        "created_at": now
    }

    # --------------------------------------------------------
    # Store reading in MongoDB
    # --------------------------------------------------------

    result = db.health_readings.insert_one(
        new_reading
    )

    # --------------------------------------------------------
    # Broadcast real-time reading
    # --------------------------------------------------------

    await manager.broadcast({
        "type": "health_reading",
        "data": {
            "id": str(result.inserted_id),
            "animal_id": new_reading["animal_id"],
            "device_id": new_reading["device_id"],
            "temperature_c": new_reading["temperature_c"],
            "heart_rate_bpm": new_reading["heart_rate_bpm"],
            "activity_level": new_reading["activity_level"],
            "rumination_level": new_reading["rumination_level"],
            "respiratory_rate": new_reading["respiratory_rate"],
            "source": new_reading["source"],
            "recorded_at": recorded_at.isoformat(),
            "created_at": now.isoformat()
        }
    })

    # --------------------------------------------------------
    # Evaluate health risk with alert rule engine
    # --------------------------------------------------------

    evaluation = evaluate_health_risk(
        temperature_c=new_reading["temperature_c"],
        heart_rate_bpm=new_reading["heart_rate_bpm"],
        activity_level=new_reading["activity_level"],
        rumination_level=new_reading["rumination_level"],
        respiratory_rate=new_reading["respiratory_rate"]
    )

    # --------------------------------------------------------
    # Generate and broadcast alert if abnormal signs detected
    # --------------------------------------------------------

    if evaluation["has_alert"]:

        cooldown_cutoff = now - timedelta(seconds=ALERT_COOLDOWN_SECONDS)

        # Check for active alert of the same type within the cooldown period
        existing_alert = db.alerts.find_one({
            "animal_id": new_reading["animal_id"],
            "alert_type": evaluation["alert_type"],
            "status": "active",
            "created_at": {"$gte": cooldown_cutoff}
        })

        severity_rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }

        should_create_alert = True

        if existing_alert:
            existing_rank = severity_rank.get(
                existing_alert.get("severity", "low"), 1
            )
            new_rank = severity_rank.get(
                evaluation["severity"], 1
            )

            # Suppress duplicate alert if severity has not escalated
            if new_rank <= existing_rank:
                should_create_alert = False

        if should_create_alert:

            new_alert = {
                "animal_id": new_reading["animal_id"],
                "farm_id": new_reading["farm_id"],
                "owner_id": new_reading["owner_id"],
                "device_id": new_reading["device_id"],
                "alert_type": evaluation["alert_type"],
                "severity": evaluation["severity"],
                "title": evaluation["title"],
                "message": evaluation["message"],
                "triggered_by": evaluation["triggered_by"],
                "status": "active",
                "health_reading_id": str(result.inserted_id),
                "created_at": now,
                "acknowledged_at": None,
                "resolved_at": None
            }

            alert_result = db.alerts.insert_one(new_alert)

            # Broadcast alert to real-time WebSocket clients
            await manager.broadcast({
                "type": "alert",
                "data": {
                    "id": str(alert_result.inserted_id),
                    "animal_id": new_alert["animal_id"],
                    "farm_id": new_alert["farm_id"],
                    "owner_id": new_alert["owner_id"],
                    "device_id": new_alert["device_id"],
                    "alert_type": new_alert["alert_type"],
                    "severity": new_alert["severity"],
                    "title": new_alert["title"],
                    "message": new_alert["message"],
                    "triggered_by": new_alert["triggered_by"],
                    "status": new_alert["status"],
                    "health_reading_id": new_alert["health_reading_id"],
                    "created_at": now.isoformat(),
                    "acknowledged_at": None,
                    "resolved_at": None
                }
            })

    # --------------------------------------------------------
    # Return API response
    # --------------------------------------------------------

    return HealthReadingResponse(
        id=str(result.inserted_id),
        animal_id=new_reading["animal_id"],
        device_id=new_reading["device_id"],
        temperature_c=new_reading["temperature_c"],
        heart_rate_bpm=new_reading["heart_rate_bpm"],
        activity_level=new_reading["activity_level"],
        rumination_level=new_reading["rumination_level"],
        respiratory_rate=new_reading["respiratory_rate"],
        source=new_reading["source"],
        recorded_at=recorded_at.isoformat(),
        created_at=now.isoformat()
    )


@router.get(
    "",
    response_model=list[HealthReadingResponse]
)
def get_all_health_readings(
    limit: int = Query(50, ge=1, le=200, description="Max readings to retrieve"),
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    animal_id: Optional[str] = Query(None, description="Optional animal ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve recent health readings across the herd with animal identity
    and vital risk status.
    """
    db = get_database()
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer").lower()

    query: dict = {}
    if role == "farmer":
        query["owner_id"] = user_id

    if farm_id and farm_id != "all":
        query["farm_id"] = farm_id

    if animal_id and animal_id != "all":
        query["animal_id"] = animal_id

    readings_cursor = db.health_readings.find(query).sort("recorded_at", -1).limit(min(limit, 200))
    readings = list(readings_cursor)

    # Preload animals for identity enrichment
    animal_ids = {r.get("animal_id") for r in readings if r.get("animal_id")}
    valid_obj_ids = [ObjectId(aid) for aid in animal_ids if ObjectId.is_valid(aid)]
    animal_map = {}
    if valid_obj_ids:
        animals_cursor = db.animals.find({"_id": {"$in": valid_obj_ids}})
        animal_map = {str(a["_id"]): a for a in animals_cursor}

    results = []
    for item in readings:
        a_id = str(item.get("animal_id", ""))
        anim = animal_map.get(a_id, {})

        # Evaluate risk status
        risk_status = "normal"
        t = float(item.get("temperature_c", 38.5))
        hr = float(item.get("heart_rate_bpm", 70))
        rr = float(item.get("respiratory_rate", 20))
        act = float(item.get("activity_level", 75))
        rum = float(item.get("rumination_level", 80))

        if t >= 40.5 or t < 36.0 or hr >= 130 or hr < 40:
            risk_status = "critical"
        elif t >= 39.5 or t < 37.0 or hr >= 110 or hr < 50 or rr >= 45 or rr < 10:
            risk_status = "high"
        elif act < 25 or rum < 30 or rr >= 35:
            risk_status = "medium"

        recorded = item.get("recorded_at")
        created = item.get("created_at")
        rec_str = recorded.isoformat() if isinstance(recorded, datetime) else str(recorded or "")
        cre_str = created.isoformat() if isinstance(created, datetime) else str(created or "")

        results.append(
            HealthReadingResponse(
                id=str(item["_id"]),
                animal_id=a_id,
                device_id=item.get("device_id", "UNKNOWN"),
                temperature_c=t,
                heart_rate_bpm=hr,
                activity_level=act,
                rumination_level=rum,
                respiratory_rate=rr,
                source=item.get("source", "simulator"),
                recorded_at=rec_str,
                created_at=cre_str,
                animal_name=anim.get("name"),
                tag_id=anim.get("tag_id"),
                species=anim.get("species"),
                risk_status=risk_status,
                farm_id=str(item.get("farm_id") or anim.get("farm_id") or "")
            )
        )

    return results


@router.get(
    "/animal/{animal_id}",
    response_model=list[HealthReadingResponse]
)
def get_animal_health_readings(
    animal_id: str,
    current_user: dict = Depends(require_farmer)
):
    """
    Get health readings for an animal owned
    by the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    # --------------------------------------------------------
    # Validate animal ID
    # --------------------------------------------------------

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    # --------------------------------------------------------
    # Find the animal
    # --------------------------------------------------------

    animal = db.animals.find_one({
        "_id": ObjectId(animal_id),
        "owner_id": user_id
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    # --------------------------------------------------------
    # Get readings
    # --------------------------------------------------------

    readings = db.health_readings.find({
        "animal_id": animal_id,
        "owner_id": user_id
    }).sort(
        "recorded_at",
        -1
    )

    results = []

    for item in readings:

        results.append(
            HealthReadingResponse(
                id=str(item["_id"]),
                animal_id=item["animal_id"],
                device_id=item["device_id"],
                temperature_c=item["temperature_c"],
                heart_rate_bpm=item["heart_rate_bpm"],
                activity_level=item["activity_level"],
                rumination_level=item["rumination_level"],
                respiratory_rate=item["respiratory_rate"],
                source=item["source"],
                recorded_at=item["recorded_at"].isoformat(),
                created_at=item["created_at"].isoformat()
            )
        )

    return results
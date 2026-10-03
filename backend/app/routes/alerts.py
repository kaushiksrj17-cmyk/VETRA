from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import require_any_authenticated_user
from app.schemas.alert import AlertResponse, AlertSeverity, AlertStatus
from app.services.preventive_alert_engine import (
    generate_preventive_alerts,
)
from app.services.websocket_manager import manager


router = APIRouter(
    prefix="/alerts",
    tags=["Alert Management"]
)


def ensure_alert_indexes():
    """
    Ensure essential MongoDB indexes exist for the alerts collection.
    """
    try:
        db = get_database()

        db.alerts.create_index("owner_id")
        db.alerts.create_index("animal_id")
        db.alerts.create_index("status")
        db.alerts.create_index("severity")
        db.alerts.create_index([("created_at", -1)])

        # Preventive alert lookup / duplicate protection.
        db.alerts.create_index(
            "preventive_event_key"
        )

    except Exception:
        pass


def _sync_preventive_alerts(
    current_user: dict
):
    """
    Automatically synchronize preventive-care alerts.

    Farmers:
        Only their own preventive records are processed.

    Veterinarians / Administrators:
        System-wide preventive records are processed.
    """

    user_role = current_user.get("role")
    user_id = current_user["sub"]

    if user_role == "farmer":
        return generate_preventive_alerts(
            owner_id=user_id
        )

    return generate_preventive_alerts()


def serialize_alert(item: dict) -> AlertResponse:
    """
    Helper function to transform a MongoDB alert document
    into an AlertResponse.
    """

    created_at = item.get("created_at")

    if isinstance(created_at, datetime):
        created_at_str = created_at.isoformat()
    else:
        created_at_str = str(created_at)

    acknowledged_at = item.get("acknowledged_at")

    if isinstance(acknowledged_at, datetime):
        acknowledged_at_str = acknowledged_at.isoformat()
    elif acknowledged_at:
        acknowledged_at_str = str(acknowledged_at)
    else:
        acknowledged_at_str = None

    resolved_at = item.get("resolved_at")

    if isinstance(resolved_at, datetime):
        resolved_at_str = resolved_at.isoformat()
    elif resolved_at:
        resolved_at_str = str(resolved_at)
    else:
        resolved_at_str = None

    return AlertResponse(
        id=str(item["_id"]),
        animal_id=str(item["animal_id"]),
        farm_id=str(item["farm_id"]),
        owner_id=str(item["owner_id"]),
        device_id=str(item.get("device_id") or "SYSTEM"),
        alert_type=item["alert_type"],
        severity=item["severity"],
        title=item["title"],
        message=item["message"],
        triggered_by=item.get(
            "triggered_by",
            []
        ),
        status=item["status"],
        health_reading_id=(
            str(item["health_reading_id"])
            if item.get("health_reading_id")
            else None
        ),
        created_at=created_at_str,
        acknowledged_at=acknowledged_at_str,
        acknowledged_by=item.get(
            "acknowledged_by"
        ),
        resolved_at=resolved_at_str,
        resolved_by=item.get(
            "resolved_by"
        ),
        preventive_record_id=(
            str(item["preventive_record_id"])
            if item.get("preventive_record_id")
            else None
        ),
        preventive_category=item.get("preventive_category"),
        preventive_due_date=item.get("preventive_due_date"),
        visual_analysis_id=(
            str(item["visual_analysis_id"])
            if item.get("visual_analysis_id")
            else None
        ),
        multimodal_assessment_id=(
            str(item["multimodal_assessment_id"])
            if item.get("multimodal_assessment_id")
            else None
        ),
        camera_id=(
            str(item["camera_id"])
            if item.get("camera_id")
            else None
        ),
        edge_device_id=(
            str(item["edge_device_id"])
            if item.get("edge_device_id")
            else None
        ),
        edge_event_id=(
            str(item["edge_event_id"])
            if item.get("edge_event_id")
            else None
        ),
    )



@router.get(
    "",
    response_model=list[AlertResponse]
)
def get_alerts(
    severity: Optional[AlertSeverity] = Query(
        default=None,
        description="Filter by alert severity"
    ),
    status_filter: Optional[AlertStatus] = Query(
        default=None,
        alias="status",
        description="Filter by alert status"
    ),
    animal_id: Optional[str] = Query(
        default=None,
        description="Filter by animal ID"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Max alerts to return (1-200)"
    ),
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Retrieve alerts based on filters.

    Preventive alerts are synchronized automatically
    before retrieving the alert list.
    """

    ensure_alert_indexes()

    # -------------------------------------------------
    # Phase 6.5 automatic preventive synchronization
    # -------------------------------------------------

    _sync_preventive_alerts(current_user)

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    query = {}

    if user_role == "farmer":
        query["owner_id"] = user_id

    if severity:
        query["severity"] = severity

    if status_filter:
        query["status"] = status_filter

    if animal_id:

        if not ObjectId.is_valid(animal_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid animal ID format."
            )

        query["animal_id"] = animal_id

    alerts_cursor = (
        db.alerts
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )

    return [
        serialize_alert(item)
        for item in alerts_cursor
    ]


@router.get(
    "/active",
    response_model=list[AlertResponse]
)
def get_active_alerts(
    severity: Optional[AlertSeverity] = Query(
        default=None,
        description="Filter by alert severity"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Max alerts to return (1-200)"
    ),
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Retrieve only active alerts.

    Preventive alerts are synchronized automatically.
    """

    ensure_alert_indexes()

    _sync_preventive_alerts(current_user)

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    query = {
        "status": "active"
    }

    if user_role == "farmer":
        query["owner_id"] = user_id

    if severity:
        query["severity"] = severity

    alerts_cursor = (
        db.alerts
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )

    return [
        serialize_alert(item)
        for item in alerts_cursor
    ]


@router.get(
    "/animal/{animal_id}",
    response_model=list[AlertResponse]
)
def get_animal_alerts(
    animal_id: str,
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Retrieve all alerts for a specific animal.
    """

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID format."
        )

    animal = db.animals.find_one({
        "_id": ObjectId(animal_id)
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    if (
        user_role == "farmer"
        and animal.get("owner_id") != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    # Synchronize preventive alerts before returning
    # the animal alert history.
    _sync_preventive_alerts(current_user)

    alerts_cursor = (
        db.alerts
        .find({
            "animal_id": animal_id
        })
        .sort("created_at", -1)
    )

    return [
        serialize_alert(item)
        for item in alerts_cursor
    ]


@router.get(
    "/{alert_id}",
    response_model=AlertResponse
)
def get_alert(
    alert_id: str,
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Retrieve details of a single alert by ID.
    """

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format."
        )

    alert = db.alerts.find_one({
        "_id": ObjectId(alert_id)
    })

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found."
        )

    if (
        user_role == "farmer"
        and alert.get("owner_id") != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied."
        )

    return serialize_alert(alert)


@router.put(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse
)
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Acknowledge an active alert.
    """

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format."
        )

    alert = db.alerts.find_one({
        "_id": ObjectId(alert_id)
    })

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found."
        )

    if (
        user_role == "farmer"
        and alert.get("owner_id") != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied."
        )

    now = datetime.now(timezone.utc)

    db.alerts.update_one(
        {
            "_id": ObjectId(alert_id)
        },
        {
            "$set": {
                "status": "acknowledged",
                "acknowledged_at": now,
                "acknowledged_by": user_id
            }
        }
    )

    updated_alert = db.alerts.find_one({
        "_id": ObjectId(alert_id)
    })

    await manager.broadcast({
        "type": "alert_updated",
        "data": {
            "alert_id": alert_id,
            "status": "acknowledged"
        }
    })

    return serialize_alert(updated_alert)


@router.put(
    "/{alert_id}/resolve",
    response_model=AlertResponse
)
async def resolve_alert(
    alert_id: str,
    current_user: dict = Depends(
        require_any_authenticated_user
    )
):
    """
    Resolve an alert.

    Resolved alerts remain stored for history,
    analytics and audit purposes.
    """

    db = get_database()

    user_id = current_user["sub"]
    user_role = current_user.get("role")

    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format."
        )

    alert = db.alerts.find_one({
        "_id": ObjectId(alert_id)
    })

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found."
        )

    if (
        user_role == "farmer"
        and alert.get("owner_id") != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied."
        )

    now = datetime.now(timezone.utc)

    db.alerts.update_one(
        {
            "_id": ObjectId(alert_id)
        },
        {
            "$set": {
                "status": "resolved",
                "resolved_at": now,
                "resolved_by": user_id
            }
        }
    )

    updated_alert = db.alerts.find_one({
        "_id": ObjectId(alert_id)
    })

    await manager.broadcast({
        "type": "alert_updated",
        "data": {
            "alert_id": alert_id,
            "status": "resolved"
        }
    })

    return serialize_alert(updated_alert)
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_database
from app.permissions import require_farmer
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse
)


router = APIRouter(
    prefix="/devices",
    tags=["Device Management"]
)


def device_to_response(device):
    return DeviceResponse(
        id=str(device["_id"]),
        device_id=device["device_id"],
        device_name=device["device_name"],
        device_type=device["device_type"],
        animal_id=device["animal_id"],
        farm_id=device["farm_id"],
        owner_id=device["owner_id"],
        battery_level=device["battery_level"],
        firmware_version=device.get("firmware_version"),
        sensor_types=device.get("sensor_types", []),
        status=device.get("status", "offline"),
        last_seen_at=(
            device["last_seen_at"].isoformat()
            if device.get("last_seen_at")
            else None
        ),
        created_at=device["created_at"].isoformat(),
        updated_at=device["updated_at"].isoformat()
    )


def verify_animal_owner(
    db,
    animal_id: str,
    user_id: str
):
    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    animal = db.animals.find_one({
        "_id": ObjectId(animal_id),
        "owner_id": user_id
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    return animal


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED
)
def register_device(
    device: DeviceCreate,
    current_user: dict = Depends(require_farmer)
):
    """
    Register a monitoring device and assign it to an animal.
    """

    db = get_database()
    user_id = current_user["sub"]

    # Verify that the animal belongs to the farmer.
    animal = verify_animal_owner(
        db,
        device.animal_id,
        user_id
    )

    # Prevent duplicate device IDs for this farmer.
    existing_device = db.devices.find_one({
        "device_id": device.device_id.strip(),
        "owner_id": user_id
    })

    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A device with this ID already exists."
        )

    now = datetime.now(timezone.utc)

    new_device = {
        "device_id": device.device_id.strip(),
        "device_name": device.device_name.strip(),
        "device_type": device.device_type,
        "animal_id": device.animal_id,
        "farm_id": animal["farm_id"],
        "owner_id": user_id,
        "battery_level": device.battery_level,
        "firmware_version": device.firmware_version,
        "sensor_types": device.sensor_types,
        "status": "offline",
        "last_seen_at": None,
        "created_at": now,
        "updated_at": now
    }

    result = db.devices.insert_one(new_device)

    return device_to_response(
        db.devices.find_one({
            "_id": result.inserted_id
        })
    )


@router.get(
    "",
    response_model=list[DeviceResponse]
)
def get_devices(
    current_user: dict = Depends(require_farmer)
):
    """
    Get all devices belonging to the current farmer.
    """

    db = get_database()
    user_id = current_user["sub"]

    devices = db.devices.find({
        "owner_id": user_id
    }).sort(
        "created_at",
        -1
    )

    return [
        device_to_response(device)
        for device in devices
    ]


@router.get(
    "/{device_id}",
    response_model=DeviceResponse
)
def get_device(
    device_id: str,
    current_user: dict = Depends(require_farmer)
):
    """
    Get one device by its MongoDB ID.
    """

    db = get_database()
    user_id = current_user["sub"]

    if not ObjectId.is_valid(device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID."
        )

    device = db.devices.find_one({
        "_id": ObjectId(device_id),
        "owner_id": user_id
    })

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    return device_to_response(device)


@router.put(
    "/{device_id}",
    response_model=DeviceResponse
)
def update_device(
    device_id: str,
    device: DeviceUpdate,
    current_user: dict = Depends(require_farmer)
):
    """
    Update device information.
    """

    db = get_database()
    user_id = current_user["sub"]

    if not ObjectId.is_valid(device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID."
        )

    existing_device = db.devices.find_one({
        "_id": ObjectId(device_id),
        "owner_id": user_id
    })

    if not existing_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    update_data = device.model_dump(
        exclude_unset=True
    )

    # If the animal is changed, verify ownership.
    if "animal_id" in update_data:
        animal = verify_animal_owner(
            db,
            update_data["animal_id"],
            user_id
        )

        update_data["farm_id"] = animal["farm_id"]

    if "device_name" in update_data:
        update_data["device_name"] = (
            update_data["device_name"].strip()
        )

    update_data["updated_at"] = datetime.now(
        timezone.utc
    )

    db.devices.update_one(
        {
            "_id": ObjectId(device_id),
            "owner_id": user_id
        },
        {
            "$set": update_data
        }
    )

    updated_device = db.devices.find_one({
        "_id": ObjectId(device_id)
    })

    return device_to_response(updated_device)


@router.delete(
    "/{device_id}"
)
def delete_device(
    device_id: str,
    current_user: dict = Depends(require_farmer)
):
    """
    Delete a monitoring device.
    """

    db = get_database()
    user_id = current_user["sub"]

    if not ObjectId.is_valid(device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID."
        )

    result = db.devices.delete_one({
        "_id": ObjectId(device_id),
        "owner_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    return {
        "message": "Device deleted successfully.",
        "device_id": device_id
    }
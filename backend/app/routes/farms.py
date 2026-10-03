from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.permissions import require_farmer
from app.database import get_database
from app.schemas.farm import (
    FarmCreate,
    FarmUpdate,
    FarmResponse
)
from app.security import decode_access_token


router = APIRouter(
    prefix="/farms",
    tags=["Farm Management"]
)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Extract and validate the JWT token.
    """

    token = credentials.credentials

    payload = decode_access_token(token)

    return payload


def _serialize_farm(farm: dict) -> FarmResponse:
    created = farm.get("created_at")
    updated = farm.get("updated_at")
    return FarmResponse(
        id=str(farm["_id"]),
        owner_id=str(farm["owner_id"]),
        name=farm["name"],
        location=farm["location"],
        livestock_type=farm["livestock_type"],
        total_animals=farm.get("total_animals", 0),
        description=farm.get("description"),
        latitude=farm.get("latitude"),
        longitude=farm.get("longitude"),
        location_accuracy=farm.get("location_accuracy"),
        district=farm.get("district"),
        state=farm.get("state"),
        pincode=farm.get("pincode"),
        created_at=created.isoformat() if hasattr(created, "isoformat") else str(created),
        updated_at=updated.isoformat() if hasattr(updated, "isoformat") else str(updated)
    )


@router.post(
    "",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED
)
def create_farm(
    farm: FarmCreate,
    current_user: dict = Depends(require_farmer)
):
    """
    Create a new farm for the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    now = datetime.now(timezone.utc)

    new_farm = {
        "owner_id": user_id,
        "name": farm.name.strip(),
        "location": farm.location.strip(),
        "livestock_type": farm.livestock_type.strip(),
        "total_animals": farm.total_animals,
        "description": (
            farm.description.strip()
            if farm.description
            else None
        ),
        "latitude": farm.latitude,
        "longitude": farm.longitude,
        "location_accuracy": farm.location_accuracy,
        "district": farm.district.strip() if farm.district else None,
        "state": farm.state.strip() if farm.state else None,
        "pincode": farm.pincode.strip() if farm.pincode else None,
        "created_at": now,
        "updated_at": now
    }

    result = db.farms.insert_one(new_farm)
    new_farm["_id"] = result.inserted_id

    return _serialize_farm(new_farm)


@router.get(
    "",
    response_model=list[FarmResponse]
)
def get_my_farms(
    current_user: dict = Depends(require_farmer)
):
    """
    Get all farms belonging to the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    farms = db.farms.find({
        "owner_id": user_id
    }).sort("created_at", -1)

    return [_serialize_farm(f) for f in farms]


@router.get(
    "/{farm_id}",
    response_model=FarmResponse
)
def get_farm(
    farm_id: str,
    current_user: dict = Depends(require_farmer)
):
    """
    Get a specific farm belonging to the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    if not ObjectId.is_valid(farm_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid farm ID."
        )

    farm = db.farms.find_one({
        "_id": ObjectId(farm_id),
        "owner_id": user_id
    })

    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )

    return _serialize_farm(farm)


@router.put(
    "/{farm_id}",
    response_model=FarmResponse
)
def update_farm(
    farm_id: str,
    farm: FarmUpdate,
    current_user: dict = Depends(require_farmer)
):
    """
    Update a farm belonging to the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    if not ObjectId.is_valid(farm_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid farm ID."
        )

    existing_farm = db.farms.find_one({
        "_id": ObjectId(farm_id),
        "owner_id": user_id
    })

    if not existing_farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )

    update_data = farm.model_dump(
        exclude_unset=True
    )

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    if "location" in update_data and update_data["location"]:
        update_data["location"] = update_data["location"].strip()

    if "livestock_type" in update_data and update_data["livestock_type"]:
        update_data["livestock_type"] = (
            update_data["livestock_type"].strip()
        )

    if "description" in update_data and update_data["description"]:
        update_data["description"] = (
            update_data["description"].strip()
        )

    if "district" in update_data and update_data["district"]:
        update_data["district"] = update_data["district"].strip()

    if "state" in update_data and update_data["state"]:
        update_data["state"] = update_data["state"].strip()

    if "pincode" in update_data and update_data["pincode"]:
        update_data["pincode"] = update_data["pincode"].strip()

    update_data["updated_at"] = datetime.now(timezone.utc)

    db.farms.update_one(
        {
            "_id": ObjectId(farm_id),
            "owner_id": user_id
        },
        {
            "$set": update_data
        }
    )

    updated_farm = db.farms.find_one({
        "_id": ObjectId(farm_id),
        "owner_id": user_id
    })

    return _serialize_farm(updated_farm)


@router.delete(
    "/{farm_id}"
)
def delete_farm(
    farm_id: str,
    current_user: dict = Depends(require_farmer)
):
    """
    Delete a farm belonging to the authenticated farmer.
    """

    db = get_database()

    user_id = current_user["sub"]

    if not ObjectId.is_valid(farm_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid farm ID."
        )

    result = db.farms.delete_one({
        "_id": ObjectId(farm_id),
        "owner_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )

    return {
        "message": "Farm deleted successfully.",
        "farm_id": farm_id
    }
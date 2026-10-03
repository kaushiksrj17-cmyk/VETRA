from datetime import datetime, timezone

from fastapi.responses import Response

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.permissions import require_farmer

from app.database import get_database
from app.schemas.animal import (
    AnimalCreate,
    AnimalUpdate,
    AnimalResponse
)
from app.security import decode_access_token
from app.utils.qr_generator import generate_animal_qr


router = APIRouter(
    prefix="/farms/{farm_id}/animals",
    tags=["Animal Management"]
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


def verify_farm_owner(
    db,
    farm_id: str,
    user_id: str
):
    """
    Verify that the farm exists and belongs to
    the authenticated user.
    """

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
            detail="Farm not found or access denied."
        )

    return farm


def animal_to_response(animal):
    """
    Convert a MongoDB animal document into AnimalResponse.
    """

    return AnimalResponse(
        id=str(animal["_id"]),
        farm_id=animal["farm_id"],
        owner_id=animal["owner_id"],
        tag_id=animal["tag_id"],
        name=animal.get("name"),
        species=animal["species"],
        breed=animal["breed"],
        gender=animal["gender"],
        date_of_birth=animal["date_of_birth"].isoformat(),
        weight_kg=animal["weight_kg"],
        health_status=animal["health_status"],
        notes=animal.get("notes"),
        created_at=animal["created_at"].isoformat(),
        updated_at=animal["updated_at"].isoformat()
    )


@router.post(
    "",
    response_model=AnimalResponse,
    status_code=status.HTTP_201_CREATED
)
def create_animal(
    farm_id: str,
    animal: AnimalCreate,
   current_user: dict = Depends(require_farmer)
):
    """
    Register a new animal under a farm.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    # Prevent duplicate tag IDs within the same farm.
    existing_animal = db.animals.find_one({
        "farm_id": farm_id,
        "tag_id": animal.tag_id.strip()
    })

    if existing_animal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An animal with this tag ID already exists in this farm."
        )

    now = datetime.now(timezone.utc)

    new_animal = {
        "farm_id": farm_id,
        "owner_id": user_id,

        "tag_id": animal.tag_id.strip(),

        "name": animal.name.strip()
        if animal.name
        else None,

        "species": animal.species.strip(),
        "breed": animal.breed.strip(),
        "gender": animal.gender,

        "date_of_birth": datetime.combine(
            animal.date_of_birth,
            datetime.min.time()
        ),

        "weight_kg": animal.weight_kg,

        "health_status": animal.health_status,

        "notes": animal.notes.strip()
        if animal.notes
        else None,

        "created_at": now,
        "updated_at": now
    }

    result = db.animals.insert_one(new_animal)

    # Increase farm animal count.
    db.farms.update_one(
        {
            "_id": ObjectId(farm_id),
            "owner_id": user_id
        },
        {
            "$inc": {
                "total_animals": 1
            },
            "$set": {
                "updated_at": now
            }
        }
    )

    created_animal = db.animals.find_one({
        "_id": result.inserted_id
    })

    return animal_to_response(created_animal)


@router.get(
    "",
    response_model=list[AnimalResponse]
)
def get_farm_animals(
    farm_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all animals belonging to a farm.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    animals = db.animals.find({
        "farm_id": farm_id,
        "owner_id": user_id
    }).sort("created_at", -1)

    return [
        animal_to_response(animal)
        for animal in animals
    ]


@router.get(
    "/{animal_id}",
    response_model=AnimalResponse
)
def get_animal(
    farm_id: str,
    animal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get one animal's complete profile.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    animal = db.animals.find_one({
        "_id": ObjectId(animal_id),
        "farm_id": farm_id,
        "owner_id": user_id
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    return animal_to_response(animal)


@router.put(
    "/{animal_id}",
    response_model=AnimalResponse
)
def update_animal(
    farm_id: str,
    animal_id: str,
    animal: AnimalUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an animal profile.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    existing_animal = db.animals.find_one({
        "_id": ObjectId(animal_id),
        "farm_id": farm_id,
        "owner_id": user_id
    })

    if not existing_animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    update_data = animal.model_dump(
        exclude_unset=True
    )

    if "tag_id" in update_data:

        new_tag = update_data["tag_id"].strip()

        duplicate = db.animals.find_one({
            "_id": {
                "$ne": ObjectId(animal_id)
            },
            "farm_id": farm_id,
            "tag_id": new_tag
        })

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another animal already uses this tag ID."
            )

        update_data["tag_id"] = new_tag

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    if "species" in update_data and update_data["species"]:
        update_data["species"] = update_data["species"].strip()

    if "breed" in update_data and update_data["breed"]:
        update_data["breed"] = update_data["breed"].strip()

    if "notes" in update_data and update_data["notes"]:
        update_data["notes"] = update_data["notes"].strip()

    if "date_of_birth" in update_data:
        update_data["date_of_birth"] = datetime.combine(
            update_data["date_of_birth"],
            datetime.min.time()
        )

    update_data["updated_at"] = datetime.now(timezone.utc)

    db.animals.update_one(
        {
            "_id": ObjectId(animal_id),
            "farm_id": farm_id,
            "owner_id": user_id
        },
        {
            "$set": update_data
        }
    )

    updated_animal = db.animals.find_one({
        "_id": ObjectId(animal_id)
    })

    return animal_to_response(updated_animal)


@router.delete(
    "/{animal_id}"
)
def delete_animal(
    farm_id: str,
    animal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an animal from a farm.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    result = db.animals.delete_one({
        "_id": ObjectId(animal_id),
        "farm_id": farm_id,
        "owner_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    now = datetime.now(timezone.utc)

    # Keep the farm's animal count synchronized.
    db.farms.update_one(
        {
            "_id": ObjectId(farm_id),
            "owner_id": user_id,
            "total_animals": {
                "$gt": 0
            }
        },
        {
            "$inc": {
                "total_animals": -1
            },
            "$set": {
                "updated_at": now
            }
        }
    )

    return {
        "message": "Animal deleted successfully.",
        "animal_id": animal_id
    }


@router.get(
    "/{animal_id}/qr",
    response_class=Response
)
def get_animal_qr(
    farm_id: str,
    animal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and return the QR code for an animal.
    """

    db = get_database()

    user_id = current_user["sub"]

    verify_farm_owner(
        db,
        farm_id,
        user_id
    )

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID."
        )

    animal = db.animals.find_one({
        "_id": ObjectId(animal_id),
        "farm_id": farm_id,
        "owner_id": user_id
    })

    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    qr_image = generate_animal_qr(
        animal_id=str(animal["_id"]),
        farm_id=animal["farm_id"],
        tag_id=animal["tag_id"]
    )

    return Response(
        content=qr_image,
        media_type="image/png"
    )


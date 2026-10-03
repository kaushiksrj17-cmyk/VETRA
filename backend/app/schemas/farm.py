from typing import Optional

from pydantic import BaseModel, Field


class FarmCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=200)
    livestock_type: str = Field(..., min_length=2, max_length=100)
    total_animals: int = Field(default=0, ge=0)
    description: Optional[str] = Field(
        default=None,
        max_length=500
    )
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    location_accuracy: Optional[float] = Field(default=None, ge=0.0)
    district: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    pincode: Optional[str] = Field(default=None, max_length=20)


class FarmUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    location: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200
    )

    livestock_type: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    total_animals: Optional[int] = Field(
        default=None,
        ge=0
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500
    )

    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    location_accuracy: Optional[float] = Field(default=None, ge=0.0)
    district: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    pincode: Optional[str] = Field(default=None, max_length=20)


class FarmResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    location: str
    livestock_type: str
    total_animals: int
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    created_at: str
    updated_at: str
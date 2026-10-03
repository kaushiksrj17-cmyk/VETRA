from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


AnimalGender = Literal["male", "female"]

AnimalHealthStatus = Literal[
    "healthy",
    "monitoring",
    "at_risk",
    "critical"
]


class AnimalCreate(BaseModel):
    tag_id: str = Field(..., min_length=2, max_length=50)

    name: Optional[str] = Field(
        default=None,
        max_length=100
    )

    species: str = Field(
        ...,
        min_length=2,
        max_length=50
    )

    breed: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    gender: AnimalGender

    date_of_birth: date

    weight_kg: float = Field(
        ...,
        gt=0,
        le=2000
    )

    health_status: AnimalHealthStatus = "healthy"

    notes: Optional[str] = Field(
        default=None,
        max_length=500
    )


class AnimalUpdate(BaseModel):
    tag_id: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50
    )

    name: Optional[str] = Field(
        default=None,
        max_length=100
    )

    species: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50
    )

    breed: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    gender: Optional[AnimalGender] = None

    date_of_birth: Optional[date] = None

    weight_kg: Optional[float] = Field(
        default=None,
        gt=0,
        le=2000
    )

    health_status: Optional[AnimalHealthStatus] = None

    notes: Optional[str] = Field(
        default=None,
        max_length=500
    )


class AnimalResponse(BaseModel):
    id: str
    farm_id: str
    owner_id: str

    tag_id: str
    name: Optional[str] = None

    species: str
    breed: str
    gender: AnimalGender
    date_of_birth: str

    weight_kg: float

    health_status: AnimalHealthStatus

    notes: Optional[str] = None

    created_at: str
    updated_at: str
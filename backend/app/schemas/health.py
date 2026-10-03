from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ReadingSource = Literal[
    "simulator",
    "esp32",
    "manual"
]


class HealthReadingCreate(BaseModel):
    animal_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    temperature_c: float = Field(
        ...,
        ge=30.0,
        le=50.0
    )

    heart_rate_bpm: float = Field(
        ...,
        ge=20.0,
        le=200.0
    )

    activity_level: float = Field(
        ...,
        ge=0.0,
        le=100.0
    )

    rumination_level: float = Field(
        ...,
        ge=0.0,
        le=100.0
    )

    respiratory_rate: float = Field(
        ...,
        ge=1.0,
        le=100.0
    )

    source: ReadingSource = "simulator"

    recorded_at: Optional[datetime] = None


class HealthReadingResponse(BaseModel):
    id: str
    animal_id: str
    device_id: str
    temperature_c: float
    heart_rate_bpm: float
    activity_level: float
    rumination_level: float
    respiratory_rate: float
    source: ReadingSource
    recorded_at: str
    created_at: str
    animal_name: Optional[str] = None
    tag_id: Optional[str] = None
    species: Optional[str] = None
    risk_status: Optional[str] = None
    farm_id: Optional[str] = None
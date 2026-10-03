from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


DeviceType = Literal[
    "wearable",
    "collar",
    "ear_tag",
    "sensor_node",
    "gateway"
]

DeviceStatus = Literal[
    "online",
    "offline",
    "maintenance",
    "inactive"
]


class DeviceCreate(BaseModel):
    device_id: str = Field(
        ...,
        min_length=3,
        max_length=100
    )

    device_name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    device_type: DeviceType = "wearable"

    animal_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    battery_level: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0
    )

    firmware_version: Optional[str] = Field(
        default=None,
        max_length=50
    )

    sensor_types: list[str] = Field(
        default_factory=lambda: [
            "temperature",
            "heart_rate",
            "activity",
            "rumination",
            "respiratory_rate"
        ]
    )


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    device_type: Optional[DeviceType] = None

    animal_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    battery_level: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0
    )

    firmware_version: Optional[str] = Field(
        default=None,
        max_length=50
    )

    sensor_types: Optional[list[str]] = None

    status: Optional[DeviceStatus] = None


class DeviceResponse(BaseModel):
    id: str
    device_id: str
    device_name: str
    device_type: DeviceType
    animal_id: str
    farm_id: str
    owner_id: str

    battery_level: float
    firmware_version: Optional[str] = None

    sensor_types: list[str]

    status: DeviceStatus

    last_seen_at: Optional[str] = None

    created_at: str
    updated_at: str
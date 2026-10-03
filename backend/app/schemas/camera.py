import re
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


CameraType = Literal[
    "stationary_pen",
    "cattle_shed",
    "feeding_area",
    "milking_area",
    "quarantine_area",
    "mobile",
    "other"
]

ConnectionType = Literal[
    "rtsp",
    "http",
    "webhook",
    "mock"
]

CameraStatus = Literal[
    "online",
    "offline",
    "degraded",
    "unknown",
    "disabled"
]


def redact_stream_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitize and redact credentials (username:password) from RTSP/HTTP URLs.
    Example: rtsp://admin:secret123@192.168.1.10:554/live -> rtsp://admin:***@192.168.1.10:554/live
    """
    if not url:
        return url
    # Regex replacing user:pass with user:***
    return re.sub(r"://([^:@\s]+):([^@\s]+)@", r"://\1:***@", url)


# ============================================================
# CAMERA REGISTRY SCHEMAS
# ============================================================

class CameraCreate(BaseModel):
    camera_name: str = Field(..., min_length=2, max_length=100, description="Human-readable camera designation")
    farm_id: str = Field(..., description="ID of holding/farm where camera is deployed")
    animal_id: Optional[str] = Field(None, description="Optional single animal continuously monitored")
    pen_id: Optional[str] = Field(None, description="Stationary enclosure/pen designation")
    camera_type: CameraType = Field(default="stationary_pen")
    connection_type: ConnectionType = Field(default="mock")
    stream_url_reference: str = Field(..., description="RTSP URL, stream URI, or mock reference")
    edge_device_id: Optional[str] = Field(None, description="Linked edge processor ID")
    enabled: bool = Field(default=True)
    fps_target: float = Field(default=25.0, ge=1.0, le=120.0)
    sampling_interval_seconds: float = Field(default=5.0, ge=1.0, le=3600.0)
    resolution: Optional[str] = Field(default="1920x1080")
    location_label: Optional[str] = Field(default="Barn Enclosure A")


class CameraUpdate(BaseModel):
    camera_name: Optional[str] = None
    animal_id: Optional[str] = None
    pen_id: Optional[str] = None
    camera_type: Optional[CameraType] = None
    connection_type: Optional[ConnectionType] = None
    stream_url_reference: Optional[str] = None
    edge_device_id: Optional[str] = None
    enabled: Optional[bool] = None
    status: Optional[CameraStatus] = None
    fps_target: Optional[float] = None
    sampling_interval_seconds: Optional[float] = None
    resolution: Optional[str] = None
    location_label: Optional[str] = None


class CameraResponse(BaseModel):
    id: str
    camera_id: str
    camera_name: str
    farm_id: str
    farm_name: Optional[str] = None
    animal_id: Optional[str] = None
    animal_tag: Optional[str] = None
    pen_id: Optional[str] = None
    camera_type: CameraType
    connection_type: ConnectionType
    stream_url_reference: str = Field(..., description="Redacted connection reference (credentials stripped)")
    edge_device_id: Optional[str] = None
    status: CameraStatus
    enabled: bool
    last_seen: Optional[str] = None
    last_frame_at: Optional[str] = None
    last_inference_at: Optional[str] = None
    fps_target: float
    sampling_interval_seconds: float
    resolution: Optional[str] = None
    location_label: Optional[str] = None
    created_at: str
    updated_at: str


class CameraTestConnectionResponse(BaseModel):
    camera_id: str
    connected: bool
    status: str
    latency_ms: float
    message: str
    frame_captured: bool
    resolution: Optional[str] = None


class CameraHealthResponse(BaseModel):
    camera_id: str
    camera_name: str
    status: CameraStatus
    health_tier: Literal["HEALTHY", "DEGRADED", "OFFLINE", "DISABLED"]
    last_seen: Optional[str] = None
    last_frame_at: Optional[str] = None
    last_inference_at: Optional[str] = None
    consecutive_failures: int
    frames_received: int
    frames_dropped: int
    inference_count: int
    average_inference_latency_ms: float
    uptime_estimate_pct: float
    connection_message: str


class CameraSummaryResponse(BaseModel):
    total_cameras: int
    online_cameras: int
    degraded_cameras: int
    offline_cameras: int
    disabled_cameras: int
    by_type: dict[str, int] = Field(default_factory=dict)
    by_connection: dict[str, int] = Field(default_factory=dict)

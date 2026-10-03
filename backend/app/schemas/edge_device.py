from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


EdgeDeviceType = Literal[
    "raspberry_pi",
    "jetson",
    "mini_pc",
    "server",
    "simulator"
]

EdgeDeviceStatus = Literal[
    "online",
    "offline",
    "degraded",
    "disabled"
]


# ============================================================
# EDGE DEVICE SCHEMAS
# ============================================================

class EdgeDeviceCreate(BaseModel):
    device_name: str = Field(..., min_length=2, max_length=100, description="Device hostname/name")
    device_type: EdgeDeviceType = Field(default="mini_pc")
    farm_id: str = Field(..., description="ID of holding/farm where device operates")
    ip_address: Optional[str] = Field(None, description="Local or tunnel IP address")
    software_version: str = Field(default="1.0.0")
    model_version: str = Field(default="Phase9-DeterministicVisual-v1.0")
    camera_ids: list[str] = Field(default_factory=list, description="IDs of cameras processed by this edge device")
    capabilities: list[str] = Field(
        default_factory=lambda: ["opencv_stream", "frame_sampler", "deterministic_analyzer", "offline_buffer"],
        description="Supported edge runtime capabilities"
    )
    status: EdgeDeviceStatus = Field(default="online")


class EdgeDeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[EdgeDeviceType] = None
    farm_id: Optional[str] = None
    ip_address: Optional[str] = None
    software_version: Optional[str] = None
    model_version: Optional[str] = None
    camera_ids: Optional[list[str]] = None
    capabilities: Optional[list[str]] = None
    status: Optional[EdgeDeviceStatus] = None


class EdgeDeviceHeartbeat(BaseModel):
    software_version: Optional[str] = None
    model_version: Optional[str] = None
    cpu_usage_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    memory_usage_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    temperature_celsius: Optional[float] = Field(None, ge=-20.0, le=120.0)
    buffered_events_count: Optional[int] = Field(default=0, ge=0)
    active_cameras: Optional[list[str]] = Field(default_factory=list)


class EdgeDeviceResponse(BaseModel):
    id: str
    edge_device_id: str
    device_name: str
    device_type: EdgeDeviceType
    farm_id: str
    farm_name: Optional[str] = None
    status: EdgeDeviceStatus
    ip_address: Optional[str] = None
    software_version: str
    model_version: str
    last_heartbeat: Optional[str] = None
    last_inference_at: Optional[str] = None
    cpu_usage_pct: Optional[float] = None
    memory_usage_pct: Optional[float] = None
    temperature_celsius: Optional[float] = None
    camera_ids: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class EdgeDeviceHealthResponse(BaseModel):
    edge_device_id: str
    device_name: str
    status: EdgeDeviceStatus
    health_tier: Literal["HEALTHY", "DEGRADED", "OFFLINE", "DISABLED"]
    last_heartbeat: Optional[str] = None
    heartbeat_age_seconds: Optional[float] = None
    cpu_usage_pct: Optional[float] = None
    memory_usage_pct: Optional[float] = None
    temperature_celsius: Optional[float] = None
    active_camera_count: int = 0
    inference_count: int = 0
    health_summary: str


class EdgeDeviceSummaryResponse(BaseModel):
    total_devices: int
    online_devices: int
    degraded_devices: int
    offline_devices: int
    disabled_devices: int
    by_type: dict[str, int] = Field(default_factory=dict)


# ============================================================
# EDGE INFERENCE EVENT SCHEMAS (WEBHOOK / ASYNC INGESTION)
# ============================================================

class EdgeInferenceEventCreate(BaseModel):
    edge_device_id: str = Field(..., description="ID of source edge device")
    camera_id: str = Field(..., description="ID of camera capturing the frame")
    animal_id: Optional[str] = Field(None, description="Optional target animal")
    captured_at: str = Field(..., description="ISO timestamp when frame was sampled")
    frame_id: str = Field(..., description="Unique frame sequence identifier")
    frame_hash: str = Field(..., min_length=16, description="SHA-256 hash of frame for deduplication & audit")
    model_name: str = Field(default="VETRA-EdgeVision")
    model_version: str = Field(default="1.0.0")
    observations: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured visual findings (posture, mobility, coat, lesions, etc.)"
    )
    visual_risk_score: float = Field(..., ge=0.0, le=1.0, description="Normalized visual risk score [0..1]")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    processing_latency_ms: float = Field(default=45.0, ge=0.0)


class EdgeInferenceEventResponse(BaseModel):
    accepted: bool
    event_id: str
    deduplicated: bool = False
    reason: Optional[str] = None
    visual_risk_score: Optional[float] = None
    alert_triggered: bool = False
    alert_id: Optional[str] = None
    surveillance_signal: bool = False

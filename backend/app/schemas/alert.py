from typing import Literal, Optional

from pydantic import BaseModel, Field


AlertSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical"
]

AlertStatus = Literal[
    "active",
    "acknowledged",
    "resolved"
]

# Physiological Telemetry Alert Types
PhysiologicalAlertType = Literal[
    "high_temperature",
    "low_temperature",
    "high_heart_rate",
    "low_heart_rate",
    "high_respiratory_rate",
    "low_respiratory_rate",
    "low_activity",
    "low_rumination",
    "multiple_abnormal_signs",
]

# Preventive Healthcare Alert Types
PreventiveAlertType = Literal[
    "preventive_vaccination",
    "preventive_deworming",
    "preventive_veterinary_follow_up",
    "preventive_care",
]

# Disease Surveillance Alert Types
SurveillanceAlertType = Literal[
    "disease_suspected",
    "disease_cluster",
    "surveillance_high_risk",
    "geospatial_cluster",
]

# Phase 9: Computer Vision & Multimodal Alert Types
VisualAlertType = Literal[
    "visual_health_signal",
    "multimodal_health_signal",
    "persistent_visual_abnormality",
    "visual_surveillance_signal",
]

# Phase 10: Edge Computer Vision & Camera Monitoring Alert Types
CameraAlertType = Literal[
    "camera_offline",
    "camera_degraded",
    "edge_device_offline",
    "persistent_visual_concern",
    "visual_health_risk",
    "multimodal_health_risk",
    "repeated_abnormal_posture",
    "feeding_inactivity",
    "visual_telemetry_mismatch",
]

# Phase 11: Predictive Health Intelligence Alert Types
PredictiveAlertType = Literal[
    "predictive_health_risk",
    "predictive_deterioration",
    "rapid_health_decline",
    "persistent_multimodal_concern",
]

# Complete Unified AlertType Supporting Physiological, Preventive, Surveillance, Visual, Edge & Predictive Systems
AlertType = Literal[
    "high_temperature",
    "low_temperature",
    "high_heart_rate",
    "low_heart_rate",
    "high_respiratory_rate",
    "low_respiratory_rate",
    "low_activity",
    "low_rumination",
    "multiple_abnormal_signs",
    "preventive_vaccination",
    "preventive_deworming",
    "preventive_veterinary_follow_up",
    "preventive_care",
    "disease_suspected",
    "disease_cluster",
    "surveillance_high_risk",
    "geospatial_cluster",
    "visual_health_signal",
    "multimodal_health_signal",
    "persistent_visual_abnormality",
    "visual_surveillance_signal",
    "camera_offline",
    "camera_degraded",
    "edge_device_offline",
    "persistent_visual_concern",
    "visual_health_risk",
    "multimodal_health_risk",
    "repeated_abnormal_posture",
    "feeding_inactivity",
    "visual_telemetry_mismatch",
    "predictive_health_risk",
    "predictive_deterioration",
    "rapid_health_decline",
    "persistent_multimodal_concern",
]



class AlertResponse(BaseModel):

    id: str

    animal_id: str

    farm_id: str

    owner_id: str

    device_id: Optional[str] = "SYSTEM"

    alert_type: AlertType

    severity: AlertSeverity

    title: str

    message: str

    triggered_by: list[str] = Field(
        default_factory=list
    )

    status: AlertStatus

    health_reading_id: Optional[str] = None

    # Preventive healthcare metadata
    preventive_record_id: Optional[str] = None

    preventive_category: Optional[str] = None

    preventive_due_date: Optional[str] = None

    # Visual health & multimodal metadata
    visual_analysis_id: Optional[str] = None

    multimodal_assessment_id: Optional[str] = None

    # Phase 10: Camera & Edge metadata
    camera_id: Optional[str] = None

    edge_device_id: Optional[str] = None

    edge_event_id: Optional[str] = None

    # Phase 11: Predictive health metadata
    predictive_assessment_id: Optional[str] = None

    forecast_window_hours: Optional[int] = None

    created_at: str

    acknowledged_at: Optional[str] = None

    acknowledged_by: Optional[str] = None

    resolved_at: Optional[str] = None

    resolved_by: Optional[str] = None
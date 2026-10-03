from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


VisualSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical"
]

VisualRiskCategory = Literal[
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL"
]

ConfidenceLevel = Literal[
    "Low",
    "Moderate",
    "High"
]

ReviewStatus = Literal[
    "pending",
    "reviewed",
    "escalated_to_case",
    "ruled_out"
]

CLINICAL_SAFETY_DISCLAIMER = (
    "Decision Support Only: Visual observations are AI-assisted indicators and are not a confirmed "
    "veterinary diagnosis. Veterinary examination is required for clinical confirmation."
)


# ============================================================
# VISUAL OBSERVATION SCHEMA
# ============================================================

class VisualObservation(BaseModel):
    observation_id: str = Field(..., description="Unique ID for this visual indicator observation")
    analysis_id: str = Field(..., description="Parent analysis ID")
    animal_id: str = Field(..., description="Target animal ID")
    indicator: str = Field(..., description="Standard visual indicator key e.g. abnormal_posture")
    description: str = Field(..., description="Human-readable clinical sign description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    confidence_level: ConfidenceLevel = Field(..., description="Qualitative confidence rating")
    severity: VisualSeverity = Field(default="medium", description="Visual indicator severity")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    source: str = Field(default="computer_vision_engine", description="Source subsystem")


# ============================================================
# VISUAL ANALYSIS SCHEMAS
# ============================================================

class VisualAnalysisResponse(BaseModel):
    id: str
    analysis_id: str
    animal_id: str
    animal_tag: Optional[str] = None
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    media_type: str = Field(default="image", description="Media type: image or video")
    filename: str
    media_hash: str
    file_size_bytes: int
    animal_detected: str = Field(default="cattle", description="Detected animal species class")
    detection_confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    observations: list[VisualObservation] = Field(default_factory=list)
    visual_risk_score: float = Field(..., ge=0.0, le=100.0, description="0-100 visual health risk score")
    risk_category: VisualRiskCategory = Field(default="LOW")
    model_name: str = Field(default="VETRA-VisualEngine")
    model_version: str = Field(default="v1.0")
    processing_time_ms: float = Field(default=0.0)
    requires_veterinary_review: bool = Field(default=False)
    review_status: ReviewStatus = Field(default="pending")
    veterinary_case_id: Optional[str] = None
    explanation: str = Field(default="")
    created_at: str
    clinical_safety_notice: str = Field(default=CLINICAL_SAFETY_DISCLAIMER)


class VideoFrameSample(BaseModel):
    frame_index: int
    timestamp_sec: float
    observations: list[VisualObservation] = Field(default_factory=list)
    frame_risk_score: float


class VideoAnalysisResponse(BaseModel):
    analysis_id: str
    animal_id: str
    animal_tag: Optional[str] = None
    farm_id: str
    filename: str
    media_hash: str
    duration_sec: float
    total_frames_sampled: int
    observations_detected: list[VisualObservation] = Field(default_factory=list)
    observation_frequency: dict[str, int] = Field(default_factory=dict)
    temporal_consistency: str = Field(..., description="Consistent, intermittent, or isolated")
    visual_risk_score: float
    risk_category: VisualRiskCategory
    model_name: str
    model_version: str
    processing_time_ms: float
    requires_veterinary_review: bool
    explanation: str
    created_at: str
    clinical_safety_notice: str = Field(default=CLINICAL_SAFETY_DISCLAIMER)


# ============================================================
# MULTIMODAL HEALTH ASSESSMENT SCHEMAS
# ============================================================

class MultimodalAssessmentCreate(BaseModel):
    animal_id: str = Field(..., description="Animal ID for multimodal fusion")
    visual_analysis_id: Optional[str] = Field(None, description="Optional specific visual analysis to link")


class MultimodalAssessmentResponse(BaseModel):
    id: str
    assessment_id: str
    animal_id: str
    animal_tag: Optional[str] = None
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    visual_analysis_id: Optional[str] = None
    visual_score: float
    telemetry_score: float
    disease_risk: float
    preventive_risk: float
    surveillance_risk: float
    combined_risk: float
    risk_category: VisualRiskCategory
    contributing_factors: list[str] = Field(default_factory=list)
    visual_telemetry_consistency: str = Field(
        ...,
        description="directional consistency: consistent, divergent, isolated_visual, isolated_telemetry, nominal"
    )
    explanation: str
    recommended_action: str
    veterinary_review_required: bool
    veterinary_case_id: Optional[str] = None
    created_at: str
    clinical_safety_notice: str = Field(default=CLINICAL_SAFETY_DISCLAIMER)


# ============================================================
# TEMPORAL COMPARISON & ESCALATION SCHEMAS
# ============================================================

class TemporalVisualComparison(BaseModel):
    animal_id: str
    animal_tag: Optional[str] = None
    earlier_analysis_id: str
    latest_analysis_id: str
    earlier_date: str
    latest_date: str
    trajectory: str = Field(..., description="improved, stable, worsening, new_signal")
    changes: list[dict[str, Any]] = Field(default_factory=list)
    persistent_indicators: list[str] = Field(default_factory=list)
    explanation: str


class VisualVeterinaryCaseCreate(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000, description="Veterinary referral notes")
    priority: Optional[str] = Field(None, description="Triage priority: low, medium, high, critical")


class VisualSurveillanceReviewCreate(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000, description="Holding syndromic surveillance notes")


class VisualHealthSummary(BaseModel):
    total_analyses: int
    animals_assessed: int
    total_observations: int
    high_risk_analyses: int
    pending_reviews: int
    multimodal_assessments_count: int
    dominant_visual_signals: list[dict[str, Any]] = Field(default_factory=list)

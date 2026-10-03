"""
backend/app/schemas/predictive.py
=================================
VETRA Phase 11 — Pydantic Schemas for Predictive Health Intelligence.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


PredictiveRiskCategory = Literal[
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
    "INSUFFICIENT_DATA"
]

PredictiveTrend = Literal[
    "stable",
    "improving",
    "deteriorating",
    "rapid_deterioration",
    "volatile",
    "insufficient_data"
]


class PredictiveAssessmentCreate(BaseModel):
    forecast_window_hours: int = Field(default=48, ge=24, le=72)
    force_refresh: bool = False


class PredictiveAssessmentResponse(BaseModel):
    id: Optional[str] = None
    assessment_id: str
    animal_id: str
    animal_tag: Optional[str] = None
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None

    current_health_risk: float = Field(..., ge=0.0, le=100.0)
    predicted_health_risk: float = Field(..., ge=0.0, le=100.0)
    forecast_window_hours: int = Field(default=48)
    risk_category: PredictiveRiskCategory
    confidence: float = Field(..., ge=0.0, le=1.0)

    trend: PredictiveTrend
    trend_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    primary_drivers: list[str] = Field(default_factory=list)
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)

    explanation: str
    recommended_action: str
    clinical_safety_notice: str

    model_name: str
    model_version: str
    feature_version: str
    training_status: str
    created_at: str


class PredictiveWatchlistItem(BaseModel):
    animal_id: str
    animal_tag: str
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    current_health_risk: float
    predicted_health_risk: float
    forecast_window_hours: int
    risk_category: PredictiveRiskCategory
    trend: PredictiveTrend
    confidence: float
    primary_driver: str
    last_update: str
    recommended_action: str
    operational_urgency: Literal["CRITICAL", "HIGH", "ELEVATED", "MODERATE", "ROUTINE"]


class FarmPredictiveSummaryResponse(BaseModel):
    farm_id: str
    farm_name: Optional[str] = None
    animal_count: int
    animals_with_predictions: int
    low_risk_count: int
    moderate_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    average_predicted_risk: float
    trend: str
    confidence: float
    status: Literal["active", "insufficient_data"]
    evaluated_at: str


class PredictiveTrendPoint(BaseModel):
    timestamp: str
    average_predicted_risk: float
    high_risk_count: int
    critical_risk_count: int
    total_evaluated: int


class PredictiveTrendResponse(BaseModel):
    farm_id: Optional[str] = None
    timeframe: str
    points: list[PredictiveTrendPoint]
    overall_trend: str


class ModelStatusResponse(BaseModel):
    model_name: str
    model_version: str
    feature_version: str
    training_status: str
    supported_windows_hours: list[int]
    models: list[dict[str, Any]]
    clinical_safety_compliance: bool
    status: str


class EscalateToCaseRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None

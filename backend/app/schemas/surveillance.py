from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


DiseaseEventStatus = Literal[
    "suspected",
    "under_investigation",
    "confirmed",
    "ruled_out",
    "resolved"
]

DiseaseEventSource = Literal[
    "health_monitoring",
    "ai_detection",
    "veterinary_case",
    "manual_report",
    "preventive_screening",
    "laboratory_result"
]

SurveillanceSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical"
]

SurveillanceRiskCategory = Literal[
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL"
]


# ============================================================
# DISEASE EVENT SCHEMAS
# ============================================================

class DiseaseEventCreate(BaseModel):
    farm_id: str = Field(..., description="ID of the affected farm")
    animal_id: Optional[str] = Field(None, description="Optional ID of a specific index animal")
    disease_name: str = Field(..., min_length=2, max_length=150, description="Name or clinical syndrome of the suspected disease")
    disease_category: str = Field(default="general", max_length=100, description="Syndromic category: respiratory, enteric, metabolic, etc.")
    symptoms: list[str] = Field(default_factory=list, description="List of observed symptoms or clinical signs")
    observed_signs: list[str] = Field(default_factory=list, description="Specific vital or behavioral abnormalities observed")
    severity: SurveillanceSeverity = Field(default="medium", description="Initial severity assessment")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Clinical or algorithmic confidence score")
    source: DiseaseEventSource = Field(default="manual_report", description="Originating source of the event")
    onset_date: Optional[str] = Field(None, description="Estimated date of onset (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=2000, description="Clinical notes or observations")


class DiseaseEventUpdate(BaseModel):
    status: Optional[DiseaseEventStatus] = Field(None, description="Updated lifecycle status")
    severity: Optional[SurveillanceSeverity] = Field(None, description="Updated severity")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    veterinarian_id: Optional[str] = Field(None, description="Assigned investigating veterinarian")
    veterinarian_name: Optional[str] = Field(None, description="Name of investigating veterinarian")
    veterinary_case_id: Optional[str] = Field(None, description="Linked veterinary clinical case ID")
    investigation_started_at: Optional[str] = None
    investigation_completed_at: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=2000)


class DiseaseEventResponse(BaseModel):
    id: str
    event_number: str
    farm_id: str
    farm_name: str
    animal_id: Optional[str] = None
    animal_tag: Optional[str] = None
    animal_name: Optional[str] = None
    disease_name: str
    disease_category: str
    symptoms: list[str] = Field(default_factory=list)
    observed_signs: list[str] = Field(default_factory=list)
    severity: str
    confidence: float
    source: str
    status: str
    reported_by: str
    reporter_role: str
    veterinarian_id: Optional[str] = None
    veterinarian_name: Optional[str] = None
    veterinary_case_id: Optional[str] = None
    onset_date: Optional[str] = None
    investigation_started_at: Optional[str] = None
    investigation_completed_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


# ============================================================
# DISEASE OBSERVATION SCHEMAS
# ============================================================

class DiseaseObservationItem(BaseModel):
    id: str
    animal_id: str
    animal_tag: str
    animal_name: Optional[str] = None
    farm_id: str
    farm_name: Optional[str] = None
    timestamp: str
    indicator: str
    value: Any
    threshold_or_reference: str
    severity: str
    source: str
    confidence: float


# ============================================================
# DISEASE CLUSTER SCHEMAS
# ============================================================

class DiseaseClusterResponse(BaseModel):
    cluster_id: str
    title: str
    disease_pattern: str
    farm_ids: list[str]
    farm_names: list[str]
    animal_ids: list[str]
    animal_tags: list[str]
    observation_count: int
    affected_animal_count: int
    first_detected: str
    last_detected: str
    geographic_spread: str
    risk_score: float
    confidence: float
    status: str
    recommended_action: str
    contributing_factors: list[str] = Field(default_factory=list)
    clinical_disclaimer: str = Field(
        default="Decision Support Only: Potential statistical cluster. Requires authorized veterinary confirmation before declaring outbreak."
    )


# ============================================================
# FARM RISK PROFILE SCHEMAS
# ============================================================

class FarmRiskProfileResponse(BaseModel):
    farm_id: str
    farm_name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    total_animals: int
    affected_animals_count: int
    abnormal_animals_pct: float
    active_alerts_count: int
    active_disease_events_count: int
    veterinary_cases_count: int
    risk_score: float
    risk_category: SurveillanceRiskCategory
    dominant_disease_pattern: str
    trend: str
    confidence: float
    contributing_factors: list[str] = Field(default_factory=list)
    affected_animal_tags: list[str] = Field(default_factory=list)
    generated_at: str


# ============================================================
# HOTSPOT & REGIONAL SCHEMAS
# ============================================================

class HotspotResponse(BaseModel):
    hotspot_id: str
    center_latitude: float
    center_longitude: float
    radius_km: float
    affected_farm_ids: list[str]
    affected_farm_names: list[str]
    affected_animal_count: int
    risk_score: float
    dominant_disease_pattern: str
    confidence: float
    status: str
    recommendation: str


class RegionalSurveillanceItem(BaseModel):
    region_key: str
    farms_count: int
    animals_count: int
    high_risk_farms_count: int
    active_alerts_count: int
    active_disease_events_count: int
    active_clusters_count: int
    average_risk_score: float
    surveillance_level: str
    dominant_patterns: list[str] = Field(default_factory=list)
    trend: str


# ============================================================
# TOP-LEVEL OVERVIEW & DASHBOARD SCHEMAS
# ============================================================

class SurveillanceOverviewResponse(BaseModel):
    farms_monitored: int
    animals_monitored: int
    high_risk_farms_count: int
    active_events_count: int
    potential_clusters_count: int
    geographic_hotspots_count: int
    surveillance_status: str
    advisory: str
    clinical_safety_notice: str = Field(
        default="VETRA Surveillance tracks statistical physiological clustering and risk patterns. Official epidemiological confirmation requires licensed veterinary pathology review."
    )
    generated_at: str


class SurveillanceTrendPoint(BaseModel):
    date: str
    observation_count: int
    affected_animals: int
    affected_farms: int
    average_risk_score: float
    alert_count: int
    case_count: int


class SurveillanceTrendsResponse(BaseModel):
    period_days: int
    time_series: list[SurveillanceTrendPoint]
    summary: dict[str, Any] = Field(default_factory=dict)


class SurveillanceRiskMapItem(BaseModel):
    farm_id: str
    farm_name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_coordinates: bool
    risk_score: float
    risk_category: str
    affected_animals: int
    active_alerts: int
    status_color: str


class SurveillanceWatchlistItem(BaseModel):
    farm_id: str
    farm_name: str
    location: str
    risk_score: float
    risk_category: str
    affected_animals: int
    active_alerts: int
    dominant_pattern: str
    last_signal: str
    recommended_action: str

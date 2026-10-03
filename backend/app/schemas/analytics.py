from typing import Any, Optional
from pydantic import BaseModel, Field


class RiskCategoryDetail(BaseModel):
    count: int = 0
    percentage: float = 0.0


class HealthRiskDistribution(BaseModel):
    low: RiskCategoryDetail
    medium: RiskCategoryDetail
    high: RiskCategoryDetail
    critical: RiskCategoryDetail


class HerdHealthIndexDetail(BaseModel):
    score: float
    band: str
    summary: str
    contributing_positive: list[str] = Field(default_factory=list)
    contributing_negative: list[str] = Field(default_factory=list)
    trend: str = "stable"


class OverviewKPIs(BaseModel):
    total_farms: int = 0
    total_animals: int = 0
    healthy_animals: int = 0
    animals_under_monitoring: int = 0
    high_risk_animals: int = 0
    critical_animals: int = 0
    active_alerts: int = 0
    critical_alerts: int = 0
    high_alerts: int = 0
    preventive_actions_due: int = 0
    open_veterinary_cases: int = 0
    devices_online: int = 0
    total_devices: int = 0
    telemetry_volume: int = 0
    preventive_compliance: float = 100.0


class OverviewAnalyticsResponse(BaseModel):
    kpis: OverviewKPIs
    risk_distribution: HealthRiskDistribution
    herd_health_index: HerdHealthIndexDetail
    generated_at: str


class HealthTrendsResponse(BaseModel):
    period_days: int
    total_readings: int
    time_series: list[dict[str, Any]] = Field(default_factory=list)
    averages: dict[str, float] = Field(default_factory=dict)
    empty: bool = False
    message: Optional[str] = None
    safe_zones: Optional[dict[str, Any]] = None


class AlertAnalyticsResponse(BaseModel):
    period_days: int
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    severity_distribution: dict[str, int]
    type_distribution: list[dict[str, Any]] = Field(default_factory=list)
    trends_over_time: list[dict[str, Any]] = Field(default_factory=list)
    mtta_minutes: Optional[float] = None
    mttr_minutes: Optional[float] = None
    mtta_display: str = "Insufficient historical data"
    mttr_display: str = "Insufficient historical data"
    empty: bool = False


class PreventionAnalyticsResponse(BaseModel):
    total_records: int
    completed_count: int
    due_today_count: int
    due_soon_count: int
    overdue_count: int
    upcoming_count: int
    compliance_rate: float
    categories: dict[str, Any]
    due_actions: list[dict[str, Any]] = Field(default_factory=list)
    empty: bool = False


class VeterinaryAnalyticsResponse(BaseModel):
    total_cases: int
    open_cases: int
    resolved_cases: int
    status_distribution: dict[str, int]
    priority_distribution: dict[str, int]
    type_distribution: list[dict[str, Any]] = Field(default_factory=list)
    avg_resolution_hours: Optional[float] = None
    avg_resolution_display: str = "Insufficient historical data"
    vet_workload: list[dict[str, Any]] = Field(default_factory=list)
    empty: bool = False


class DeviceAnalyticsResponse(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    avg_battery: float
    low_battery_count: int
    sensor_coverage_pct: float
    latest_reading_time: Optional[str] = None
    freshness_minutes: Optional[float] = None
    freshness_display: str
    devices: list[dict[str, Any]] = Field(default_factory=list)
    empty: bool = False


class DiseaseRiskAnalyticsResponse(BaseModel):
    total_screened: int
    disease_risk_distribution: dict[str, int]
    early_warning_distribution: dict[str, int]
    suspected_patterns: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str


class FarmPerformanceItem(BaseModel):
    farm_id: str
    farm_name: str
    location: str
    total_animals: int
    health_index: float
    health_band: str
    active_alerts: int
    open_cases: int
    critical_animals: int
    at_risk_animals: int


class WatchlistResponse(BaseModel):
    critical_attention: list[dict[str, Any]] = Field(default_factory=list)
    high_risk: list[dict[str, Any]] = Field(default_factory=list)
    monitoring: list[dict[str, Any]] = Field(default_factory=list)
    preventive_due: list[dict[str, Any]] = Field(default_factory=list)

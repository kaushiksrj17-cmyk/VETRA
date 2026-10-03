from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.permissions import require_any_authenticated_user
from app.schemas.analytics import (
    AlertAnalyticsResponse,
    DeviceAnalyticsResponse,
    DiseaseRiskAnalyticsResponse,
    FarmPerformanceItem,
    HealthTrendsResponse,
    OverviewAnalyticsResponse,
    PreventionAnalyticsResponse,
    VeterinaryAnalyticsResponse,
    WatchlistResponse,
)
from app.services.analytics_service import (
    get_alert_analytics,
    get_device_analytics,
    get_disease_risk_analytics,
    get_farm_performance,
    get_health_trends,
    get_overview_analytics,
    get_prevention_analytics,
    get_veterinary_analytics,
    get_watchlist,
)


router = APIRouter(
    prefix="/analytics",
    tags=["Advanced Analytics & Dashboards"]
)


@router.get(
    "/overview",
    response_model=OverviewAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_overview(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    species: Optional[str] = Query(None, description="Optional livestock species filter"),
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get real-time operational overview KPIs, risk distribution,
    and Herd Health Index (HHI) for the active user's authorized scope.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_overview_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id,
        species=species,
        days=days
    )


@router.get(
    "/health-trends",
    response_model=HealthTrendsResponse,
    status_code=status.HTTP_200_OK
)
def get_trends(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    animal_id: Optional[str] = Query(None, description="Optional individual animal ID filter"),
    species: Optional[str] = Query(None, description="Optional livestock species filter"),
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get aggregated time-series physiological vitals trends (temperature, heart rate,
    respiration, activity, rumination) with clinical safe reference zones.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_health_trends(
        user_id=user_id,
        role=role,
        farm_id=farm_id,
        animal_id=animal_id,
        species=species,
        days=days
    )


@router.get(
    "/alerts",
    response_model=AlertAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_alerts_analysis(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get alert analytics including severity distribution, alert types, time trends,
    and MTTA (Mean Time to Acknowledge) / MTTR (Mean Time to Resolve).
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_alert_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id,
        days=days
    )


@router.get(
    "/prevention",
    response_model=PreventionAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_prevention_analysis(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get preventive healthcare analytics including compliance rate formula,
    due/overdue task breakdowns, and category progress.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_prevention_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id
    )


@router.get(
    "/veterinary",
    response_model=VeterinaryAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_veterinary_analysis(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get veterinary clinical case workload, case status distribution, priority metrics,
    average resolution turnaround, and veterinarian distribution.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_veterinary_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id
    )


@router.get(
    "/devices",
    response_model=DeviceAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_device_analysis(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get IoT hardware fleet analytics including online/offline nodes, battery health,
    telemetry freshness, and animal-sensor pairing coverage.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_device_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id
    )


@router.get(
    "/disease-risk",
    response_model=DiseaseRiskAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_disease_risk_analysis(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get AI Disease Intelligence population screening patterns and early-warning signals.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_disease_risk_analytics(
        user_id=user_id,
        role=role,
        farm_id=farm_id
    )


@router.get(
    "/farms",
    response_model=list[FarmPerformanceItem],
    status_code=status.HTTP_200_OK
)
def get_farms_comparison(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get multi-farm operational and health performance benchmarks.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_farm_performance(
        user_id=user_id,
        role=role
    )


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    status_code=status.HTTP_200_OK
)
def get_operational_watchlist(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get targeted operational watchlists for immediate triage:
    critical attention, high risk, under monitoring, and preventive due.
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "farmer")

    return get_watchlist(
        user_id=user_id,
        role=role,
        farm_id=farm_id
    )

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import (
    get_current_user,
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.surveillance import (
    DiseaseClusterResponse,
    DiseaseEventCreate,
    DiseaseEventResponse,
    DiseaseEventUpdate,
    DiseaseObservationItem,
    FarmRiskProfileResponse,
    HotspotResponse,
    RegionalSurveillanceItem,
    SurveillanceOverviewResponse,
    SurveillanceRiskMapItem,
    SurveillanceTrendsResponse,
    SurveillanceWatchlistItem,
)
from app.services.disease_cluster_engine import detect_disease_clusters
from app.services.geospatial_service import detect_hotspots
from app.services.surveillance_service import (
    create_disease_event,
    ensure_surveillance_indexes,
    extract_disease_observations,
    get_disease_event,
    get_farm_risk_profiles,
    get_regional_surveillance,
    get_surveillance_overview,
    get_surveillance_risk_map,
    get_surveillance_trends,
    get_surveillance_watchlist,
    list_disease_events,
    trigger_surveillance_analysis,
    update_disease_event,
)

router = APIRouter(
    prefix="/surveillance",
    tags=["Disease Surveillance & Geospatial Intelligence"]
)


@router.on_event("startup")
def startup_surveillance():
    ensure_surveillance_indexes()


# ============================================================
# OVERVIEW & WATCHLIST & RISK MAP
# ============================================================

@router.get("/overview", response_model=SurveillanceOverviewResponse)
def get_overview(
    window_days: int = Query(7, ge=1, le=90, description="Surveillance time window in days"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get top-level surveillance KPI metrics and active advisory.
    """
    db = get_database()
    return get_surveillance_overview(db, current_user, window_days=window_days)


@router.get("/farms", response_model=list[FarmRiskProfileResponse])
def get_farms_risk(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List farm risk profiles with contributing factor breakdowns.
    """
    db = get_database()
    return get_farm_risk_profiles(db, current_user, window_days=window_days)


@router.get("/farm/{farm_id}", response_model=FarmRiskProfileResponse)
def get_single_farm_risk(
    farm_id: str,
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get detailed risk evaluation for a specific farm.
    """
    db = get_database()
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    target = next((p for p in profiles if p["farm_id"] == farm_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm surveillance profile not found for farm {farm_id} or unauthorized."
        )
    return target


@router.get("/watchlist", response_model=list[SurveillanceWatchlistItem])
def get_watchlist(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get high-risk farm surveillance watchlist.
    """
    db = get_database()
    return get_surveillance_watchlist(db, current_user, window_days=window_days)


@router.get("/risk-map", response_model=list[SurveillanceRiskMapItem])
def get_risk_map(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get geospatial farm coordinates and risk levels for interactive mapping.
    """
    db = get_database()
    return get_surveillance_risk_map(db, current_user, window_days=window_days)


# ============================================================
# DISEASE EVENTS & OBSERVATIONS
# ============================================================

@router.get("/diseases")
def get_disease_patterns(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get summary of observed and cataloged disease patterns across holdings.
    """
    db = get_database()
    profiles = get_farm_risk_profiles(db, current_user)
    patterns: dict[str, int] = {}
    for p in profiles:
        pattern = p.get("dominant_disease_pattern", "Baseline")
        patterns[pattern] = patterns.get(pattern, 0) + 1

    return {
        "cataloged_patterns": [
            "Thermal Elevation / Fever Syndrome",
            "Bovine Respiratory Disease (BRD) Complex",
            "Rumination & Metabolic Depression",
            "Enteric / Digestive Disturbance",
            "Multi-system Physiological Anomaly"
        ],
        "active_pattern_distribution": patterns
    }


@router.get("/observations", response_model=list[DiseaseObservationItem])
def get_observations(
    farm_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Extract dynamic disease observations from telemetry deviations.
    """
    db = get_database()
    return extract_disease_observations(db, farm_id=farm_id, limit=limit)


@router.get("/events", response_model=list[DiseaseEventResponse])
def get_events(
    farm_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List reported disease events under surveillance.
    """
    db = get_database()
    return list_disease_events(db, farm_id=farm_id, status=status_filter, limit=limit)


@router.post("/events", response_model=DiseaseEventResponse, status_code=status.HTTP_201_CREATED)
def report_disease_event(
    event_in: DiseaseEventCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Report a new suspected disease event.
    """
    db = get_database()
    return create_disease_event(event_in.model_dump(), current_user, db)


@router.get("/events/{event_id}", response_model=DiseaseEventResponse)
def get_single_event(
    event_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Retrieve single disease event details.
    """
    db = get_database()
    event = get_disease_event(event_id, db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disease event '{event_id}' not found."
        )
    return event


@router.put("/events/{event_id}", response_model=DiseaseEventResponse)
def update_event(
    event_id: str,
    update_in: DiseaseEventUpdate,
    current_user: dict = Depends(require_vet_or_admin)
):
    """
    Update disease event lifecycle status or clinical investigation details.
    Requires Veterinarian or Administrator permission.
    """
    db = get_database()
    updated = update_disease_event(event_id, update_in.model_dump(exclude_unset=True), current_user, db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disease event '{event_id}' not found."
        )
    return updated


# ============================================================
# CLUSTERS & HOTSPOTS
# ============================================================

@router.get("/clusters", response_model=list[DiseaseClusterResponse])
def get_clusters(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    List potential statistical disease clusters across holdings.
    """
    db = get_database()
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    return detect_disease_clusters(profiles, db, window_days=window_days)


@router.get("/clusters/{cluster_id}", response_model=DiseaseClusterResponse)
def get_single_cluster(
    cluster_id: str,
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get detailed information for a specific disease cluster.
    """
    db = get_database()
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    clusters = detect_disease_clusters(profiles, db, window_days=window_days)
    target = next((c for c in clusters if c["cluster_id"] == cluster_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{cluster_id}' not found."
        )
    return target


@router.get("/hotspots", response_model=list[HotspotResponse])
def get_hotspots_route(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Detect geographic disease hotspots based on farm proximity and elevated risk.
    """
    db = get_database()
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    return detect_hotspots(profiles, max_radius_km=30.0)


# ============================================================
# REGIONAL SURVEILLANCE & TRENDS
# ============================================================

@router.get("/regions", response_model=list[RegionalSurveillanceItem])
def get_regions(
    window_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get regional surveillance aggregated by district or state.
    """
    db = get_database()
    return get_regional_surveillance(db, current_user, window_days=window_days)


@router.get("/trends", response_model=SurveillanceTrendsResponse)
def get_trends(
    period_days: int = Query(30, ge=1, le=90, description="Rolling historical period in days"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Get bounded day-by-day surveillance trends.
    """
    db = get_database()
    return get_surveillance_trends(db, current_user, period_days=period_days)


# ============================================================
# AI SURVEILLANCE INTELLIGENCE
# ============================================================

@router.post("/analyze")
def run_surveillance_analysis(
    farm_id: Optional[str] = Query(None, description="Optional target farm ID for tailored analysis"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Execute AI disease surveillance synthesis with deterministic fallback.
    """
    db = get_database()
    return trigger_surveillance_analysis(farm_id, current_user, db)

"""
backend/app/routes/predictive.py
================================
VETRA Phase 11 — Predictive Health Intelligence & Forecasting REST Endpoints.

All endpoints are authenticated and adhere to VETRA RBAC policies.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.permissions import (
    get_current_user,
    require_any_authenticated_user,
    require_vet_or_admin,
)
from app.schemas.predictive import (
    EscalateToCaseRequest,
    FarmPredictiveSummaryResponse,
    ModelStatusResponse,
    PredictiveAssessmentCreate,
    PredictiveAssessmentResponse,
    PredictiveTrendResponse,
    PredictiveWatchlistItem,
)
from app.services.predictive_service import (
    analyze_animal_predictive,
    ensure_predictive_indexes,
    escalate_to_veterinary_case,
    get_animal_latest_prediction,
    get_animal_prediction_history,
    get_farm_predictive_summary,
    get_model_status,
    get_predictive_trends,
    get_predictive_watchlist,
)

router = APIRouter(
    prefix="/predictive",
    tags=["Predictive Health Intelligence & Forecasting"]
)


@router.on_event("startup")
def startup_predictive():
    ensure_predictive_indexes()


# ============================================================
# 1. ANIMAL PREDICTIVE ANALYSIS & RETRIEVAL
# ============================================================

@router.post(
    "/analyze/animal/{animal_id}",
    response_model=PredictiveAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger predictive health analysis for animal"
)
def trigger_animal_analysis(
    animal_id: str,
    forecast_window_hours: int = Query(48, ge=24, le=72, description="Forecast window in hours (24, 48, 72)"),
    force_refresh: bool = Query(False, description="Bypass 5-minute cache and recompute immediately"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Executes prospective health risk analysis for the specified animal.
    Extracts multi-domain telemetry and visual features, runs deterministic forecasting baseline,
    and returns calibrated risk score, trend trajectory, and primary risk drivers.
    """
    try:
        assessment = analyze_animal_predictive(
            animal_id=animal_id,
            forecast_window_hours=forecast_window_hours,
            force_refresh=force_refresh
        )
        return assessment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Predictive analysis failure: {str(e)}"
        )


@router.get(
    "/animal/{animal_id}",
    response_model=PredictiveAssessmentResponse,
    summary="Get latest predictive health assessment for animal"
)
def get_animal_prediction(
    animal_id: str,
    forecast_window: Optional[int] = Query(None, description="Optional filter by forecast window hours (24, 48, 72)"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Retrieves the most recent prospective assessment for an animal, computing one if none exists."""
    try:
        return get_animal_latest_prediction(animal_id, forecast_window_hours=forecast_window)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve animal prediction: {str(e)}"
        )


@router.get(
    "/history/{animal_id}",
    response_model=list[PredictiveAssessmentResponse],
    summary="Get historical predictive assessments for animal"
)
def get_prediction_history(
    animal_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum historical records to return"),
    forecast_window: Optional[int] = Query(None, description="Optional filter by forecast window hours"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns chronological prospective assessments for an animal."""
    try:
        return get_animal_prediction_history(
            animal_id=animal_id,
            limit=limit,
            forecast_window_hours=forecast_window
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query prediction history: {str(e)}"
        )


# ============================================================
# 2. FARM & HERD PREDICTIVE INTELLIGENCE
# ============================================================

@router.get(
    "/farm/{farm_id}",
    response_model=FarmPredictiveSummaryResponse,
    summary="Get farm-level predictive health index & risk distribution"
)
def get_farm_prediction(
    farm_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Computes herd-level prospective risk indices, risk tiers, and population trends."""
    try:
        return get_farm_predictive_summary(farm_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute farm predictive summary: {str(e)}"
        )


@router.get(
    "/summary",
    summary="Get overall herd predictive intelligence summary"
)
def get_predictive_summary_overview(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns aggregated predictive health statistics across all animals or a specific farm."""
    db = get_database()
    farms = [farm_id] if farm_id else [str(f["_id"]) for f in db.farms.find({}, {"_id": 1})]

    total_animals = 0
    total_evaluated = 0
    low_c = 0
    mod_c = 0
    high_c = 0
    crit_c = 0
    avg_risks = []

    for f_id in farms:
        summary = get_farm_predictive_summary(f_id)
        total_animals += summary["animal_count"]
        total_evaluated += summary["animals_with_predictions"]
        low_c += summary["low_risk_count"]
        mod_c += summary["moderate_risk_count"]
        high_c += summary["high_risk_count"]
        crit_c += summary["critical_risk_count"]
        if summary["animals_with_predictions"] > 0:
            avg_risks.append(summary["average_predicted_risk"])

    overall_avg = round(float(sum(avg_risks) / len(avg_risks)), 1) if avg_risks else 0.0

    return {
        "farm_id": farm_id,
        "total_farms_monitored": len(farms),
        "total_animals": total_animals,
        "animals_under_prediction": total_evaluated,
        "prediction_coverage_pct": round((total_evaluated / total_animals * 100.0) if total_animals > 0 else 0.0, 1),
        "low_risk_count": low_c,
        "moderate_risk_count": mod_c,
        "high_risk_count": high_c,
        "critical_risk_count": crit_c,
        "average_predicted_risk": overall_avg,
        "clinical_safety_notice": "Decision Support Only: Not a definitive medical diagnosis."
    }


# ============================================================
# 3. WATCHLIST & HIGH-RISK FORECASTS
# ============================================================

@router.get(
    "/watchlist",
    response_model=list[PredictiveWatchlistItem],
    summary="Get prioritized deterioration watchlist"
)
def get_watchlist(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum watchlist items"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Returns prioritized operational watchlist of animals exhibiting:
    - Rapid deterioration
    - Critical or high prospective health risk
    - Persistent visual + telemetry convergence
    Sorted by operational urgency without arbitrary ranking.
    """
    try:
        return get_predictive_watchlist(farm_id=farm_id, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate predictive watchlist: {str(e)}"
        )


@router.get(
    "/high-risk",
    response_model=list[PredictiveWatchlistItem],
    summary="Get animals with elevated or critical predicted risk"
)
def get_high_risk_predictions(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Convenience endpoint returning only animals classified as HIGH or CRITICAL predicted risk."""
    watchlist = get_predictive_watchlist(farm_id=farm_id, limit=limit)
    return [w for w in watchlist if w["risk_category"] in ("HIGH", "CRITICAL")]


# ============================================================
# 4. TRENDS & MODEL STATUS
# ============================================================

@router.get(
    "/trends",
    response_model=PredictiveTrendResponse,
    summary="Get prospective health risk trends over time"
)
def get_trends(
    farm_id: Optional[str] = Query(None, description="Optional farm ID filter"),
    timeframe: str = Query("7d", pattern="^(24h|48h|7d|30d)$", description="Trend timeframe (24h, 48h, 7d, 30d)"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Returns historical risk trajectory aggregate data points for Plotly visualization."""
    try:
        return get_predictive_trends(farm_id=farm_id, timeframe=timeframe)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query predictive trends: {str(e)}"
        )


@router.get(
    "/model-status",
    response_model=ModelStatusResponse,
    summary="Get predictive AI model version, health, and metadata"
)
def get_predictive_model_status_endpoint(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """Provides model transparency details: version, training status, and supported architectures."""
    return get_model_status()


# ============================================================
# 5. CLINICAL ESCALATION WORKFLOW
# ============================================================

@router.post(
    "/escalate/{assessment_id}",
    summary="Escalate predictive assessment into a clinical veterinary case"
)
def escalate_prediction_to_case(
    assessment_id: str,
    payload: EscalateToCaseRequest,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Escalates prospective deterioration findings into an actionable veterinary case.
    Populates clinical findings with primary drivers and confidence without auto-diagnosing.
    """
    try:
        new_case = escalate_to_veterinary_case(
            assessment_id=assessment_id,
            user_info=current_user,
            title=payload.title,
            notes=payload.notes,
            priority=payload.priority
        )
        return new_case
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate prediction to case: {str(e)}"
        )

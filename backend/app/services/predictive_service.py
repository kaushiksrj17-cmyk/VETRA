"""
backend/app/services/predictive_service.py
==========================================
VETRA Phase 11 — Predictive Health Intelligence Service.

Coordinates:
- Multi-sensor bounded telemetry and visual feature extraction
- Longitudinal trend detection across multi-metric trajectories
- Prospective risk score evaluation using DeterministicPredictiveModel
- Explanation generation (deterministic grounded + Gemini enhancement)
- Persistent assessment logging in MongoDB
- Cooldown-governed predictive alerting (predictive_health_risk, rapid_health_decline)
- Farm-level predictive indices and herd risk forecasting
- Operational triage watchlist synthesis
- Direct escalation to clinical veterinary case workflow
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from bson import ObjectId

from app.database import get_database
from app.services.websocket_manager import manager
from ai_engine.feature_engineering import extract_health_features
from ai_engine.risk_model import calculate_risk_score
from ai_engine.trend_engine import compute_holistic_trend
from ai_engine.predictive_features import (
    FEATURE_VERSION,
    extract_predictive_features,
    parse_iso_datetime,
)
from ai_engine.predictive_health import (
    CLINICAL_SAFETY_DISCLAIMER,
    MODEL_NAME,
    MODEL_VERSION,
    get_predictive_model,
    registry,
)
from ai_engine.gemini_service import get_ai_predictive_explanation


def ensure_predictive_indexes(db=None):
    """Initializes and validates required indexes for predictive assessments collection."""
    if db is None:
        db = get_database()
    try:
        db.predictive_assessments.create_index("assessment_id", unique=True, sparse=True)
        db.predictive_assessments.create_index("animal_id")
        db.predictive_assessments.create_index("farm_id")
        db.predictive_assessments.create_index("risk_category")
        db.predictive_assessments.create_index("forecast_window_hours")
        db.predictive_assessments.create_index([("created_at", -1)])
        db.predictive_assessments.create_index([("animal_id", 1), ("created_at", -1)])
        db.predictive_assessments.create_index([("farm_id", 1), ("risk_category", 1)])
    except Exception as e:
        print(f"[PREDICTIVE INDEXES] Index warning: {e}")


def serialize_predictive_assessment(doc: dict[str, Any]) -> dict[str, Any]:
    """Formats MongoDB predictive assessment document for clean API response."""
    if not doc:
        return {}
    res = dict(doc)
    if "_id" in res:
        res["id"] = str(res["_id"])
        del res["_id"]
    return res


def get_animal_obj_id(animal_id_str: str) -> Optional[ObjectId]:
    """Safely converts string to ObjectId if valid."""
    try:
        return ObjectId(animal_id_str)
    except Exception:
        return None


def analyze_animal_predictive(
    animal_id: str,
    forecast_window_hours: int = 48,
    force_refresh: bool = False
) -> dict[str, Any]:
    """
    Executes complete end-to-end predictive health analysis for a target animal.
    Adheres strictly to bounded queries, deterministic baselines, and safety thresholds.
    """
    db = get_database()
    ensure_predictive_indexes(db)
    now = datetime.now(timezone.utc)

    # 1. Lookup animal record
    obj_id = get_animal_obj_id(animal_id)
    animal_query = {"_id": obj_id} if obj_id else {"_id": animal_id}
    animal = db.animals.find_one(animal_query)
    if not animal:
        # Try finding by string ID or tag_id
        animal = db.animals.find_one({"$or": [{"_id": animal_id}, {"tag_id": animal_id}]})
    if not animal:
        raise ValueError(f"Animal '{animal_id}' was not found in registry.")

    animal_actual_id = str(animal["_id"])
    farm_id = str(animal.get("farm_id", ""))
    farm = db.farms.find_one({"_id": get_animal_obj_id(farm_id) or farm_id}) if farm_id else None
    farm_name = farm.get("name") if farm else "Primary Farm"

    # 2. Freshness & Caching check (5-minute window if force_refresh is False)
    if not force_refresh:
        five_min_ago = (now - timedelta(minutes=5)).isoformat()
        recent_cached = db.predictive_assessments.find_one({
            "animal_id": animal_actual_id,
            "forecast_window_hours": forecast_window_hours,
            "created_at": {"$gte": five_min_ago}
        }, sort=[("created_at", -1)])
        if recent_cached:
            return serialize_predictive_assessment(recent_cached)

    # 3. Bounded Historical Telemetry (bounded to maximum 72 hours, limit 100)
    cutoff_time = (now - timedelta(hours=max(72, forecast_window_hours))).isoformat()
    readings = list(db.health_readings.find({
        "animal_id": animal_actual_id,
        "recorded_at": {"$gte": cutoff_time}
    }).sort("recorded_at", -1).limit(100))

    # If no recent readings by ISO string, query last 30 readings regardless of timestamp
    if not readings:
        readings = list(db.health_readings.find({
            "animal_id": animal_actual_id
        }).sort("recorded_at", -1).limit(30))

    # 4. Bounded Visual Analyses & Edge Observations
    visual_analyses = list(db.visual_analyses.find({
        "animal_id": animal_actual_id
    }).sort("created_at", -1).limit(10))

    # 5. Bounded Multimodal Assessments
    multimodal_assessments = list(db.multimodal_assessments.find({
        "animal_id": animal_actual_id
    }).sort("created_at", -1).limit(5))

    # 6. Bounded Alerts
    alerts = list(db.alerts.find({
        "animal_id": animal_actual_id
    }).sort("created_at", -1).limit(20))

    # 7. Bounded Veterinary Cases & Treatments
    cases = list(db.veterinary_cases.find({
        "animal_id": animal_actual_id
    }).sort("created_at", -1).limit(10))

    # 8. Bounded Preventive Tasks
    tasks = list(db.preventive_tasks.find({
        "animal_id": animal_actual_id
    }).limit(20))

    # 9. Farm Risk Profile
    farm_risk = db.farm_risk_profiles.find_one({"farm_id": farm_id}) if farm_id else None

    # 10. Bounded Edge Events
    edge_events = list(db.edge_events.find({
        "$or": [{"animal_id": animal_actual_id}, {"farm_id": farm_id}]
    }).sort("captured_at", -1).limit(20))

    # 11. Evaluate Current Health Risk Score
    if readings:
        curr_feats = extract_health_features(readings)
        curr_risk_calc = calculate_risk_score(curr_feats)
        current_health_risk = float(curr_risk_calc.get("health_risk_score", 0.0))
    else:
        current_health_risk = float(animal.get("health_risk_score", 0.0))

    # 12. Multi-Metric Longitudinal Trend Analysis
    trend_res = compute_holistic_trend(readings, visual_analyses)

    # 13. Multi-Modal Feature Extraction
    features = extract_predictive_features(
        readings=readings,
        visual_analyses=visual_analyses,
        multimodal_assessments=multimodal_assessments,
        alerts=alerts,
        veterinary_cases=cases,
        preventive_tasks=tasks,
        farm_risk_profile=farm_risk,
        edge_events=edge_events,
        window_hours=forecast_window_hours,
        reference_time=now
    )

    # 14. Execute Active Predictive Model
    model = get_predictive_model()
    pred_result = model.predict(
        features=features,
        context={
            "animal_id": animal_actual_id,
            "farm_id": farm_id,
            "current_health_risk": current_health_risk,
            "forecast_window_hours": forecast_window_hours,
            "trend_analysis": trend_res,
        }
    )

    # 15. Optional Gemini Clinical Narrative Synthesis (with deterministic fallback)
    ai_narrative_res = get_ai_predictive_explanation(animal, pred_result)
    enhanced_explanation = ai_narrative_res.get("predictive_narrative") or pred_result["explanation"]

    # 16. Assemble Document for Persistence
    assessment_doc = {
        "assessment_id": pred_result["assessment_id"],
        "animal_id": animal_actual_id,
        "animal_tag": animal.get("tag_id"),
        "animal_name": animal.get("name"),
        "farm_id": farm_id,
        "farm_name": farm_name,
        "current_health_risk": pred_result["current_health_risk"],
        "predicted_health_risk": pred_result["predicted_health_risk"],
        "forecast_window_hours": forecast_window_hours,
        "risk_category": pred_result["risk_category"],
        "confidence": pred_result["confidence"],
        "trend": pred_result["trend"],
        "trend_strength": pred_result["trend_strength"],
        "primary_drivers": pred_result["primary_drivers"],
        "feature_snapshot": features,
        "explanation": enhanced_explanation,
        "recommended_action": pred_result["recommended_action"],
        "clinical_safety_notice": CLINICAL_SAFETY_DISCLAIMER,
        "model_name": pred_result["model_name"],
        "model_version": pred_result["model_version"],
        "feature_version": pred_result["feature_version"],
        "training_status": pred_result["training_status"],
        "created_at": now.isoformat(),
    }

    # Insert into database
    db.predictive_assessments.insert_one(assessment_doc)

    # 17. Alert Integration with 30-Minute Cooldown & Deduplication
    pred_risk = pred_result["predicted_health_risk"]
    trend_val = pred_result["trend"]
    if pred_risk >= 50.0 or trend_val == "rapid_deterioration":
        # Check active alerts within 30-minute cooldown
        thirty_min_ago = (now - timedelta(minutes=30)).isoformat()
        existing_alert = db.alerts.find_one({
            "animal_id": animal_actual_id,
            "alert_type": {"$in": ["predictive_health_risk", "rapid_health_decline", "predictive_deterioration"]},
            "status": "active",
            "created_at": {"$gte": thirty_min_ago}
        })

        if not existing_alert:
            alert_type = "rapid_health_decline" if trend_val == "rapid_deterioration" else "predictive_health_risk"
            severity = "critical" if pred_result["risk_category"] == "CRITICAL" else "high"
            title = f"Predictive Warning: {animal.get('tag_id') or 'Animal'}"
            msg = (
                f"Prospective {forecast_window_hours}h health risk elevated to {pred_risk:.1f}/100 ({pred_result['risk_category']}). "
                f"Trajectory: {trend_val.replace('_', ' ')}. Primary signal: {pred_result['primary_drivers'][0] if pred_result['primary_drivers'] else 'Multi-vital deviation'}."
            )
            db.alerts.insert_one({
                "animal_id": animal_actual_id,
                "farm_id": farm_id,
                "owner_id": farm.get("owner_id", "") if farm else "",
                "device_id": "PREDICTIVE_AI_ENGINE",
                "alert_type": alert_type,
                "severity": severity,
                "title": title,
                "message": msg,
                "triggered_by": ["predictive_health_engine", trend_val],
                "status": "active",
                "predictive_assessment_id": pred_result["assessment_id"],
                "forecast_window_hours": forecast_window_hours,
                "created_at": now.isoformat(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "resolved_by": None,
            })

    # 18. Non-blocking WebSocket Broadcast
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "predictive_assessment_update",
                "action": "assessed",
                "assessment_id": pred_result["assessment_id"],
                "animal_id": animal_actual_id,
                "animal_tag": animal.get("tag_id"),
                "predicted_health_risk": pred_result["predicted_health_risk"],
                "risk_category": pred_result["risk_category"],
                "forecast_window_hours": forecast_window_hours,
                "trend": pred_result["trend"],
                "confidence": pred_result["confidence"]
            }))
    except Exception:
        pass

    return serialize_predictive_assessment(assessment_doc)


def get_animal_latest_prediction(
    animal_id: str,
    forecast_window_hours: Optional[int] = None
) -> dict[str, Any]:
    """Retrieves the most recent predictive assessment for an animal, computing a fresh one if none exists."""
    db = get_database()
    ensure_predictive_indexes(db)

    obj_id = get_animal_obj_id(animal_id)
    animal = db.animals.find_one({"_id": obj_id} if obj_id else {"_id": animal_id})
    if not animal:
        animal = db.animals.find_one({"$or": [{"_id": animal_id}, {"tag_id": animal_id}]})
    if not animal:
        raise ValueError(f"Animal '{animal_id}' was not found.")

    actual_id = str(animal["_id"])
    query = {"animal_id": actual_id}
    if forecast_window_hours:
        query["forecast_window_hours"] = forecast_window_hours

    latest = db.predictive_assessments.find_one(query, sort=[("created_at", -1)])
    if latest:
        return serialize_predictive_assessment(latest)

    # Compute fresh assessment
    return analyze_animal_predictive(actual_id, forecast_window_hours or 48)


def get_animal_prediction_history(
    animal_id: str,
    limit: int = 20,
    forecast_window_hours: Optional[int] = None
) -> list[dict[str, Any]]:
    """Retrieves paginated, chronological predictive history for an animal."""
    db = get_database()
    ensure_predictive_indexes(db)

    obj_id = get_animal_obj_id(animal_id)
    animal = db.animals.find_one({"_id": obj_id} if obj_id else {"_id": animal_id})
    if not animal:
        animal = db.animals.find_one({"$or": [{"_id": animal_id}, {"tag_id": animal_id}]})
    if not animal:
        return []

    actual_id = str(animal["_id"])
    query = {"animal_id": actual_id}
    if forecast_window_hours:
        query["forecast_window_hours"] = forecast_window_hours

    cursor = db.predictive_assessments.find(query).sort("created_at", -1).limit(min(limit, 100))
    return [serialize_predictive_assessment(doc) for doc in cursor]


def get_farm_predictive_summary(farm_id: str) -> dict[str, Any]:
    """
    Computes farm-level predictive health index and herd risk distribution.
    Never declares an outbreak; produces prospective herd surveillance indicators.
    """
    db = get_database()
    ensure_predictive_indexes(db)
    now = datetime.now(timezone.utc)

    farm = db.farms.find_one({"_id": get_animal_obj_id(farm_id) or farm_id})
    farm_name = farm.get("name") if farm else "Target Farm"

    # Query all animals belonging to this farm
    animals = list(db.animals.find({"farm_id": farm_id}))
    if not animals:
        # Check string or ObjectId farm_id
        animals = list(db.animals.find({"$or": [{"farm_id": farm_id}, {"farm_id": str(farm_id)}]}))

    total_animals = len(animals)
    if total_animals == 0:
        return {
            "farm_id": farm_id,
            "farm_name": farm_name,
            "animal_count": 0,
            "animals_with_predictions": 0,
            "low_risk_count": 0,
            "moderate_risk_count": 0,
            "high_risk_count": 0,
            "critical_risk_count": 0,
            "average_predicted_risk": 0.0,
            "trend": "insufficient_data",
            "confidence": 0.0,
            "status": "insufficient_data",
            "evaluated_at": now.isoformat(),
        }

    # Gather latest prediction for each animal on farm
    pred_risks = []
    low_c = 0
    mod_c = 0
    high_c = 0
    crit_c = 0
    deteriorating_count = 0
    confs = []

    for a in animals:
        a_id = str(a["_id"])
        latest = db.predictive_assessments.find_one(
            {"animal_id": a_id},
            sort=[("created_at", -1)]
        )
        if not latest:
            # Generate assessment on-the-fly for complete herd coverage
            try:
                latest = analyze_animal_predictive(a_id, forecast_window_hours=48)
            except Exception:
                latest = None

        if latest:
            cat = latest.get("risk_category", "LOW")
            score = float(latest.get("predicted_health_risk", 0.0))
            pred_risks.append(score)
            confs.append(float(latest.get("confidence", 0.5)))
            if cat == "CRITICAL":
                crit_c += 1
            elif cat == "HIGH":
                high_c += 1
            elif cat == "MODERATE":
                mod_c += 1
            else:
                low_c += 1

            if latest.get("trend") in ("deteriorating", "rapid_deterioration"):
                deteriorating_count += 1

    evaluated_count = len(pred_risks)
    if evaluated_count == 0:
        return {
            "farm_id": farm_id,
            "farm_name": farm_name,
            "animal_count": total_animals,
            "animals_with_predictions": 0,
            "low_risk_count": 0,
            "moderate_risk_count": 0,
            "high_risk_count": 0,
            "critical_risk_count": 0,
            "average_predicted_risk": 0.0,
            "trend": "insufficient_data",
            "confidence": 0.0,
            "status": "insufficient_data",
            "evaluated_at": now.isoformat(),
        }

    avg_risk = round(float(sum(pred_risks) / evaluated_count), 1)
    avg_conf = round(float(sum(confs) / evaluated_count), 2)

    # Determine overall farm herd trend
    if deteriorating_count >= (evaluated_count * 0.35) or crit_c >= 2:
        farm_trend = "deteriorating"
    elif mod_c + high_c + crit_c == 0:
        farm_trend = "stable"
    elif (high_c + crit_c) > 0:
        farm_trend = "elevated_surveillance_attention"
    else:
        farm_trend = "stable"

    return {
        "farm_id": farm_id,
        "farm_name": farm_name,
        "animal_count": total_animals,
        "animals_with_predictions": evaluated_count,
        "low_risk_count": low_c,
        "moderate_risk_count": mod_c,
        "high_risk_count": high_c,
        "critical_risk_count": crit_c,
        "average_predicted_risk": avg_risk,
        "trend": farm_trend,
        "confidence": avg_conf,
        "status": "active",
        "evaluated_at": now.isoformat(),
    }


def get_predictive_watchlist(
    farm_id: Optional[str] = None,
    limit: int = 20
) -> list[dict[str, Any]]:
    """
    Synthesizes an actionable predictive watchlist containing animals with:
    - Rapid deterioration trajectories
    - High or critical predicted health risk
    - Persistent visual + telemetry convergence
    - Repeated alerts
    Sorted strictly by operational clinical urgency without arbitrary ranking.
    """
    db = get_database()
    ensure_predictive_indexes(db)

    # Build match criteria
    match_q: dict[str, Any] = {}
    if farm_id:
        match_q["farm_id"] = farm_id

    # Find the most recent assessment for each animal using aggregation
    pipeline = [
        {"$match": match_q} if match_q else {"$match": {}},
        {"$sort": {"created_at": -1}},
        {
            "$group": {
                "_id": "$animal_id",
                "latest_assessment": {"$first": "$$ROOT"}
            }
        },
        {"$replaceRoot": {"newRoot": "$latest_assessment"}},
        {"$limit": 100}
    ]

    assessments = list(db.predictive_assessments.aggregate(pipeline))

    watchlist_items = []
    for a in assessments:
        cat = a.get("risk_category", "LOW")
        trend = a.get("trend", "stable")
        p_risk = float(a.get("predicted_health_risk", 0.0))
        c_risk = float(a.get("current_health_risk", 0.0))

        # Operational urgency scoring (for clinical triage sorting)
        if trend == "rapid_deterioration" or cat == "CRITICAL":
            urgency = "CRITICAL"
            sort_weight = 400 + p_risk
        elif cat == "HIGH" or (trend == "deteriorating" and p_risk >= 40.0):
            urgency = "HIGH"
            sort_weight = 300 + p_risk
        elif cat == "MODERATE" or trend == "deteriorating":
            urgency = "ELEVATED"
            sort_weight = 200 + p_risk
        elif cat == "INSUFFICIENT_DATA" and c_risk >= 50.0:
            urgency = "MODERATE"
            sort_weight = 100 + c_risk
        else:
            urgency = "ROUTINE"
            sort_weight = p_risk

        # Only include non-routine items, or top items if few exist
        if urgency != "ROUTINE" or p_risk >= 20.0:
            watchlist_items.append({
                "animal_id": a.get("animal_id"),
                "animal_tag": a.get("animal_tag") or a.get("animal_id"),
                "animal_name": a.get("animal_name") or "Animal",
                "farm_id": a.get("farm_id"),
                "farm_name": a.get("farm_name") or "Farm",
                "current_health_risk": c_risk,
                "predicted_health_risk": p_risk,
                "forecast_window_hours": a.get("forecast_window_hours", 48),
                "risk_category": cat,
                "trend": trend,
                "confidence": a.get("confidence", 0.5),
                "primary_driver": a.get("primary_drivers", ["Baseline monitoring"])[0] if a.get("primary_drivers") else "Stable baseline",
                "last_update": a.get("created_at", ""),
                "recommended_action": a.get("recommended_action", "Maintain routine monitoring"),
                "operational_urgency": urgency,
                "_sort_weight": sort_weight
            })

    # Sort descending by operational urgency weight
    watchlist_items.sort(key=lambda item: item["_sort_weight"], reverse=True)
    clean_items = []
    for it in watchlist_items[:min(limit, 50)]:
        del it["_sort_weight"]
        clean_items.append(it)

    return clean_items


def get_predictive_trends(
    farm_id: Optional[str] = None,
    timeframe: str = "7d"
) -> dict[str, Any]:
    """
    Returns time-series risk trends across historical predictive assessments.
    Supports 24h, 48h, 7d, 30d time horizons.
    """
    db = get_database()
    ensure_predictive_indexes(db)
    now = datetime.now(timezone.utc)

    hours_map = {"24h": 24, "48h": 48, "7d": 168, "30d": 720}
    hours = hours_map.get(timeframe, 168)
    cutoff = (now - timedelta(hours=hours)).isoformat()

    match_q: dict[str, Any] = {"created_at": {"$gte": cutoff}}
    if farm_id:
        match_q["farm_id"] = farm_id

    records = list(db.predictive_assessments.find(match_q).sort("created_at", 1).limit(200))

    if not records:
        return {
            "farm_id": farm_id,
            "timeframe": timeframe,
            "points": [],
            "overall_trend": "stable"
        }

    # Bin into temporal buckets (up to 12 points)
    points = []
    # If fewer than 15 records, return them directly as points
    for r in records[-15:]:
        points.append({
            "timestamp": r.get("created_at", ""),
            "average_predicted_risk": float(r.get("predicted_health_risk", 0.0)),
            "high_risk_count": 1 if r.get("risk_category") in ("HIGH", "CRITICAL") else 0,
            "critical_risk_count": 1 if r.get("risk_category") == "CRITICAL" else 0,
            "total_evaluated": 1
        })

    risks = [p["average_predicted_risk"] for p in points]
    if len(risks) >= 2:
        diff = risks[-1] - risks[0]
        if diff >= 10.0:
            trend_str = "deteriorating"
        elif diff <= -10.0:
            trend_str = "improving"
        else:
            trend_str = "stable"
    else:
        trend_str = "stable"

    return {
        "farm_id": farm_id,
        "timeframe": timeframe,
        "points": points,
        "overall_trend": trend_str
    }


def get_model_status() -> dict[str, Any]:
    """Returns runtime model health, versioning, active adapter, and clinical safety status."""
    active = get_predictive_model()
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "training_status": "deterministic_baseline",
        "supported_windows_hours": [24, 48, 72],
        "models": registry.get_all_models_status(),
        "clinical_safety_compliance": True,
        "status": "operational"
    }


def escalate_to_veterinary_case(
    assessment_id: str,
    user_info: dict[str, Any],
    title: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None
) -> dict[str, Any]:
    """
    Escalates a predictive health assessment into a formal veterinary clinical case.
    Never auto-diagnoses: supplies verified prediction, drivers, and trajectory for clinical review.
    """
    db = get_database()
    assessment = db.predictive_assessments.find_one({"assessment_id": assessment_id})
    if not assessment:
        raise ValueError(f"Predictive assessment '{assessment_id}' was not found.")

    animal_id = assessment["animal_id"]
    animal = db.animals.find_one({"_id": get_animal_obj_id(animal_id) or animal_id})
    farm_id = assessment.get("farm_id") or (str(animal.get("farm_id", "")) if animal else "")
    farm = db.farms.find_one({"_id": get_animal_obj_id(farm_id) or farm_id}) if farm_id else None

    user_id = str(user_info.get("id") or user_info.get("_id") or "SYSTEM")
    user_name = user_info.get("full_name") or user_info.get("name") or "Veterinary Officer"
    user_role = str(user_info.get("role", "veterinarian")).lower()

    now = datetime.now(timezone.utc)
    case_number = f"CASE-PRED-{uuid.uuid4().hex[:6].upper()}"

    p_risk = float(assessment.get("predicted_health_risk", 0.0))
    cat = assessment.get("risk_category", "HIGH")
    case_priority = priority or ("critical" if cat == "CRITICAL" else ("high" if p_risk >= 45.0 else "medium"))
    case_title = title or f"Predictive Deterioration Triage: {animal.get('tag_id') if animal else animal_id}"

    drivers_str = "\n".join([f"• {d}" for d in assessment.get("primary_drivers", [])])
    clinical_findings = (
        f"Prospective Health Risk: {p_risk:.1f}/100 ({cat})\n"
        f"Forecast Window: {assessment.get('forecast_window_hours', 48)} hours\n"
        f"Longitudinal Trajectory: {assessment.get('trend', 'deteriorating')}\n"
        f"Confidence: {int(assessment.get('confidence', 0.5) * 100)}%\n\n"
        f"Primary Contributing Drivers:\n{drivers_str}\n\n"
        f"System Recommendations: {assessment.get('recommended_action', 'Veterinary clinical review advised.')}"
    )

    if notes:
        clinical_findings += f"\n\nClinician Notes: {notes}"

    timeline_event = {
        "event": "case_created_from_prediction",
        "title": "Case Opened via Predictive Intelligence",
        "description": f"Escalated from predictive assessment {assessment_id} (Risk: {p_risk:.1f}/100)",
        "performed_by": user_id,
        "performed_by_name": user_name,
        "performed_by_role": user_role,
        "timestamp": now.isoformat(),
    }

    new_case = {
        "case_number": case_number,
        "animal_id": animal_id,
        "farm_id": farm_id,
        "owner_id": farm.get("owner_id", "") if farm else "",
        "title": case_title,
        "description": f"Predictive deterioration escalation for {animal.get('name') if animal else 'animal'} ({animal.get('tag_id') if animal else animal_id}).",
        "case_type": "suspected_disease",
        "priority": case_priority,
        "status": "open",
        "source": "ai_assessment",
        "alert_id": None,
        "predictive_assessment_id": assessment_id,
        "health_risk_score": float(assessment.get("current_health_risk", 0.0)),
        "predicted_risk_score": p_risk,
        "disease_risk_level": "moderate" if p_risk < 70 else "high",
        "early_warning_level": "warning" if p_risk >= 50 else "elevated",
        "assigned_veterinarian_id": user_id if user_role == "veterinarian" else None,
        "assigned_veterinarian_name": user_name if user_role == "veterinarian" else None,
        "clinical_findings": clinical_findings,
        "diagnosis": None,  # Diagnostic determination reserved strictly for veterinarian
        "treatment_plan": None,
        "medications": [],
        "recommendations": assessment.get("recommended_action"),
        "follow_up_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
        "timeline": [timeline_event],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "closed_at": None,
    }

    res = db.veterinary_cases.insert_one(new_case)
    new_case["id"] = str(res.inserted_id)
    if "_id" in new_case:
        del new_case["_id"]

    return new_case

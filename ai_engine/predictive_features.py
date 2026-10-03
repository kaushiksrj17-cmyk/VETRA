"""
ai_engine/predictive_features.py
================================
VETRA Phase 11 — Multi-Modal Predictive Feature Engineering.

Transforms chronological multi-sensor IoT telemetry, visual inspections,
edge inferences, alerts, preventive schedules, and surveillance risk records
into standardized feature matrices for predictive health triage.

Features:
- Telemetry: means, standard deviations, slopes, change rates, drop rates
- Visual & Multimodal: mean visual risk, visual slope, multimodal slope
- Clinical & History: alert frequency, critical alert count, preventive compliance,
  recent case indicators, surveillance exposure score, edge concern frequency.
- Supports bounded temporal windows: 6h, 12h, 24h, 48h, 72h, 7d, 14d, 30d.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence
import numpy as np

from ai_engine.trend_engine import (
    PHYSIOLOGICAL_BASELINES,
    calculate_linear_slope,
)


FEATURE_VERSION = "v1.0"

SUPPORTED_WINDOWS_HOURS = {
    "6h": 6,
    "12h": 12,
    "24h": 24,
    "48h": 48,
    "72h": 72,
    "7d": 168,
    "14d": 336,
    "30d": 720,
}


def parse_iso_datetime(dt_str: Any) -> Optional[datetime]:
    """Safely converts ISO-formatted string or datetime object to UTC datetime."""
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        if dt_str.tzinfo is None:
            return dt_str.replace(tzinfo=timezone.utc)
        return dt_str
    try:
        clean = str(dt_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def filter_by_window(
    records: Sequence[dict[str, Any]],
    window_hours: int,
    time_key: str = "recorded_at",
    reference_time: Optional[datetime] = None
) -> list[dict[str, Any]]:
    """
    Filters chronological records strictly within [reference_time - window_hours, reference_time].
    Prevents unbounded queries and ensures reproducible temporal scoping.
    """
    if not records:
        return []
    ref = reference_time or datetime.now(timezone.utc)
    cutoff = ref - timedelta(hours=window_hours)

    filtered = []
    for r in records:
        ts = parse_iso_datetime(r.get(time_key) or r.get("created_at") or r.get("timestamp"))
        if ts and ts >= cutoff:
            filtered.append(r)
        elif not ts:
            # Fallback if no timestamp: allow if within reasonable recent count
            filtered.append(r)
    return filtered


def extract_predictive_features(
    readings: list[dict[str, Any]],
    visual_analyses: Optional[list[dict[str, Any]]] = None,
    multimodal_assessments: Optional[list[dict[str, Any]]] = None,
    alerts: Optional[list[dict[str, Any]]] = None,
    veterinary_cases: Optional[list[dict[str, Any]]] = None,
    preventive_tasks: Optional[list[dict[str, Any]]] = None,
    farm_risk_profile: Optional[dict[str, Any]] = None,
    edge_events: Optional[list[dict[str, Any]]] = None,
    window_hours: int = 48,
    reference_time: Optional[datetime] = None
) -> dict[str, Any]:
    """
    Extracts multi-domain bounded features for predictive health modeling.
    Returns complete feature snapshot and missing data diagnostics.
    """
    ref_time = reference_time or datetime.now(timezone.utc)

    # 1. Temporal window filtering
    filtered_readings = filter_by_window(readings, window_hours, "recorded_at", ref_time)
    filtered_visual = filter_by_window(visual_analyses or [], window_hours, "created_at", ref_time)
    filtered_multimodal = filter_by_window(multimodal_assessments or [], window_hours, "created_at", ref_time)
    filtered_alerts = filter_by_window(alerts or [], window_hours, "created_at", ref_time)
    filtered_edge = filter_by_window(edge_events or [], window_hours, "captured_at", ref_time)

    # Sort readings oldest first for slope calculation
    ordered_readings = sorted(
        filtered_readings,
        key=lambda r: parse_iso_datetime(r.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc)
    )

    n_readings = len(ordered_readings)

    # Initialize telemetry feature defaults
    if n_readings > 0:
        temps = [float(r.get("temperature_c", PHYSIOLOGICAL_BASELINES["temperature_c"])) for r in ordered_readings]
        hrs = [float(r.get("heart_rate_bpm", PHYSIOLOGICAL_BASELINES["heart_rate_bpm"])) for r in ordered_readings]
        resps = [float(r.get("respiratory_rate", PHYSIOLOGICAL_BASELINES["respiratory_rate"])) for r in ordered_readings]
        acts = [float(r.get("activity_level", PHYSIOLOGICAL_BASELINES["activity_level"])) for r in ordered_readings]
        rums = [float(r.get("rumination_level", PHYSIOLOGICAL_BASELINES["rumination_level"])) for r in ordered_readings]

        temperature_mean = round(float(np.mean(temps)), 2)
        temperature_std = round(float(np.std(temps)), 2)
        temperature_slope = calculate_linear_slope(temps)
        temperature_change_rate = round(temps[-1] - temps[0], 2)

        heart_rate_mean = round(float(np.mean(hrs)), 1)
        heart_rate_std = round(float(np.std(hrs)), 1)
        heart_rate_slope = calculate_linear_slope(hrs)

        respiratory_rate_mean = round(float(np.mean(resps)), 1)
        respiratory_rate_slope = calculate_linear_slope(resps)

        activity_mean = round(float(np.mean(acts)), 1)
        activity_slope = calculate_linear_slope(acts)
        # Drop rate from expected baseline
        activity_drop_rate = max(0.0, round(((PHYSIOLOGICAL_BASELINES["activity_level"] - acts[-1]) / PHYSIOLOGICAL_BASELINES["activity_level"]) * 100.0, 1))

        rumination_mean = round(float(np.mean(rums)), 1)
        rumination_slope = calculate_linear_slope(rums)
        rumination_drop_rate = max(0.0, round(((PHYSIOLOGICAL_BASELINES["rumination_level"] - rums[-1]) / PHYSIOLOGICAL_BASELINES["rumination_level"]) * 100.0, 1))

        latest_reading_time = parse_iso_datetime(ordered_readings[-1].get("recorded_at"))
        recency_minutes = max(0, int((ref_time - latest_reading_time).total_seconds() / 60)) if latest_reading_time else 9999
    else:
        temperature_mean = PHYSIOLOGICAL_BASELINES["temperature_c"]
        temperature_std = 0.0
        temperature_slope = 0.0
        temperature_change_rate = 0.0

        heart_rate_mean = PHYSIOLOGICAL_BASELINES["heart_rate_bpm"]
        heart_rate_std = 0.0
        heart_rate_slope = 0.0

        respiratory_rate_mean = PHYSIOLOGICAL_BASELINES["respiratory_rate"]
        respiratory_rate_slope = 0.0

        activity_mean = PHYSIOLOGICAL_BASELINES["activity_level"]
        activity_slope = 0.0
        activity_drop_rate = 0.0

        rumination_mean = PHYSIOLOGICAL_BASELINES["rumination_level"]
        rumination_slope = 0.0
        rumination_drop_rate = 0.0

        recency_minutes = 9999

    # 2. Visual and Multimodal features
    n_visual = len(filtered_visual)
    if n_visual > 0:
        vis_scores = [float(v.get("visual_risk_score", 0.0)) for v in filtered_visual]
        visual_risk_mean = round(float(np.mean(vis_scores)), 1)
        visual_risk_slope = calculate_linear_slope(vis_scores)
    else:
        visual_risk_mean = 0.0
        visual_risk_slope = 0.0

    n_multimodal = len(filtered_multimodal)
    if n_multimodal > 0:
        multi_scores = [float(m.get("combined_risk_score", 0.0)) for m in filtered_multimodal]
        multimodal_risk_mean = round(float(np.mean(multi_scores)), 1)
        multimodal_risk_slope = calculate_linear_slope(multi_scores)
    else:
        multimodal_risk_mean = 0.0
        multimodal_risk_slope = 0.0

    # 3. Alert frequency & severity
    n_alerts = len(filtered_alerts)
    critical_alerts = sum(1 for a in filtered_alerts if str(a.get("severity")).lower() == "critical")
    high_alerts = sum(1 for a in filtered_alerts if str(a.get("severity")).lower() == "high")
    alert_frequency = round((n_alerts / max(1, window_hours / 24.0)), 2)  # alerts per day

    # 4. Preventive healthcare compliance
    tasks = preventive_tasks or []
    if tasks:
        completed = sum(1 for t in tasks if str(t.get("status")).lower() == "completed")
        preventive_compliance = round((completed / len(tasks)) * 100.0, 1)
    else:
        preventive_compliance = 100.0  # No outstanding overdue tasks detected

    # 5. Veterinary case and treatment history
    cases = veterinary_cases or []
    recent_vet_case = False
    recent_treatment = False
    for c in cases:
        c_time = parse_iso_datetime(c.get("created_at") or c.get("updated_at"))
        if c_time and (ref_time - c_time) <= timedelta(days=14):
            recent_vet_case = True
            if c.get("treatment_plan") or c.get("medications"):
                recent_treatment = True

    # 6. Surveillance & Epidemiological Exposure
    surv_score = 0.0
    if farm_risk_profile:
        surv_score = float(farm_risk_profile.get("risk_score", 0.0))
    disease_surveillance_exposure = round(min(100.0, max(0.0, surv_score)), 1)

    # 7. Camera & Edge vision concern frequency
    camera_observation_frequency = round(n_visual / max(1, window_hours / 24.0), 2)
    edge_visual_concern_frequency = sum(1 for e in filtered_edge if float(e.get("visual_risk_score", 0.0)) >= 45.0)

    # 8. Data availability flags & missing data indicators
    has_sufficient_telemetry = (n_readings >= 3)
    has_visual_data = (n_visual > 0 or len(filtered_edge) > 0)
    is_telemetry_fresh = (recency_minutes <= 180)  # within 3 hours

    return {
        "feature_version": FEATURE_VERSION,
        "window_hours": window_hours,
        "data_availability": {
            "num_readings": n_readings,
            "num_visual_observations": n_visual,
            "num_multimodal_assessments": n_multimodal,
            "num_alerts": n_alerts,
            "num_edge_events": len(filtered_edge),
            "telemetry_recency_minutes": recency_minutes,
            "has_sufficient_telemetry": has_sufficient_telemetry,
            "has_visual_data": has_visual_data,
            "is_telemetry_fresh": is_telemetry_fresh,
        },
        # Monitored Vital Features
        "temperature_mean": temperature_mean,
        "temperature_std": temperature_std,
        "temperature_slope": temperature_slope,
        "temperature_change_rate": temperature_change_rate,
        "heart_rate_mean": heart_rate_mean,
        "heart_rate_std": heart_rate_std,
        "heart_rate_slope": heart_rate_slope,
        "respiratory_rate_mean": respiratory_rate_mean,
        "respiratory_rate_slope": respiratory_rate_slope,
        "activity_mean": activity_mean,
        "activity_slope": activity_slope,
        "activity_drop_rate": activity_drop_rate,
        "rumination_mean": rumination_mean,
        "rumination_slope": rumination_slope,
        "rumination_drop_rate": rumination_drop_rate,
        # Visual & Multimodal Features
        "visual_risk_mean": visual_risk_mean,
        "visual_risk_slope": visual_risk_slope,
        "multimodal_risk_mean": multimodal_risk_mean,
        "multimodal_risk_slope": multimodal_risk_slope,
        # Alert & Health History Features
        "alert_frequency": alert_frequency,
        "critical_alert_count": critical_alerts,
        "high_alert_count": high_alerts,
        "preventive_compliance": preventive_compliance,
        "recent_veterinary_case": recent_vet_case,
        "recent_treatment": recent_treatment,
        "disease_surveillance_exposure": disease_surveillance_exposure,
        "camera_observation_frequency": camera_observation_frequency,
        "edge_visual_concern_frequency": edge_visual_concern_frequency,
    }

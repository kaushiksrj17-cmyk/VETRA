"""
ai_engine/trend_engine.py
=========================
VETRA Phase 11 — Multi-Metric Longitudinal Trend Analysis Engine.

Analyzes sequential physiological vitals, visual indicators, and multimodal scores
over bounded temporal windows to detect direction, velocity, and stability of health trajectories.

Classifications:
- stable: Parameter remains within normal physiological variance.
- improving: Deviations returning towards normal healthy reference baselines.
- deteriorating: Sustained progression away from healthy reference baselines.
- rapid_deterioration: High-velocity divergence exceeding critical rate-of-change thresholds.
- volatile: High variance with alternating signs lacking directional stability.
- insufficient_data: Fewer than the minimum required observations for trend evaluation.
"""

from typing import Any, Optional, Sequence
import numpy as np


# Standard bovine physiological references
PHYSIOLOGICAL_BASELINES = {
    "temperature_c": 38.6,
    "heart_rate_bpm": 70.0,
    "respiratory_rate": 22.0,
    "activity_level": 75.0,
    "rumination_level": 80.0,
    "visual_risk_score": 0.0,
    "multimodal_risk_score": 0.0,
}

# Healthy physiological bounds (min, max)
HEALTHY_RANGES = {
    "temperature_c": (38.0, 39.3),
    "heart_rate_bpm": (48.0, 88.0),
    "respiratory_rate": (15.0, 32.0),
    "activity_level": (45.0, 100.0),
    "rumination_level": (45.0, 100.0),
    "visual_risk_score": (0.0, 25.0),
    "multimodal_risk_score": (0.0, 25.0),
}


def calculate_linear_slope(values: Sequence[float]) -> float:
    """
    Computes ordinary least squares linear regression slope for sequential values.
    Returns 0.0 if fewer than 2 valid points.
    """
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    y = np.array(values, dtype=float)
    if np.all(y == y[0]):
        return 0.0
    n = len(x)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    if denominator == 0:
        return 0.0
    return float(round(numerator / denominator, 4))


def analyze_metric_trajectory(
    metric_name: str,
    values: list[float],
    timestamps: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Evaluates trajectory of a specific monitored parameter across time.
    Values are ordered from oldest (index 0) to newest (index -1).
    """
    if not values or len(values) < 3:
        return {
            "metric": metric_name,
            "status": "insufficient_data",
            "sample_size": len(values),
            "slope": 0.0,
            "change_percentage": 0.0,
            "baseline_deviation": 0.0,
            "mean": round(float(np.mean(values)), 2) if values else 0.0,
            "std": 0.0,
            "confidence": 0.2 if values else 0.0,
            "description": f"Insufficient data ({len(values)} points) to determine {metric_name} trend."
        }

    val_arr = np.array(values, dtype=float)
    n = len(val_arr)
    mean_val = float(np.mean(val_arr))
    std_val = float(np.std(val_arr))
    latest = val_arr[-1]
    oldest = val_arr[0]
    baseline = PHYSIOLOGICAL_BASELINES.get(metric_name, mean_val if mean_val != 0 else 1.0)
    normal_min, normal_max = HEALTHY_RANGES.get(metric_name, (0.0, 100.0))

    slope = calculate_linear_slope(values)
    baseline_dev = round(mean_val - baseline, 2)

    # Change percentage relative to baseline or initial reading
    ref_denom = baseline if baseline != 0 else (oldest if oldest != 0 else 1.0)
    change_pct = round(((latest - oldest) / abs(ref_denom)) * 100.0, 2)

    # Evaluation of directional health significance
    # For temperature, HR, resp, visual_risk: rising is generally worse
    # For activity, rumination: falling is generally worse
    is_inverse = metric_name in ("activity_level", "rumination_level")
    
    # Check volatility (coefficient of variation or alternating swings)
    diffs = np.diff(val_arr)
    sign_changes = np.sum(np.diff(np.sign(diffs[diffs != 0])) != 0) if len(diffs[diffs != 0]) > 1 else 0
    volatility_ratio = std_val / (abs(mean_val) + 1e-5)

    is_volatile = (sign_changes >= (n // 2)) and (volatility_ratio > 0.15)

    # Trend categorization
    if is_volatile:
        status = "volatile"
        desc = f"Volatile fluctuations observed in {metric_name} without stable directional momentum."
    elif is_inverse:
        # Lower is worse (e.g. activity, rumination)
        if slope < -2.0 or change_pct <= -30.0:
            status = "rapid_deterioration"
            desc = f"Rapid decline in {metric_name}: dropped {abs(change_pct):.1f}% below initial reading."
        elif slope < -0.5 or change_pct <= -15.0:
            status = "deteriorating"
            desc = f"Deteriorating trend: steady reduction in {metric_name} ({change_pct:+.1f}%)."
        elif slope > 0.8 and mean_val < normal_min:
            status = "improving"
            desc = f"Improving trend: {metric_name} recovering towards normal levels."
        else:
            status = "stable"
            desc = f"{metric_name} remains relatively stable within normal variance."
    else:
        # Higher is worse (e.g. temperature, respiratory rate, risk score)
        if metric_name == "temperature_c":
            if slope >= 0.15 or (latest - oldest >= 0.8):
                status = "rapid_deterioration"
                desc = f"Rapid thermal climb (+{latest - oldest:.2f}°C) over observation period."
            elif slope >= 0.05 or (latest - oldest >= 0.4):
                status = "deteriorating"
                desc = f"Rising temperature trajectory (+{latest - oldest:.2f}°C elevation)."
            elif slope <= -0.06 and mean_val > normal_max:
                status = "improving"
                desc = f"Temperature resolving back towards baseline (-{abs(latest - oldest):.2f}°C)."
            else:
                status = "stable"
                desc = "Temperature trajectory remains stable."
        elif metric_name in ("visual_risk_score", "multimodal_risk_score"):
            if slope >= 4.0 or change_pct >= 40.0:
                status = "rapid_deterioration"
                desc = f"Rapid climb in {metric_name} ({change_pct:+.1f}%)."
            elif slope >= 1.5 or change_pct >= 20.0:
                status = "deteriorating"
                desc = f"Upward trajectory in {metric_name}."
            elif slope <= -1.5:
                status = "improving"
                desc = f"Declining risk score for {metric_name}."
            else:
                status = "stable"
                desc = f"{metric_name} is stable."
        else:
            # HR, Respiratory rate
            if slope >= 1.8 or change_pct >= 25.0:
                status = "rapid_deterioration"
                desc = f"Sharp escalation in {metric_name} (+{change_pct:.1f}%)."
            elif slope >= 0.6 or change_pct >= 12.0:
                status = "deteriorating"
                desc = f"Upward climb in {metric_name} (+{change_pct:.1f}%)."
            elif slope <= -0.8 and mean_val > normal_max:
                status = "improving"
                desc = f"{metric_name} recovering towards standard baseline."
            else:
                status = "stable"
                desc = f"{metric_name} within stable baseline variance."

    # Confidence calculation based on sample count and variance
    base_conf = min(0.85, 0.40 + (min(n, 20) / 20.0) * 0.45)
    if is_volatile:
        base_conf = max(0.35, base_conf - 0.20)
    confidence = round(base_conf, 2)

    return {
        "metric": metric_name,
        "status": status,
        "sample_size": n,
        "slope": slope,
        "change_percentage": change_pct,
        "baseline_deviation": baseline_dev,
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        "confidence": confidence,
        "description": desc
    }


def compute_holistic_trend(
    readings: list[dict[str, Any]],
    visual_analyses: Optional[list[dict[str, Any]]] = None
) -> dict[str, Any]:
    """
    Computes multi-system composite trajectory across vital telemetry and visual observations.
    Never classifies health trend based on a solitary reading.
    """
    if not readings or len(readings) < 3:
        return {
            "overall_trend": "insufficient_data",
            "trend_strength": 0.0,
            "confidence": 0.20 if readings else 0.0,
            "metrics": {},
            "deterioration_count": 0,
            "improving_count": 0,
            "stable_count": 0,
            "volatile_count": 0,
            "primary_trend_driver": "Insufficient telemetry history (minimum 3 readings required).",
            "summary": "Telemetry record contains fewer than 3 samples. Longitudinal trend cannot be determined reliably."
        }

    # Sort readings oldest first
    ordered_readings = sorted(readings, key=lambda r: r.get("recorded_at") or "")

    temps = [float(r.get("temperature_c", PHYSIOLOGICAL_BASELINES["temperature_c"])) for r in ordered_readings]
    hrs = [float(r.get("heart_rate_bpm", PHYSIOLOGICAL_BASELINES["heart_rate_bpm"])) for r in ordered_readings]
    resps = [float(r.get("respiratory_rate", PHYSIOLOGICAL_BASELINES["respiratory_rate"])) for r in ordered_readings]
    acts = [float(r.get("activity_level", PHYSIOLOGICAL_BASELINES["activity_level"])) for r in ordered_readings]
    rums = [float(r.get("rumination_level", PHYSIOLOGICAL_BASELINES["rumination_level"])) for r in ordered_readings]

    metrics_res = {
        "temperature_c": analyze_metric_trajectory("temperature_c", temps),
        "heart_rate_bpm": analyze_metric_trajectory("heart_rate_bpm", hrs),
        "respiratory_rate": analyze_metric_trajectory("respiratory_rate", resps),
        "activity_level": analyze_metric_trajectory("activity_level", acts),
        "rumination_level": analyze_metric_trajectory("rumination_level", rums),
    }

    # Optional visual trajectory
    if visual_analyses and len(visual_analyses) >= 2:
        ordered_vis = sorted(visual_analyses, key=lambda v: v.get("created_at") or "")
        vis_scores = [float(v.get("visual_risk_score", 0.0)) for v in ordered_vis]
        metrics_res["visual_risk_score"] = analyze_metric_trajectory("visual_risk_score", vis_scores)

    statuses = [m["status"] for m in metrics_res.values()]
    rapid_count = statuses.count("rapid_deterioration")
    deteriorate_count = statuses.count("deteriorating") + rapid_count
    improve_count = statuses.count("improving")
    stable_count = statuses.count("stable")
    volatile_count = statuses.count("volatile")

    # Determine dominant overall trajectory
    # Multi-system deterioration prioritizes safety
    if rapid_count >= 1 or deteriorate_count >= 2:
        if rapid_count >= 2 or (rapid_count >= 1 and deteriorate_count >= 3):
            overall_trend = "rapid_deterioration"
            trend_strength = 0.90
        else:
            overall_trend = "deteriorating"
            trend_strength = 0.70
    elif improve_count >= 2 and deteriorate_count == 0:
        overall_trend = "improving"
        trend_strength = 0.65
    elif volatile_count >= 2:
        overall_trend = "volatile"
        trend_strength = 0.50
    else:
        overall_trend = "stable"
        trend_strength = 0.40

    # Pick primary trend driver
    drivers = []
    for m_name, m_res in metrics_res.items():
        if m_res["status"] in ("rapid_deterioration", "deteriorating"):
            drivers.append(m_res["description"])
    
    if not drivers:
        for m_name, m_res in metrics_res.items():
            if m_res["status"] == "improving":
                drivers.append(m_res["description"])

    primary_driver = drivers[0] if drivers else "All physiological vitals demonstrate baseline stability."

    # Average metric confidence
    avg_conf = float(np.mean([m["confidence"] for m in metrics_res.values()]))
    # Cap between 0.25 and 0.88
    final_conf = round(min(0.88, max(0.25, avg_conf)), 2)

    return {
        "overall_trend": overall_trend,
        "trend_strength": trend_strength,
        "confidence": final_conf,
        "metrics": metrics_res,
        "deterioration_count": deteriorate_count,
        "rapid_deterioration_count": rapid_count,
        "improving_count": improve_count,
        "stable_count": stable_count,
        "volatile_count": volatile_count,
        "primary_trend_driver": primary_driver,
        "summary": f"Trajectory evaluated as {overall_trend.upper().replace('_', ' ')} based on {len(ordered_readings)} chronological readings."
    }

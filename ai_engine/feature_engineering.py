from typing import Any
import numpy as np


# Standard bovine physiological references
BASELINE_TEMP_C = 38.6
BASELINE_HR_BPM = 70.0
BASELINE_RESP_RATE = 22.0
BASELINE_ACTIVITY = 75.0
BASELINE_RUMINATION = 80.0


def extract_health_features(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Extract temporal, statistical, and deviation features from recent livestock telemetry.
    Expects readings sorted with newest reading first.
    """
    if not readings:
        return {
            "num_readings": 0,
            "avg_temp": BASELINE_TEMP_C,
            "temp_deviation": 0.0,
            "temp_rate_of_change": 0.0,
            "avg_heart_rate": BASELINE_HR_BPM,
            "hr_deviation": 0.0,
            "avg_respiratory_rate": BASELINE_RESP_RATE,
            "resp_deviation": 0.0,
            "avg_activity": BASELINE_ACTIVITY,
            "activity_reduction_pct": 0.0,
            "avg_rumination": BASELINE_RUMINATION,
            "rumination_reduction_pct": 0.0,
            "abnormal_signal_count": 0,
            "vital_stability_score": 100.0,
            "recent_trend": "stable"
        }

    # Use up to 30 recent readings
    sample = readings[:30]
    temps = [float(r.get("temperature_c", BASELINE_TEMP_C)) for r in sample]
    hrs = [float(r.get("heart_rate_bpm", BASELINE_HR_BPM)) for r in sample]
    resps = [float(r.get("respiratory_rate", BASELINE_RESP_RATE)) for r in sample]
    activities = [float(r.get("activity_level", BASELINE_ACTIVITY)) for r in sample]
    ruminations = [float(r.get("rumination_level", BASELINE_RUMINATION)) for r in sample]

    avg_temp = float(np.mean(temps))
    avg_hr = float(np.mean(hrs))
    avg_resp = float(np.mean(resps))
    avg_act = float(np.mean(activities))
    avg_rum = float(np.mean(ruminations))

    # Calculate deviations against bovine baseline
    temp_deviation = round(avg_temp - BASELINE_TEMP_C, 2)
    hr_deviation = round(avg_hr - BASELINE_HR_BPM, 1)
    resp_deviation = round(avg_resp - BASELINE_RESP_RATE, 1)

    # Activity & rumination drops (percentage drop from expected baseline)
    act_drop = max(0.0, round(((BASELINE_ACTIVITY - avg_act) / BASELINE_ACTIVITY) * 100, 1))
    rum_drop = max(0.0, round(((BASELINE_RUMINATION - avg_rum) / BASELINE_RUMINATION) * 100, 1))

    # Rate of change (trend slope from oldest to newest in sample)
    temp_roc = 0.0
    if len(temps) >= 2:
        # sample[0] is newest, sample[-1] is oldest
        temp_roc = round(temps[0] - temps[-1], 2)

    # Count abnormal signals
    abnormal_count = 0
    if avg_temp >= 39.5 or avg_temp < 37.0:
        abnormal_count += 1
    if avg_temp >= 40.5:
        abnormal_count += 1
    if avg_hr >= 100 or avg_hr < 50:
        abnormal_count += 1
    if avg_resp >= 35 or avg_resp < 12:
        abnormal_count += 1
    if act_drop >= 40.0:
        abnormal_count += 1
    if rum_drop >= 40.0:
        abnormal_count += 1

    # Trend summary
    if temp_roc > 0.5 and act_drop > 20.0:
        trend = "deteriorating"
    elif temp_roc < -0.5 and act_drop < 15.0:
        trend = "recovering"
    else:
        trend = "stable"

    # Stability score based on variance
    temp_var = float(np.var(temps)) if len(temps) > 1 else 0.0
    stability = max(0.0, min(100.0, round(100.0 - (temp_var * 15.0) - (abnormal_count * 10.0), 1)))

    return {
        "num_readings": len(sample),
        "latest_temp": temps[0],
        "avg_temp": round(avg_temp, 2),
        "temp_deviation": temp_deviation,
        "temp_rate_of_change": temp_roc,
        "latest_heart_rate": hrs[0],
        "avg_heart_rate": round(avg_hr, 1),
        "hr_deviation": hr_deviation,
        "latest_respiratory_rate": resps[0],
        "avg_respiratory_rate": round(avg_resp, 1),
        "resp_deviation": resp_deviation,
        "latest_activity": activities[0],
        "avg_activity": round(avg_act, 1),
        "activity_reduction_pct": act_drop,
        "latest_rumination": ruminations[0],
        "avg_rumination": round(avg_rum, 1),
        "rumination_reduction_pct": rum_drop,
        "abnormal_signal_count": abnormal_count,
        "vital_stability_score": stability,
        "recent_trend": trend
    }

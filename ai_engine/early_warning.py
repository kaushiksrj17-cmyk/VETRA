from typing import Any


def detect_early_warning(
    readings: list[dict[str, Any]],
    current_risk_score: float,
    disease_risk_level: str,
) -> dict[str, Any]:
    """
    VETRA AI Early-Warning Detection Engine.

    Detects deterioration across consecutive physiological readings.
    This is an early-warning and decision-support layer, not a diagnosis.
    """

    if not readings:
        return {
            "early_warning_status": "INSUFFICIENT_DATA",
            "warning_level": "LOW",
            "warning_score": 0,
            "deterioration_detected": False,
            "warning_signals": [],
            "trend_summary": "Insufficient telemetry data for deterioration analysis.",
            "recommended_action": "Continue collecting health telemetry.",
            "engine_version": "VETRA-EarlyWarning-v1.0",
        }

    ordered = sorted(
        readings,
        key=lambda item: item.get("recorded_at") or ""
    )

    recent = ordered[-5:]

    def value(reading: dict[str, Any], key: str) -> float:
        try:
            return float(reading.get(key, 0))
        except (TypeError, ValueError):
            return 0.0

    warning_score = 0
    warning_signals: list[str] = []

    # ---------------------------------------------------------
    # 1. Temperature deterioration
    # ---------------------------------------------------------
    temperatures = [value(r, "temperature_c") for r in recent]

    if len(temperatures) >= 2:
        if temperatures[-1] - temperatures[0] >= 0.5:
            warning_score += 18
            warning_signals.append(
                "Temperature is showing a rising trajectory."
            )

        if temperatures[-1] >= 39.5:
            warning_score += 20
            warning_signals.append(
                "Current temperature is above the normal monitoring range."
            )

    # ---------------------------------------------------------
    # 2. Heart-rate deterioration
    # ---------------------------------------------------------
    heart_rates = [value(r, "heart_rate_bpm") for r in recent]

    if len(heart_rates) >= 2:
        if heart_rates[-1] - heart_rates[0] >= 12:
            warning_score += 15
            warning_signals.append(
                "Heart rate is increasing across recent readings."
            )

    # ---------------------------------------------------------
    # 3. Respiratory deterioration
    # ---------------------------------------------------------
    respiratory_rates = [
        value(r, "respiratory_rate")
        for r in recent
    ]

    if len(respiratory_rates) >= 2:
        if respiratory_rates[-1] - respiratory_rates[0] >= 5:
            warning_score += 15
            warning_signals.append(
                "Respiratory rate is increasing across recent readings."
            )

    # ---------------------------------------------------------
    # 4. Activity deterioration
    # ---------------------------------------------------------
    activities = [
        value(r, "activity_level")
        for r in recent
    ]

    if len(activities) >= 2:
        if activities[0] > 0:
            activity_drop = (
                (activities[0] - activities[-1])
                / activities[0]
            ) * 100

            if activity_drop >= 20:
                warning_score += 18
                warning_signals.append(
                    "Activity level has decreased significantly."
                )

    # ---------------------------------------------------------
    # 5. Rumination deterioration
    # ---------------------------------------------------------
    rumination = [
        value(r, "rumination_level")
        for r in recent
    ]

    if len(rumination) >= 2:
        if rumination[0] > 0:
            rumination_drop = (
                (rumination[0] - rumination[-1])
                / rumination[0]
            ) * 100

            if rumination_drop >= 20:
                warning_score += 18
                warning_signals.append(
                    "Rumination level has decreased significantly."
                )

    # ---------------------------------------------------------
    # 6. Multi-system deterioration
    # ---------------------------------------------------------
    if len(warning_signals) >= 3:
        warning_score += 15
        warning_signals.append(
            "Multiple physiological systems show simultaneous changes."
        )

    # ---------------------------------------------------------
    # 7. Rapid deterioration pattern
    # ---------------------------------------------------------
    if (
        temperatures
        and activities
        and rumination
        and len(recent) >= 3
    ):
        temperature_rising = (
            temperatures[-1] > temperatures[0]
        )

        activity_falling = (
            activities[-1] < activities[0]
        )

        rumination_falling = (
            rumination[-1] < rumination[0]
        )

        if (
            temperature_rising
            and activity_falling
            and rumination_falling
        ):
            warning_score += 20
            warning_signals.append(
                "Combined temperature rise with declining activity "
                "and rumination indicates a deterioration pattern."
            )

    warning_score = min(100, warning_score)

    # ---------------------------------------------------------
    # Combine physiological and disease intelligence
    # ---------------------------------------------------------
    effective_score = max(
        warning_score,
        float(current_risk_score or 0)
    )

    disease_level = str(
        disease_risk_level or "low"
    ).lower()

    if effective_score >= 75 or disease_level == "high":
        warning_level = "CRITICAL"
    elif effective_score >= 50 or disease_level == "moderate":
        warning_level = "HIGH"
    elif effective_score >= 25:
        warning_level = "MODERATE"
    else:
        warning_level = "LOW"

    deterioration_detected = (
        warning_level in {"MODERATE", "HIGH", "CRITICAL"}
    )

    # ---------------------------------------------------------
    # Action recommendation
    # ---------------------------------------------------------
    if warning_level == "CRITICAL":
        recommended_action = (
            "Immediate veterinary review recommended. "
            "Increase monitoring frequency and evaluate the animal "
            "for clinical deterioration."
        )
    elif warning_level == "HIGH":
        recommended_action = (
            "Veterinary review should be considered promptly. "
            "Continue close telemetry monitoring."
        )
    elif warning_level == "MODERATE":
        recommended_action = (
            "Increase monitoring frequency and review recent "
            "feeding, activity, rumination, and environmental conditions."
        )
    else:
        recommended_action = (
            "Continue routine telemetry monitoring and preventive care."
        )

    if warning_signals:
        trend_summary = (
            f"{len(warning_signals)} early-warning signal(s) "
            "identified from recent telemetry."
        )
    else:
        trend_summary = (
            "No significant deterioration pattern detected "
            "in recent telemetry."
        )

    return {
        "early_warning_status": (
            "WARNING_DETECTED"
            if deterioration_detected
            else "NO_WARNING"
        ),
        "warning_level": warning_level,
        "warning_score": round(effective_score, 2),
        "deterioration_detected": deterioration_detected,
        "warning_signals": warning_signals,
        "trend_summary": trend_summary,
        "recommended_action": recommended_action,
        "analyzed_readings": len(recent),
        "engine_version": "VETRA-EarlyWarning-v1.0",
    }

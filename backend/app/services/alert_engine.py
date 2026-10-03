from typing import Any


def evaluate_health_risk(
    temperature_c: float,
    heart_rate_bpm: float,
    activity_level: float,
    rumination_level: float,
    respiratory_rate: float
) -> dict[str, Any]:

    triggered_rules = []

    # -------------------------------------------------
    # Temperature
    # -------------------------------------------------

    if temperature_c >= 40.5:

        triggered_rules.append({
            "type": "high_temperature",
            "severity": "critical",
            "message": (
                f"Body temperature is critically high "
                f"at {temperature_c:.1f} °C."
            )
        })

    elif temperature_c >= 39.5:

        triggered_rules.append({
            "type": "high_temperature",
            "severity": "high",
            "message": (
                f"Body temperature is elevated "
                f"at {temperature_c:.1f} °C."
            )
        })

    elif temperature_c < 37.0:

        triggered_rules.append({
            "type": "low_temperature",
            "severity": "high",
            "message": (
                f"Body temperature is unusually low "
                f"at {temperature_c:.1f} °C."
            )
        })

    # -------------------------------------------------
    # Heart rate
    # -------------------------------------------------

    if heart_rate_bpm >= 120:

        triggered_rules.append({
            "type": "high_heart_rate",
            "severity": "high",
            "message": (
                f"Heart rate is unusually high "
                f"at {heart_rate_bpm:.1f} BPM."
            )
        })

    elif heart_rate_bpm < 45:

        triggered_rules.append({
            "type": "low_heart_rate",
            "severity": "high",
            "message": (
                f"Heart rate is unusually low "
                f"at {heart_rate_bpm:.1f} BPM."
            )
        })

    # -------------------------------------------------
    # Respiratory rate
    # -------------------------------------------------

    if respiratory_rate >= 45:

        triggered_rules.append({
            "type": "high_respiratory_rate",
            "severity": "high",
            "message": (
                f"Respiratory rate is elevated "
                f"at {respiratory_rate:.1f} /min."
            )
        })

    elif respiratory_rate < 10:

        triggered_rules.append({
            "type": "low_respiratory_rate",
            "severity": "high",
            "message": (
                f"Respiratory rate is unusually low "
                f"at {respiratory_rate:.1f} /min."
            )
        })

    # -------------------------------------------------
    # Activity
    # -------------------------------------------------

    if activity_level < 25:

        triggered_rules.append({
            "type": "low_activity",
            "severity": "medium",
            "message": (
                f"Activity level is low "
                f"at {activity_level:.1f}%."
            )
        })

    # -------------------------------------------------
    # Rumination
    # -------------------------------------------------

    if rumination_level < 30:

        triggered_rules.append({
            "type": "low_rumination",
            "severity": "medium",
            "message": (
                f"Rumination level is low "
                f"at {rumination_level:.1f}%."
            )
        })

    # -------------------------------------------------
    # No abnormal signs
    # -------------------------------------------------

    if not triggered_rules:

        return {
            "has_alert": False,
            "severity": None,
            "alert_type": None,
            "title": "Normal Health Reading",
            "message": "No abnormal health indicators detected.",
            "triggered_by": []
        }

    # -------------------------------------------------
    # Determine overall severity
    # -------------------------------------------------

    severity_priority = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4
    }

    highest_severity = max(
        triggered_rules,
        key=lambda rule:
        severity_priority[rule["severity"]]
    )["severity"]

    # -------------------------------------------------
    # Multiple abnormal indicators
    # -------------------------------------------------

    if len(triggered_rules) >= 2:

        alert_type = "multiple_abnormal_signs"

        title = "Multiple Health Abnormalities Detected"

        message = (
            f"{len(triggered_rules)} abnormal "
            "health indicators detected."
        )

    else:

        alert_type = triggered_rules[0]["type"]

        title = (
            triggered_rules[0]["type"]
            .replace("_", " ")
            .title()
            + " Detected"
        )

        message = triggered_rules[0]["message"]

    return {
        "has_alert": True,
        "severity": highest_severity,
        "alert_type": alert_type,
        "title": title,
        "message": message,
        "triggered_by": [
            rule["type"]
            for rule in triggered_rules
        ]
    }
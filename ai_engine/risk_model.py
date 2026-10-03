from typing import Any
import numpy as np


class LivestockRiskModel:
    """
    Explainable physiological risk scoring model for livestock early health triage.
    Combines weighted feature sensitivities with clinical risk tiers.
    """

    def __init__(self):
        # Calibrated physiological risk weights
        self.weights = {
            "temp_elevation": 28.0,       # Hyperthermia / pyrexia
            "temp_depression": 22.0,      # Hypothermia
            "tachycardia": 18.0,          # Elevated heart rate
            "bradycardia": 15.0,          # Low heart rate
            "tachypnea": 16.0,            # High respiratory rate
            "rumination_drop": 20.0,      # Rumination reduction (key digestive/metabolic signal)
            "activity_drop": 14.0,        # Lethargy / reduced mobility
            "trend_acceleration": 12.0    # Rapid temperature change
        }

    def predict_risk(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Compute continuous health risk score (0-100) and contributing factors.
        """
        temp_dev = features.get("temp_deviation", 0.0)
        hr_dev = features.get("hr_deviation", 0.0)
        resp_dev = features.get("resp_deviation", 0.0)
        act_drop = features.get("activity_reduction_pct", 0.0)
        rum_drop = features.get("rumination_reduction_pct", 0.0)
        temp_roc = features.get("temp_rate_of_change", 0.0)

        raw_score = 0.0
        contributing_factors = []

        # 1. Temperature evaluation
        if temp_dev >= 1.9:  # >= 40.5 °C
            raw_score += self.weights["temp_elevation"] * 1.5
            contributing_factors.append(f"Severe pyrexia: body temperature is {temp_dev:+.2f} °C above baseline.")
        elif temp_dev >= 0.9:  # >= 39.5 °C
            raw_score += self.weights["temp_elevation"] * 1.0
            contributing_factors.append(f"Elevated body temperature: {temp_dev:+.2f} °C above baseline.")
        elif temp_dev <= -1.6:  # < 37.0 °C
            raw_score += self.weights["temp_depression"] * 1.2
            contributing_factors.append(f"Subnormal body temperature (hypothermia): {temp_dev:+.2f} °C below baseline.")

        # 2. Heart rate evaluation
        if hr_dev >= 30.0:  # >= 100 BPM
            raw_score += self.weights["tachycardia"] * 1.2
            contributing_factors.append(f"Tachycardia detected: heart rate is elevated by {hr_dev:+.1f} BPM.")
        elif hr_dev <= -25.0:  # < 45 BPM
            raw_score += self.weights["bradycardia"] * 1.1
            contributing_factors.append(f"Bradycardia detected: heart rate is unusually low ({hr_dev:+.1f} BPM).")

        # 3. Respiration evaluation
        if resp_dev >= 15.0:  # >= 37 /min
            raw_score += self.weights["tachypnea"] * 1.1
            contributing_factors.append(f"Tachypnea / elevated respiration: {resp_dev:+.1f} /min above baseline.")

        # 4. Rumination evaluation
        if rum_drop >= 50.0:
            raw_score += self.weights["rumination_drop"] * 1.3
            contributing_factors.append(f"Severe rumination depression: -{rum_drop:.1f}% below normal digestion cycle.")
        elif rum_drop >= 30.0:
            raw_score += self.weights["rumination_drop"] * 0.9
            contributing_factors.append(f"Moderate rumination decline: -{rum_drop:.1f}% reduction observed.")

        # 5. Activity evaluation
        if act_drop >= 50.0:
            raw_score += self.weights["activity_drop"] * 1.2
            contributing_factors.append(f"Pronounced lethargy: physical activity decreased by -{act_drop:.1f}%.")
        elif act_drop >= 30.0:
            raw_score += self.weights["activity_drop"] * 0.8
            contributing_factors.append(f"Reduced mobility: physical activity decreased by -{act_drop:.1f}%.")

        # 6. Trend acceleration
        if temp_roc > 0.6:
            raw_score += self.weights["trend_acceleration"]
            contributing_factors.append(f"Rapid thermal escalation: +{temp_roc:.2f} °C climb across recent readings.")

        # Calibrate final risk score 0 to 100
        risk_score = min(100.0, max(5.0 if contributing_factors else 0.0, round(raw_score, 1)))

        # Categorize risk tier
        if risk_score >= 75.0:
            category = "critical"
        elif risk_score >= 50.0:
            category = "high"
        elif risk_score >= 25.0:
            category = "medium"
        else:
            category = "low"

        if not contributing_factors:
            contributing_factors.append("All monitored physiological indicators are currently within standard reference ranges.")

        return {
            "health_risk_score": risk_score,
            "risk_category": category,
            "contributing_factors": contributing_factors,
            "model_version": "VETRA-ML-RiskModel-v1.0"
        }


# Global model instance
model = LivestockRiskModel()


def calculate_risk_score(features: dict[str, Any]) -> dict[str, Any]:
    """
    Convenience wrapper to compute ML risk score from extracted features.
    """
    return model.predict_risk(features)

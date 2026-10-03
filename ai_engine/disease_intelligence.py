from typing import Any


def assess_disease_risk(features: dict[str, Any]) -> dict[str, Any]:
    """
    VETRA Disease Intelligence Layer.

    Identifies physiological patterns associated with elevated
    disease/health risk. This is a screening and decision-support
    layer, not a definitive veterinary diagnosis.
    """

    temp_dev = float(features.get("temp_deviation", 0.0))
    hr_dev = float(features.get("hr_deviation", 0.0))
    resp_dev = float(features.get("resp_deviation", 0.0))
    activity_drop = float(features.get("activity_reduction_pct", 0.0))
    rumination_drop = float(features.get("rumination_reduction_pct", 0.0))
    temp_roc = float(features.get("temp_rate_of_change", 0.0))

    indicators = []
    risk_patterns = []
    recommendations = []

    # ---------------------------------------------------------
    # 1. Fever / inflammatory pattern
    # ---------------------------------------------------------
    fever_score = 0

    if temp_dev >= 1.9:
        fever_score += 3
    elif temp_dev >= 0.9:
        fever_score += 2
    elif temp_dev >= 0.5:
        fever_score += 1

    if temp_roc > 0.6:
        fever_score += 1

    if fever_score >= 3:
        risk_patterns.append("Elevated fever/inflammatory pattern")
        indicators.append(
            "Body temperature is substantially above the established physiological baseline."
        )
        recommendations.append(
            "Review temperature trend and consider veterinary examination if elevation persists."
        )
    elif fever_score >= 1:
        indicators.append(
            "Temperature shows a mild elevation or upward trend."
        )

    # ---------------------------------------------------------
    # 2. Respiratory-risk pattern
    # ---------------------------------------------------------
    respiratory_score = 0

    if resp_dev >= 15:
        respiratory_score += 3
    elif resp_dev >= 8:
        respiratory_score += 2
    elif resp_dev >= 4:
        respiratory_score += 1

    if respiratory_score >= 3:
        risk_patterns.append("Respiratory stress pattern")
        indicators.append(
            "Respiratory rate is substantially above the reference baseline."
        )
        recommendations.append(
            "Monitor breathing pattern and assess for respiratory distress or environmental stress."
        )
    elif respiratory_score >= 1:
        indicators.append(
            "Respiratory rate shows a mild elevation."
        )

    # ---------------------------------------------------------
    # 3. Digestive / metabolic pattern
    # ---------------------------------------------------------
    digestive_score = 0

    if rumination_drop >= 50:
        digestive_score += 3
    elif rumination_drop >= 30:
        digestive_score += 2
    elif rumination_drop >= 15:
        digestive_score += 1

    if activity_drop >= 30:
        digestive_score += 1

    if digestive_score >= 3:
        risk_patterns.append("Digestive/metabolic disturbance pattern")
        indicators.append(
            "Rumination has decreased substantially relative to the expected activity pattern."
        )
        recommendations.append(
            "Review feed intake, rumination trend, hydration and digestive status."
        )
    elif digestive_score >= 1:
        indicators.append(
            "Rumination or activity shows a downward trend."
        )

    # ---------------------------------------------------------
    # 4. Systemic health pattern
    # ---------------------------------------------------------
    systemic_signals = 0

    if temp_dev >= 0.9:
        systemic_signals += 1

    if hr_dev >= 20:
        systemic_signals += 1

    if resp_dev >= 8:
        systemic_signals += 1

    if activity_drop >= 30:
        systemic_signals += 1

    if rumination_drop >= 30:
        systemic_signals += 1

    if systemic_signals >= 3:
        risk_patterns.append("Multi-system physiological disturbance")
        indicators.append(
            "Multiple physiological indicators are deviating from baseline simultaneously."
        )
        recommendations.append(
            "Increase monitoring frequency and consider veterinary assessment."
        )

    # ---------------------------------------------------------
    # 5. Rapid deterioration pattern
    # ---------------------------------------------------------
    if temp_roc > 0.6 and (
        activity_drop >= 30 or rumination_drop >= 30
    ):
        risk_patterns.append("Rapid deterioration pattern")
        indicators.append(
            "Temperature is rising while activity or rumination is declining."
        )
        recommendations.append(
            "Prioritize repeat measurements and veterinary review if the pattern continues."
        )

    # ---------------------------------------------------------
    # Final classification
    # ---------------------------------------------------------
    pattern_count = len(risk_patterns)

    if pattern_count >= 3:
        disease_risk_level = "high"
    elif pattern_count >= 1:
        disease_risk_level = "moderate"
    else:
        disease_risk_level = "low"

    if not indicators:
        indicators.append(
            "No significant disease-associated physiological pattern detected."
        )

    if not recommendations:
        recommendations.append(
            "Continue routine telemetry monitoring and preventive healthcare."
        )

    return {
        "disease_risk_level": disease_risk_level,
        "risk_patterns": risk_patterns,
        "physiological_indicators": indicators,
        "recommendations": recommendations,
        "screening_note": (
            "Disease intelligence provides early-warning patterns for "
            "decision support and does not constitute a definitive diagnosis."
        ),
        "engine_version": "VETRA-DiseaseIntelligence-v1.0",
    }


def generate_surveillance_explanation(
    farm_profile: dict[str, Any],
    clusters: list[dict[str, Any]] = None,
    observations: list[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Generate structured clinical narrative and decision support
    for herd-level and farm-level disease surveillance.

    Maintains 100% deterministic availability without external API dependencies.
    """
    clusters = clusters or []
    observations = observations or []

    farm_name = farm_profile.get("farm_name", "Holding")
    risk_score = farm_profile.get("risk_score", 0.0)
    risk_category = farm_profile.get("risk_category", "LOW")
    affected_count = farm_profile.get("affected_animals_count", 0)
    total_animals = farm_profile.get("total_animals", 0)
    dominant_pattern = farm_profile.get("dominant_disease_pattern", "Baseline")
    contributing = farm_profile.get("contributing_factors", [])

    if risk_category in ["CRITICAL", "HIGH"]:
        pattern_explanation = (
            f"Elevated surveillance indicators detected on {farm_name}. "
            f"Approximately {affected_count}/{total_animals} animals show concurrent physiological deviations "
            f"consistent with {dominant_pattern}. Immediate epidemiological isolation and veterinary examination recommended."
        )
        risk_interpretation = (
            f"Holding is classified as {risk_category} risk ({risk_score:.1f}/100). "
            f"The primary driver is synchronized physiological telemetry anomalies accompanied by active health alerts."
        )
        next_steps = [
            "Conduct physical clinical exams and verify core body temperatures manually.",
            "Inspect herd drinking troughs and feed rations for contamination.",
            "Quarantine symptomatic animals into isolated pens.",
            "Record diagnostic swabs or blood samples if respiratory or febrile symptoms persist."
        ]
        vet_questions = [
            "Are multiple animals demonstrating nasal discharge, coughing, or thoracic wheezing?",
            "Has there been recent introduction of new animals or equipment from outside herds?",
            "Is there localized herd lethargy or sudden drop in milk yield or water consumption?"
        ]
    elif risk_category == "MODERATE":
        pattern_explanation = (
            f"Mild to moderate physiological variance observed across herd on {farm_name}. "
            f"Current signals suggest sub-clinical stress or early syndromic anomaly centered around {dominant_pattern}."
        )
        risk_interpretation = (
            f"Holding is classified as MODERATE risk ({risk_score:.1f}/100). "
            f"Parameters remain near acceptable boundaries but warrant increased monitoring frequency."
        )
        next_steps = [
            "Increase vital telemetry sampling frequency on flagged animals.",
            "Verify barn ventilation, ambient temperature index, and water availability.",
            "Review preventive vaccination and deworming compliance schedules."
        ]
        vet_questions = [
            "Are feed rations or grazing pastures consistent with historical baseline?",
            "Has the farm experienced recent environmental or thermal heat stress?"
        ]
    else:
        pattern_explanation = (
            f"All monitored livestock on {farm_name} demonstrate vital physiological parameters "
            f"and activity metrics within expected bovine baselines."
        )
        risk_interpretation = (
            f"Holding is classified as LOW risk ({risk_score:.1f}/100). "
            f"No syndromic clustering or epidemiological escalation detected."
        )
        next_steps = [
            "Maintain routine telemetry monitoring and automated alert tracking.",
            "Continue standard herd preventive health management protocols."
        ]
        vet_questions = [
            "Continue standard herd management protocols."
        ]

    cluster_explanation = (
        f"{len(clusters)} potential statistical clusters identified in the surveillance window. "
        "All clusters represent mathematical signal aggregations and require authorized veterinary confirmation before declaring an outbreak."
        if clusters else
        "No statistical disease clusters detected across monitored holdings."
    )

    return {
        "pattern_explanation": pattern_explanation,
        "cluster_explanation": cluster_explanation,
        "risk_interpretation": risk_interpretation,
        "surveillance_recommendations": next_steps,
        "veterinary_questions": vet_questions,
        "next_investigation_steps": next_steps,
        "dominant_disease_pattern": dominant_pattern,
        "clinical_safety_notice": (
            "Decision Support Only: VETRA Surveillance flags statistical anomalies. "
            "Definitive outbreak confirmation requires authorized veterinary investigation."
        )
    }


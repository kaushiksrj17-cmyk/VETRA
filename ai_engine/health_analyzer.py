from typing import Any

from ai_engine.feature_engineering import extract_health_features
from ai_engine.gemini_service import get_ai_clinical_explanation
from ai_engine.risk_model import calculate_risk_score
from ai_engine.disease_intelligence import assess_disease_risk
from ai_engine.early_warning import detect_early_warning


def analyze_animal_health(
    animal_data: dict[str, Any],
    readings: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    End-to-end VETRA AI clinical assessment pipeline.

    1. Feature Engineering
    2. Physiological Risk Scoring
    3. Disease Intelligence Screening
    4. Early-Warning Detection
    5. Gemini / Deterministic Clinical Interpretation
    6. Unified AI Health Report
    """

    features = extract_health_features(readings)

    risk_assessment = calculate_risk_score(features)

    disease_assessment = assess_disease_risk(features)

    early_warning = detect_early_warning(
        readings=readings,
        current_risk_score=risk_assessment["health_risk_score"],
        disease_risk_level=disease_assessment["disease_risk_level"],
    )

    ai_explanation = get_ai_clinical_explanation(
        animal_data,
        features,
        risk_assessment
    )

    return {
        "animal_id": animal_data.get("id"),
        "tag_id": animal_data.get("tag_id"),
        "animal_name": animal_data.get("name"),

        "current_health_status": animal_data.get(
            "health_status",
            "healthy"
        ),

        # Physiological Risk Intelligence
        "risk_score": risk_assessment["health_risk_score"],
        "risk_category": risk_assessment["risk_category"],
        "contributing_factors": risk_assessment["contributing_factors"],

        # Feature Engineering
        "trend_summary": features["recent_trend"],
        "vital_stability_score": features["vital_stability_score"],
        "features": features,

        # Disease Intelligence
        "disease_risk_level": disease_assessment[
            "disease_risk_level"
        ],
        "risk_patterns": disease_assessment[
            "risk_patterns"
        ],
        "physiological_indicators": disease_assessment[
            "physiological_indicators"
        ],
        "disease_recommendations": disease_assessment[
            "recommendations"
        ],
        "disease_screening_note": disease_assessment[
            "screening_note"
        ],
        "disease_engine_version": disease_assessment[
            "engine_version"
        ],

        # Early-Warning Intelligence
        "early_warning_status": early_warning[
            "early_warning_status"
        ],
        "early_warning_level": early_warning[
            "warning_level"
        ],
        "early_warning_score": early_warning[
            "warning_score"
        ],
        "deterioration_detected": early_warning[
            "deterioration_detected"
        ],
        "early_warning_signals": early_warning[
            "warning_signals"
        ],
        "early_warning_trend": early_warning[
            "trend_summary"
        ],
        "early_warning_action": early_warning[
            "recommended_action"
        ],
        "early_warning_readings_analyzed": early_warning[
            "analyzed_readings"
        ],
        "early_warning_engine_version": early_warning[
            "engine_version"
        ],

        # Clinical Interpretation
        "ai_explanation": ai_explanation[
            "explanation"
        ],
        "clinical_interpretation": ai_explanation[
            "clinical_interpretation"
        ],
        "recommended_action": ai_explanation[
            "recommended_action"
        ],
        "monitoring_recommendation": ai_explanation[
            "monitoring_recommendation"
        ],
        "questions_for_veterinarian": ai_explanation[
            "questions_for_veterinarian"
        ],

        "analysis_engine": ai_explanation.get(
            "source",
            "VETRA-AI-Core"
        )
    }

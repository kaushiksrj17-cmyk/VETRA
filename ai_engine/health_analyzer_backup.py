from typing import Any

from ai_engine.feature_engineering import extract_health_features
from ai_engine.gemini_service import get_ai_clinical_explanation
from ai_engine.risk_model import calculate_risk_score
from ai_engine.disease_intelligence import assess_disease_risk


def analyze_animal_health(
    animal_data: dict[str, Any],
    readings: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    End-to-end VETRA AI clinical assessment pipeline.

    1. Feature Engineering
    2. Physiological Risk Scoring
    3. Disease Intelligence Screening
    4. Gemini / Deterministic Clinical Interpretation
    5. Unified AI Health Report
    """

    # 1. Extract statistical health features
    features = extract_health_features(readings)

    # 2. Compute existing physiological risk score
    risk_assessment = calculate_risk_score(features)

    # 3. Run disease-pattern intelligence
    disease_assessment = assess_disease_risk(features)

    # 4. Generate clinical explanation via Gemini / fallback
    ai_explanation = get_ai_clinical_explanation(
        animal_data,
        features,
        risk_assessment
    )

    # 5. Return unified VETRA AI Health Report
    return {
        "animal_id": animal_data.get("id"),
        "tag_id": animal_data.get("tag_id"),
        "animal_name": animal_data.get("name"),
        "current_health_status": animal_data.get(
            "health_status",
            "healthy"
        ),

        # Existing physiological risk intelligence
        "risk_score": risk_assessment["health_risk_score"],
        "risk_category": risk_assessment["risk_category"],
        "contributing_factors": risk_assessment[
            "contributing_factors"
        ],

        # Existing feature intelligence
        "trend_summary": features["recent_trend"],
        "vital_stability_score": features[
            "vital_stability_score"
        ],
        "features": features,

        # New disease intelligence
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

        # Existing clinical intelligence
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

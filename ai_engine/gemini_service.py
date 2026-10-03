import json
import os
from typing import Any
import requests

from ai_engine.prompts import CLINICAL_SYSTEM_INSTRUCTION, build_analysis_prompt


def generate_fallback_explanation(animal_data: dict, features: dict, risk_data: dict) -> dict[str, Any]:
    """
    Deterministic clinical fallback generator when Gemini API is offline or unconfigured.
    Maintains 100% platform availability and explainability without external dependencies.
    """
    category = risk_data.get("risk_category", "low")
    score = risk_data.get("health_risk_score", 0.0)
    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"
    temp_dev = features.get("temp_deviation", 0.0)
    rum_drop = features.get("rumination_reduction_pct", 0.0)
    act_drop = features.get("activity_reduction_pct", 0.0)

    if category in ["critical", "high"]:
        clinical_interp = (
            f"Significant physiological deviation detected in {animal_name}. "
            f"The cluster of thermal elevation and rumination decline indicates a suspected acute health concern requiring veterinary review."
        )
        explanation = (
            f"Telemetry records body temperature at {features.get('latest_temp', 'N/A')} °C ({temp_dev:+.2f} °C variance), "
            f"combined with a {rum_drop:.1f}% reduction in rumination and a {act_drop:.1f}% drop in physical activity. "
            f"This physiological combination frequently correlates with systemic immune response or acute metabolic disruption."
        )
        recommended_action = (
            "Isolate the animal in a well-ventilated, shaded stall. Check rectal temperature manually and notify the attending veterinarian."
        )
        monitoring_rec = (
            "Continuous vital sign telemetry logging every 5 minutes. Conduct physical inspection of udder, joints, and mucous membranes every 2 hours."
        )
        questions = [
            "Are there visible nasal discharges, coughing, or audible thoracic wheezing?",
            "Is there localized swelling, tenderness, or heat in the mammary quarters (mastitis check)?",
            "Has feed intake ceased completely or is partial water consumption maintained?"
        ]
    elif category == "medium":
        clinical_interp = (
            f"Moderate physiological variance observed in {animal_name}. Mild sub-clinical stress or early anomaly suspected."
        )
        explanation = (
            f"Vital telemetry exhibits slight variance ({temp_dev:+.2f} °C temperature shift, {rum_drop:.1f}% rumination decline). "
            f"While vital parameters remain near acceptable thresholds, the trajectory suggests early metabolic or environmental stress."
        )
        recommended_action = (
            "Verify adequate access to clean drinking water and check ambient barn temperature for heat stress."
        )
        monitoring_rec = (
            "Monitor next 3 feeding and rumination cycles. Alert veterinarian if temperature rises above 39.5 °C."
        )
        questions = [
            "Has the daily ration composition or grazing area changed recently?",
            "Is the animal exhibiting signs of heat stress or lethargy during midday?"
        ]
    else:
        clinical_interp = (
            f"Physiological baseline for {animal_name} is within healthy reference parameters. No immediate clinical concerns."
        )
        explanation = (
            f"Body temperature ({features.get('latest_temp', 38.6):.2f} °C), heart rate, activity, and rumination index "
            f"all align closely with standard bovine physiological baselines."
        )
        recommended_action = "Maintain regular feeding schedule and preventive care routine."
        monitoring_rec = "Standard routine telemetry monitoring."
        questions = ["Continue standard herd management protocols."]

    return {
        "clinical_interpretation": clinical_interp,
        "explanation": explanation,
        "recommended_action": recommended_action,
        "monitoring_recommendation": monitoring_rec,
        "questions_for_veterinarian": questions,
        "source": "VETRA-Clinical-Fallback-Engine"
    }


def get_ai_clinical_explanation(animal_data: dict, features: dict, risk_data: dict) -> dict[str, Any]:
    """
    Generate an AI clinical decision support explanation using Gemini API,
    with automatic graceful fallback.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return generate_fallback_explanation(animal_data, features, risk_data)

    prompt = build_analysis_prompt(animal_data, features, risk_data)

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": CLINICAL_SYSTEM_INSTRUCTION}
                ]
            },
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        response = requests.post(url, json=payload, timeout=12)

        if response.status_code == 200:
            content = response.json()
            candidates = content.get("candidates", [])
            if candidates:
                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(text_part)
                parsed["source"] = "Gemini-2.5-Flash"
                return parsed

        # Fallback if status code != 200
        return generate_fallback_explanation(animal_data, features, risk_data)

    except Exception:
        # Fallback if network or parsing error occurs
        return generate_fallback_explanation(animal_data, features, risk_data)


def generate_visual_explanation(animal_data: dict, visual_data: dict) -> dict[str, Any]:
    """
    Generate decision-support explanation for visual observations.
    Never claims confirmed disease. Clearly distinguishes observed signs from clinical diagnoses.
    """
    obs = visual_data.get("observations", [])
    obs_names = [o.get("indicator", "").replace("_", " ").title() for o in obs]
    score = visual_data.get("visual_risk_score", 0.0)
    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"

    if obs:
        narrative = (
            f"Visual screening of {animal_name} identified {len(obs)} potential physical indicator(s): "
            f"{', '.join(obs_names)}. Overall visual risk evaluated at {score:.0f}/100. "
            f"These visual indicators represent observable signs for veterinary decision-support and do not constitute a confirmed diagnosis."
        )
    else:
        narrative = f"Visual screening of {animal_name} indicates nominal posture, gait, and coat condition with no visible distress markers."

    return {
        "visual_narrative": narrative,
        "observed_signs": obs_names,
        "decision_support_disclaimer": "Visual observations are AI-assisted indicators and require veterinary physical examination for clinical confirmation.",
        "source": "VETRA-Visual-Intelligence"
    }


def generate_multimodal_explanation(animal_data: dict, mm_data: dict) -> dict[str, Any]:
    """
    Generate unified multimodal clinical narrative fusing visual, physiological, and surveillance indicators.
    """
    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"
    comb_risk = mm_data.get("combined_risk", 0.0)
    consistency = mm_data.get("visual_telemetry_consistency", "nominal")
    factors = mm_data.get("contributing_factors", [])

    if consistency == "directionally_consistent":
        narrative = (
            f"Multimodal evaluation for {animal_name} reveals directionally concordant visual signs and physiological telemetry "
            f"(Combined Risk: {comb_risk:.0f}/100). Both observable posture/gait anomalies and vital deviations align, "
            f"substantially heightening confidence in an early health concern requiring prompt veterinary triage."
        )
    elif consistency == "divergent":
        narrative = (
            f"Multimodal evaluation for {animal_name} shows divergent indicators (Combined Risk: {comb_risk:.0f}/100). "
            f"Physical appearance and physiological telemetry present conflicting signals; sensor recalibration or focused clinical inspection recommended."
        )
    elif consistency == "isolated_visual":
        narrative = (
            f"Physical screening for {animal_name} detected visible surface or posture indicators while vital telemetry remains near baseline. "
            f"Inspect for localized injury or behavioral discomfort."
        )
    elif consistency == "isolated_telemetry":
        narrative = (
            f"Physiological telemetry shows vital deviations while visual screening appears nominal. Sub-clinical systemic or metabolic deviation suspected."
        )
    else:
        narrative = f"All multimodal health indicators for {animal_name} remain within healthy physiological and physical baselines."

    return {
        "multimodal_narrative": narrative,
        "contributing_factors": factors,
        "recommendation": "Prompt veterinary physical examination advised" if comb_risk >= 45 else "Continue routine herd surveillance",
        "source": "VETRA-Multimodal-Intelligence"
    }


def generate_predictive_explanation(animal_data: dict, prediction_data: dict) -> dict[str, Any]:
    """
    Deterministic clinical explanation generator for prospective health forecasting.
    Grounds all statements strictly in verified features and trends.
    """
    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"
    pred_risk = prediction_data.get("predicted_health_risk", 0.0)
    category = prediction_data.get("risk_category", "LOW")
    trend = prediction_data.get("trend", "stable")
    window = prediction_data.get("forecast_window_hours", 48)
    drivers = prediction_data.get("primary_drivers", [])
    confidence = prediction_data.get("confidence", 0.5)

    if category == "INSUFFICIENT_DATA":
        narrative = (
            f"Predictive health forecast for {animal_name} cannot be reliably generated "
            "due to insufficient historical telemetry. Additional observations are required."
        )
    elif category in ["CRITICAL", "HIGH"]:
        narrative = (
            f"Prospective health trajectory for {animal_name} shows elevated deterioration risk "
            f"over the next {window} hours (Predicted Risk: {pred_risk:.1f}/100, Trajectory: {trend.replace('_', ' ')}). "
            f"Key indicators include: {'; '.join(drivers[:3])}. Early veterinary review is strongly recommended."
        )
    elif category == "MODERATE":
        narrative = (
            f"Prospective health trajectory for {animal_name} indicates mild risk elevation "
            f"over the next {window} hours (Predicted Risk: {pred_risk:.1f}/100, Trajectory: {trend.replace('_', ' ')}). "
            f"Contributing factors: {'; '.join(drivers[:2])}. Enhanced herd observation recommended."
        )
    else:
        narrative = (
            f"Prospective health forecast for {animal_name} indicates stable baseline health "
            f"over the next {window} hours (Predicted Risk: {pred_risk:.1f}/100). No acute deterioration signals detected."
        )

    return {
        "predictive_narrative": narrative,
        "primary_drivers": drivers,
        "confidence": confidence,
        "forecast_window_hours": window,
        "clinical_safety_notice": "Decision Support Only: Prospective health risks are statistical estimates and not medical diagnoses.",
        "source": "VETRA-Predictive-Clinical-Engine"
    }


def get_ai_predictive_explanation(animal_data: dict, prediction_data: dict) -> dict[str, Any]:
    """
    Attempts to generate an enriched predictive explanation via Gemini API,
    falling back to the deterministic explanation engine on any failure or missing credentials.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return generate_predictive_explanation(animal_data, prediction_data)

    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"
    prompt = (
        f"You are the VETRA Clinical Decision Support Assistant. Provide a brief 2-3 sentence veterinary explanation "
        f"for a prospective health forecast.\n"
        f"Animal: {animal_name} ({animal_data.get('breed', 'Bovine')})\n"
        f"Predicted Risk: {prediction_data.get('predicted_health_risk')}/100 ({prediction_data.get('risk_category')})\n"
        f"Forecast Window: {prediction_data.get('forecast_window_hours')} hours\n"
        f"Trajectory: {prediction_data.get('trend')}\n"
        f"Confidence: {int(prediction_data.get('confidence', 0.5)*100)}%\n"
        f"Key Evidence: {', '.join(prediction_data.get('primary_drivers', []))}\n"
        f"Rules: NEVER make a definitive clinical diagnosis. Use terms like 'elevated predicted risk' and 'early warning signal'."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=6)
        if res.status_code == 200:
            data = res.json()
            gemini_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {
                "predictive_narrative": gemini_text,
                "primary_drivers": prediction_data.get("primary_drivers", []),
                "confidence": prediction_data.get("confidence", 0.5),
                "forecast_window_hours": prediction_data.get("forecast_window_hours", 48),
                "clinical_safety_notice": "Decision Support Only: Prospective health risks are statistical estimates and not medical diagnoses.",
                "source": "Gemini-2.5-Flash-Predictive-AI"
            }
    except Exception:
        pass

    return generate_predictive_explanation(animal_data, prediction_data)


# ============================================================
# PHASE 13: SURVEILLANCE & INSTITUTIONAL NARRATIVE DRAFTING
# ============================================================

def generate_surveillance_narrative_draft(event_data: dict, evidence_summary: dict) -> dict[str, Any]:
    """
    Deterministic surveillance narrative generator.
    Guarantees decision support safety:
    - Never confirms an outbreak autonomously.
    - Status strictly remains DRAFT until human review.
    - Grounded only in verified event and telemetry signals.
    """
    event_id = event_data.get("event_id", "EPI-EVENT")
    ev_type = event_data.get("event_type", "surveillance_signal").replace("_", " ")
    severity = str(event_data.get("severity", "moderate")).upper()
    risk_score = event_data.get("risk_score", 45.0)

    narrative = (
        f"[DRAFT SURVEILLANCE NARRATIVE] Epidemiological event {event_id} indicates a {severity} severity {ev_type} "
        f"with a composite risk score of {risk_score:.1f}/100. "
        "Multi-source correlation suggests statistical variance across monitored vital parameters and clinical signals. "
        "This draft requires authorized human veterinary and institutional officer review prior to any regulatory action."
    )

    return {
        "status": "DRAFT",
        "narrative": narrative,
        "event_id": event_id,
        "is_ai_generated": False,
        "review_required": True,
        "safety_disclaimer": "AI Decision Support: Draft narrative for human officer review. Does not confirm outbreaks autonomously or override institutional authorization."
    }


def get_ai_surveillance_narrative_draft(event_data: dict, evidence_summary: dict) -> dict[str, Any]:
    """
    Attempts to draft an epidemiological narrative via Gemini API,
    falling back to the deterministic safety engine on any failure or missing credentials.
    All outputs strictly labeled DRAFT.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return generate_surveillance_narrative_draft(event_data, evidence_summary)

    prompt = (
        f"You are the VETRA Institutional Epidemiological Surveillance Assistant. Draft a 2-3 sentence institutional "
        f"summary for an epidemiological surveillance signal.\n"
        f"Event ID: {event_data.get('event_id')}\n"
        f"Type: {event_data.get('event_type')}\n"
        f"Severity: {event_data.get('severity')}\n"
        f"Risk Score: {event_data.get('risk_score')}\n"
        f"Evidence: {json.dumps(evidence_summary)}\n"
        "MANDATORY SAFETY RULES:\n"
        "1. Prefix your response with '[DRAFT NARRATIVE]'.\n"
        "2. NEVER declare or confirm an official outbreak autonomously.\n"
        "3. Emphasize that formal human veterinary/institutional review is required."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=6)
        if res.status_code == 200:
            data = res.json()
            gemini_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {
                "status": "DRAFT",
                "narrative": gemini_text,
                "event_id": event_data.get("event_id"),
                "is_ai_generated": True,
                "review_required": True,
                "safety_disclaimer": "AI Decision Support: Draft narrative for human officer review. Does not confirm outbreaks autonomously or override institutional authorization."
            }
    except Exception:
        pass

    return generate_surveillance_narrative_draft(event_data, evidence_summary)




from datetime import datetime, timezone
from typing import Any, Optional


CLINICAL_SAFETY_DISCLAIMER = (
    "Decision Support Only: Multimodal health assessments synthesize visual, physiological, and epidemiological "
    "signals for clinical triage. Official diagnosis requires licensed veterinary examination."
)

# Standardized multimodal weighting model (sum = 1.0)
WEIGHT_VISUAL = 0.30
WEIGHT_TELEMETRY = 0.30
WEIGHT_DISEASE = 0.15
WEIGHT_SURVEILLANCE = 0.15
WEIGHT_PREVENTIVE = 0.10


def compute_multimodal_health_assessment(
    animal_data: dict[str, Any],
    visual_analysis: Optional[dict[str, Any]],
    telemetry_risk_data: Optional[dict[str, Any]],
    disease_intelligence_data: Optional[dict[str, Any]],
    surveillance_risk_data: Optional[dict[str, Any]],
    preventive_status_data: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """
    Multimodal Animal Health Intelligence Engine.

    Synthesizes:
    1. Visual Health Risk (0-100)
    2. IoT Telemetry Health Risk (0-100)
    3. Disease Intelligence Pattern Risk (0-100)
    4. Herd Surveillance Risk (0-100)
    5. Preventive Health Gaps Risk (0-100)

    Produces a transparent weighted combined score, evaluates directional
    consistency between visual cues and sensor telemetry, and generates
    prioritized clinical recommendations.
    """
    now = datetime.now(timezone.utc)
    animal_name = animal_data.get("name") or animal_data.get("tag_id") or "Animal"

    # 1. Component Scores Extraction (normalized 0-100)
    visual_score = float(visual_analysis.get("visual_risk_score", 0.0)) if visual_analysis else 0.0

    # Telemetry risk (from evaluate_health_risk or animal risk)
    telemetry_score = float(telemetry_risk_data.get("health_risk_score", 0.0)) if telemetry_risk_data else 0.0

    # Disease intelligence risk
    if disease_intelligence_data and "disease_risk_score" in disease_intelligence_data:
        disease_score = float(disease_intelligence_data["disease_risk_score"])
    else:
        d_level = str(disease_intelligence_data.get("disease_risk_level", "low")).lower() if disease_intelligence_data else "low"
        if d_level == "high":
            disease_score = 75.0
        elif d_level == "moderate":
            disease_score = 45.0
        else:
            disease_score = 15.0

    # Surveillance risk (from farm risk profile)
    surveillance_score = float(surveillance_risk_data.get("risk_score", 0.0)) if surveillance_risk_data else 0.0

    # Preventive risk (overdue tasks / gaps)
    if preventive_status_data and "preventive_risk_score" in preventive_status_data:
        preventive_score = float(preventive_status_data["preventive_risk_score"])
    else:
        overdue_count = int(preventive_status_data.get("overdue_tasks_count", 0)) if preventive_status_data else 0
        if overdue_count >= 3:
            preventive_score = 80.0
        elif overdue_count >= 1:
            preventive_score = 40.0
        else:
            preventive_score = 10.0

    # 2. Weighted Combined Risk Score
    combined_raw = (
        (visual_score * WEIGHT_VISUAL) +
        (telemetry_score * WEIGHT_TELEMETRY) +
        (disease_score * WEIGHT_DISEASE) +
        (surveillance_score * WEIGHT_SURVEILLANCE) +
        (preventive_score * WEIGHT_PREVENTIVE)
    )
    combined_risk = round(min(max(combined_raw, 0.0), 100.0), 1)

    # 3. Categorical Grading
    if combined_risk >= 70.0:
        risk_category = "CRITICAL"
        vet_review_req = True
    elif combined_risk >= 45.0:
        risk_category = "HIGH"
        vet_review_req = True
    elif combined_risk >= 25.0:
        risk_category = "MODERATE"
        vet_review_req = visual_score >= 35.0 or telemetry_score >= 35.0
    else:
        risk_category = "LOW"
        vet_review_req = False

    # 4. Directional Consistency Analysis (Step 15)
    visual_obs = visual_analysis.get("observations", []) if visual_analysis else []
    visual_indicators = {o["indicator"] for o in visual_obs}

    v_high = visual_score >= 35.0
    t_high = telemetry_score >= 35.0

    consistency_reasons = []
    if "respiratory_effort" in visual_indicators and telemetry_risk_data:
        resp_rate = telemetry_risk_data.get("latest_resp", 0.0)
        if resp_rate >= 35.0:
            consistency_reasons.append("Visual respiratory effort corroborates elevated telemetry respiratory rate.")

    if ("visible_lethargy" in visual_indicators or "standing_lying_state" in visual_indicators) and telemetry_risk_data:
        act_level = telemetry_risk_data.get("latest_activity", 100.0)
        if act_level < 50.0:
            consistency_reasons.append("Visual recumbency/lethargy aligns with reduced IoT physical activity telemetry.")

    if v_high and t_high:
        consistency = "consistent"
        consistency_summary = "High directional consistency: visual anomalies and physiological vitals mutually reinforce health concern."
    elif v_high and not t_high:
        consistency = "isolated_visual"
        consistency_summary = "Visual anomaly detected while sensor telemetry remains within acceptable baseline."
    elif not v_high and t_high:
        consistency = "isolated_telemetry"
        consistency_summary = "Physiological sensor deviation detected without visible external signs (possible sub-clinical condition)."
    elif abs(visual_score - telemetry_score) > 30.0:
        consistency = "divergent"
        consistency_summary = "Variance between visual inspection and IoT telemetry requires field clinical verification."
    else:
        consistency = "nominal"
        consistency_summary = "Both visual inspection and telemetry sensors indicate stable baseline health."

    # 5. Contributing Factors Breakdown
    factors = []
    if visual_score >= 25.0:
        obs_names = [o["description"] for o in visual_obs]
        factors.append(f"Visual Signals ({visual_score:.0f}/100): {'; '.join(obs_names[:2])}")
    if telemetry_score >= 25.0:
        factors.append(f"IoT Telemetry ({telemetry_score:.0f}/100): Physiological parameters deviate from reference baseline.")
    if disease_score >= 40.0:
        factors.append(f"Disease Screening ({disease_score:.0f}/100): Active physiological risk pattern detected.")
    if surveillance_score >= 40.0:
        factors.append(f"Holding Surveillance ({surveillance_score:.0f}/100): Herd is under elevated surveillance monitoring.")
    if preventive_score >= 40.0:
        factors.append(f"Preventive Care Gaps ({preventive_score:.0f}/100): {overdue_count} overdue preventive health protocol(s).")

    if not factors:
        factors.append("All visual, physiological, preventive, and surveillance parameters align with healthy baseline.")

    # 6. Actionable Clinical Explanation
    if risk_category in ["CRITICAL", "HIGH"]:
        explanation = (
            f"Multimodal assessment flags elevated health risk ({combined_risk}/100 - {risk_category}) for {animal_name}. "
            f"{consistency_summary} Immediate veterinary physical triage and diagnostic examination recommended."
        )
        recommended_action = "Initiate veterinary clinical case; isolate animal in clean holding pen; check rectal temperature."
    elif risk_category == "MODERATE":
        explanation = (
            f"Multimodal assessment indicates moderate health variance ({combined_risk}/100) for {animal_name}. "
            f"{consistency_summary} Parameters suggest early or sub-clinical stress."
        )
        recommended_action = "Increase telemetry logging; perform follow-up visual reassessment in 24 hours; verify feed and water intake."
    else:
        explanation = (
            f"Multimodal assessment confirms healthy vital baseline ({combined_risk}/100 - LOW) for {animal_name}. "
            f"{consistency_summary}"
        )
        recommended_action = "Maintain routine sensor monitoring, good nutrition, and adherence to preventive vaccination schedule."

    return {
        "assessment_id": f"MM-{now.strftime('%Y%m%d')}-{int(now.timestamp()) % 100000:05d}",
        "animal_id": str(animal_data.get("_id") or animal_data.get("id")),
        "animal_tag": animal_data.get("tag_id"),
        "animal_name": animal_data.get("name"),
        "farm_id": str(animal_data.get("farm_id", "")),
        "visual_analysis_id": str(visual_analysis.get("id") or visual_analysis.get("_id", "")) if visual_analysis else None,
        "visual_score": visual_score,
        "telemetry_score": telemetry_score,
        "disease_risk": disease_score,
        "preventive_risk": preventive_score,
        "surveillance_risk": surveillance_score,
        "combined_risk": combined_risk,
        "risk_category": risk_category,
        "contributing_factors": factors,
        "visual_telemetry_consistency": consistency,
        "consistency_summary": consistency_summary,
        "explanation": explanation,
        "recommended_action": recommended_action,
        "veterinary_review_required": vet_review_req,
        "created_at": now.isoformat(),
        "clinical_safety_notice": CLINICAL_SAFETY_DISCLAIMER
    }


def compare_temporal_visual_analyses(
    earlier_analysis: dict[str, Any],
    latest_analysis: dict[str, Any]
) -> dict[str, Any]:
    """
    Compare chronological visual assessments for the same animal.
    Detects persistent, worsening, improving, or emerging visual signs.
    """
    e_obs = {o["indicator"]: o for o in earlier_analysis.get("observations", [])}
    l_obs = {o["indicator"]: o for o in latest_analysis.get("observations", [])}

    e_score = earlier_analysis.get("visual_risk_score", 0.0)
    l_score = latest_analysis.get("visual_risk_score", 0.0)
    score_delta = round(l_score - e_score, 1)

    persistent = [ind for ind in l_obs if ind in e_obs]
    new_signals = [ind for ind in l_obs if ind not in e_obs]
    resolved_signals = [ind for ind in e_obs if ind not in l_obs]

    if score_delta >= 15.0 or (new_signals and l_score >= 35.0):
        trajectory = "worsening"
        explanation = (
            f"Visual condition shows elevated concern (+{score_delta:.1f} score variance). "
            f"New signals detected: {', '.join(new_signals) if new_signals else 'Increased severity'}."
        )
    elif score_delta <= -15.0 or (resolved_signals and l_score < 25.0):
        trajectory = "improved"
        explanation = (
            f"Visual indicators have improved ({score_delta:+.1f} score reduction). "
            f"Resolved signals: {', '.join(resolved_signals) if resolved_signals else 'Reduced severity'}."
        )
    elif persistent:
        trajectory = "stable"
        explanation = (
            f"Visual indicators remain stable over time ({score_delta:+.1f} variance). "
            f"Persistent signals: {', '.join(persistent)}."
        )
    else:
        trajectory = "stable"
        explanation = "Visual assessment parameters remain stable within baseline reference range."

    changes = []
    for p in persistent:
        changes.append({"indicator": p, "change": "persistent", "current_confidence": l_obs[p].get("confidence")})
    for n in new_signals:
        changes.append({"indicator": n, "change": "new_signal", "current_confidence": l_obs[n].get("confidence")})
    for r in resolved_signals:
        changes.append({"indicator": r, "change": "resolved", "previous_confidence": e_obs[r].get("confidence")})

    return {
        "animal_id": str(latest_analysis.get("animal_id")),
        "animal_tag": latest_analysis.get("animal_tag"),
        "earlier_analysis_id": str(earlier_analysis.get("analysis_id") or earlier_analysis.get("_id")),
        "latest_analysis_id": str(latest_analysis.get("analysis_id") or latest_analysis.get("_id")),
        "earlier_date": str(earlier_analysis.get("created_at")),
        "latest_date": str(latest_analysis.get("created_at")),
        "trajectory": trajectory,
        "score_delta": score_delta,
        "persistent_indicators": persistent,
        "new_indicators": new_signals,
        "resolved_indicators": resolved_signals,
        "changes": changes,
        "explanation": explanation
    }

"""
Prompt templates for VETRA Gemini AI Clinical Decision Support Engine.
"""

CLINICAL_SYSTEM_INSTRUCTION = """
You are VETRA AI — an Intelligent Livestock Health Decision-Support Assistant designed for farmers and veterinarians.

CRITICAL CLINICAL & ETHICAL GUIDELINES:
1. DECISION SUPPORT ONLY: You are an assistive triage system, NOT a licensed veterinary medical authority.
2. NO CONFIRMED DIAGNOSES: Never state that an animal "has" or is "diagnosed with" a specific disease.
3. UNCERTAINTY-AWARE LANGUAGE: Always use probabilistic terms such as:
   - "Suspected physiological abnormality"
   - "Elevated health risk detected"
   - "Requires urgent veterinary review"
   - "Recommended observation protocol"
4. EVIDENCE GROUNDED: Base all observations strictly on the telemetry deviations, risk score, and animal context provided.
5. PRACTICAL ACTIONS: Provide clear, actionable, humane steps for the farmer (e.g. quarantine, hydration, veterinary alert, physical inspection).

Your output must be formatted as valid JSON adhering to the requested schema.
"""


def build_analysis_prompt(animal_data: dict, features: dict, risk_data: dict) -> str:
    """
    Construct a structured prompt for Gemini evaluation.
    """
    return f"""
Analyze the following livestock physiological telemetry data and provide a clinical triage summary.

ANIMAL INFORMATION:
- Name: {animal_data.get('name', 'Unknown')}
- Tag ID: {animal_data.get('tag_id', 'Unknown')}
- Species: {animal_data.get('species', 'Cattle')}
- Breed: {animal_data.get('breed', 'Unknown')}
- Gender: {animal_data.get('gender', 'Unknown')}
- Current Health Status: {animal_data.get('health_status', 'monitoring')}

TELEMETRY & STATISTICAL FEATURES:
- Latest Temperature: {features.get('latest_temp', 'N/A')} °C (Avg: {features.get('avg_temp', 'N/A')} °C, Dev: {features.get('temp_deviation', 0.0):+0.2f} °C)
- Latest Heart Rate: {features.get('latest_heart_rate', 'N/A')} BPM (Avg: {features.get('avg_heart_rate', 'N/A')} BPM, Dev: {features.get('hr_deviation', 0.0):+0.1f} BPM)
- Latest Respiration: {features.get('latest_respiratory_rate', 'N/A')} /min (Avg: {features.get('avg_respiratory_rate', 'N/A')} /min)
- Activity Reduction: {features.get('activity_reduction_pct', 0.0)}% drop
- Rumination Reduction: {features.get('rumination_reduction_pct', 0.0)}% drop
- Thermal Rate of Change: {features.get('temp_rate_of_change', 0.0):+0.2f} °C
- Recent Trend: {features.get('recent_trend', 'stable')}
- Vital Stability Index: {features.get('vital_stability_score', 100.0)}/100

ML RISK ENGINE ASSESSMENT:
- Calculated Risk Score: {risk_data.get('health_risk_score', 0)} / 100
- Risk Category: {risk_data.get('risk_category', 'low').upper()}
- Contributing Factors:
{chr(10).join(['  * ' + f for f in risk_data.get('contributing_factors', [])])}

RESPONSE REQUIREMENTS:
Provide your response strictly in the following JSON structure:
{{
  "clinical_interpretation": "1-2 sentence high-level clinical summary using cautious terminology",
  "explanation": "Detailed physiological explanation correlating temperature, rumination, heart rate, and activity",
  "recommended_action": "Primary immediate action step for the farmer",
  "monitoring_recommendation": "Specific monitoring frequency and protocol for the next 12-24 hours",
  "questions_for_veterinarian": [
    "Key question or symptom to verify during physical examination",
    "Secondary inspection question"
  ]
}}
"""

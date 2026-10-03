from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from bson import ObjectId


def _normalize_dt(dt: Any) -> Optional[datetime]:
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def compute_farm_disease_risk(
    farm: dict[str, Any],
    db: Any,
    window_days: int = 7
) -> dict[str, Any]:

    """
    Deterministic Farm Disease Risk Engine.

    Calculates a standardized 0–100 risk score and categorical profile
    for a farm based on:
    1. Proportion of herd exhibiting physiological telemetry deviations (0-25 pts)
    2. Severity-weighted active health alerts (0-25 pts)
    3. Active suspected disease events under surveillance (0-20 pts)
    4. Active open veterinary clinical cases (0-15 pts)
    5. Preventive compliance and overdue preventive tasks (0-15 pts)

    Scoring Tiers:
    - 0–24:   LOW
    - 25–49:  MODERATE
    - 50–74:  HIGH
    - 75–100: CRITICAL
    """
    farm_id = str(farm.get("_id") or farm.get("id"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    # 1. Animals belonging to this farm
    animals = list(db.animals.find({"farm_id": farm_id}))
    if not animals and ObjectId.is_valid(farm_id):
        animals = list(db.animals.find({"farm_id": ObjectId(farm_id)}))

    total_animals = len(animals)
    animal_ids = [str(a["_id"]) for a in animals]
    animal_tags = {str(a["_id"]): a.get("tag_id") or a.get("name") or "Unknown" for a in animals}

    # 2. Telemetry abnormalities in window
    # Query readings for these animals
    abnormal_animal_ids = set()
    dominant_patterns = []

    if animal_ids:
        # Check readings where status is abnormal or critical, or alert_triggered is True
        query = {
            "animal_id": {"$in": animal_ids},
            "timestamp": {"$gte": cutoff}
        }
        readings = list(db.health_readings.find(query).limit(500))
        for r in readings:
            temp = r.get("temperature_c", 38.5)
            hr = r.get("heart_rate_bpm", 70)
            resp = r.get("respiratory_rate", 24)
            rum = r.get("rumination_level", 450)
            act = r.get("activity_level", 100)
            status = r.get("status", "normal")

            is_abnormal = status in ["abnormal", "critical"] or r.get("alert_triggered") is True
            if temp >= 39.5 or temp < 37.0 or resp >= 40 or hr >= 100 or act < 40:
                is_abnormal = True

            if is_abnormal:
                aid = str(r.get("animal_id"))
                abnormal_animal_ids.add(aid)
                if temp >= 39.5:
                    dominant_patterns.append("Thermal Elevation / Fever")
                if resp >= 38:
                    dominant_patterns.append("Respiratory Stress Pattern")
                if rum < 300 or act < 40:
                    dominant_patterns.append("Rumination / Metabolic Drop")

    affected_animals_count = len(abnormal_animal_ids)
    abnormal_pct = round((affected_animals_count / total_animals * 100.0) if total_animals > 0 else 0.0, 1)

    # Component 1: Telemetry abnormality (0-25 pts)
    if abnormal_pct == 0:
        telemetry_score = 0.0
    elif abnormal_pct < 20.0:
        telemetry_score = 8.0
    elif abnormal_pct < 50.0:
        telemetry_score = 16.0
    else:
        telemetry_score = 25.0

    # Component 2: Active alerts (0-25 pts)
    alert_query = {
        "farm_id": farm_id,
        "status": "active"
    }
    active_alerts = list(db.alerts.find(alert_query))
    if not active_alerts and ObjectId.is_valid(farm_id):
        active_alerts = list(db.alerts.find({"farm_id": ObjectId(farm_id), "status": "active"}))

    alert_score = 0.0
    for al in active_alerts:
        sev = al.get("severity", "low")
        if sev == "critical":
            alert_score += 10.0
        elif sev == "high":
            alert_score += 6.0
        elif sev == "medium":
            alert_score += 3.0
        else:
            alert_score += 1.0
    alert_score = min(alert_score, 25.0)

    # Component 3: Suspected Disease Events (0-20 pts)
    event_query = {
        "farm_id": farm_id,
        "status": {"$in": ["suspected", "under_investigation"]}
    }
    disease_events = list(db.disease_events.find(event_query))
    if len(disease_events) >= 2:
        event_score = 20.0
    elif len(disease_events) == 1:
        event_score = 10.0
    else:
        event_score = 0.0

    for de in disease_events:
        if de.get("disease_name"):
            dominant_patterns.append(de["disease_name"])

    # Component 4: Active Veterinary Cases (0-15 pts)
    case_query = {
        "farm_id": farm_id,
        "status": {"$in": ["open", "in_progress", "pending_review"]}
    }
    vet_cases = list(db.veterinary_cases.find(case_query))
    if len(vet_cases) >= 2:
        case_score = 15.0
    elif len(vet_cases) == 1:
        case_score = 8.0
    else:
        case_score = 0.0

    # Component 5: Preventive Care Gaps (0-15 pts)
    # Check overdue preventive tasks
    now_str = now.strftime("%Y-%m-%d")
    prev_query = {
        "farm_id": farm_id,
        "status": "pending",
        "due_date": {"$lt": now_str}
    }
    overdue_tasks = list(db.preventive_tasks.find(prev_query))
    if len(overdue_tasks) >= 3:
        preventive_score = 15.0
    elif len(overdue_tasks) >= 1:
        preventive_score = 7.5
    else:
        preventive_score = 0.0

    # Total score calculation
    raw_total = telemetry_score + alert_score + event_score + case_score + preventive_score
    risk_score = round(min(max(raw_total, 0.0), 100.0), 1)

    # Categorization
    if risk_score >= 75.0:
        risk_category = "CRITICAL"
    elif risk_score >= 50.0:
        risk_category = "HIGH"
    elif risk_score >= 25.0:
        risk_category = "MODERATE"
    else:
        risk_category = "LOW"

    # Contributing factors
    contributing_factors = []
    if telemetry_score > 0:
        contributing_factors.append(
            f"{affected_animals_count}/{total_animals} animals ({abnormal_pct}%) exhibit vital or behavioral deviations."
        )
    if alert_score > 0:
        contributing_factors.append(
            f"{len(active_alerts)} active unresolved alerts contributing {alert_score:.1f} risk points."
        )
    if event_score > 0:
        contributing_factors.append(
            f"{len(disease_events)} suspected or active disease events under investigation."
        )
    if case_score > 0:
        contributing_factors.append(
            f"{len(vet_cases)} active veterinary clinical cases on the holding."
        )
    if preventive_score > 0:
        contributing_factors.append(
            f"{len(overdue_tasks)} overdue preventive health protocols."
        )

    if not contributing_factors:
        contributing_factors.append("Vital indicators, alerts, and preventive care are within normal reference baseline.")

    # Dominant pattern
    if dominant_patterns:
        dominant_pattern = max(set(dominant_patterns), key=dominant_patterns.count)
    else:
        dominant_pattern = "Normal / Baseline"

    # Trend calculation: compare first half of window vs second half

    midpoint = (now.replace(tzinfo=None) - timedelta(days=window_days / 2.0))
    recent_readings_abnormal = sum(
        1 for r in readings
        if _normalize_dt(r.get("timestamp")) and _normalize_dt(r.get("timestamp")) >= midpoint and (r.get("status") in ["abnormal", "critical"] or r.get("alert_triggered") is True)
    ) if animal_ids else 0
    older_readings_abnormal = sum(
        1 for r in readings
        if _normalize_dt(r.get("timestamp")) and _normalize_dt(r.get("timestamp")) < midpoint and (r.get("status") in ["abnormal", "critical"] or r.get("alert_triggered") is True)
    ) if animal_ids else 0


    if recent_readings_abnormal > older_readings_abnormal + 1:
        trend = "escalating"
    elif older_readings_abnormal > recent_readings_abnormal + 1:
        trend = "recovering"
    else:
        trend = "stable"

    # Confidence calculation: based on sample size and data freshness
    confidence = 0.85 if total_animals > 0 and len(readings) > 0 else 0.70

    affected_tags = [animal_tags.get(aid, aid) for aid in abnormal_animal_ids]

    return {
        "farm_id": farm_id,
        "farm_name": farm.get("name", "Unknown Farm"),
        "location": farm.get("location", "Location unspecified"),
        "latitude": farm.get("latitude"),
        "longitude": farm.get("longitude"),
        "district": farm.get("district"),
        "state": farm.get("state"),
        "pincode": farm.get("pincode"),
        "total_animals": total_animals,
        "affected_animals_count": affected_animals_count,
        "abnormal_animals_pct": abnormal_pct,
        "active_alerts_count": len(active_alerts),
        "active_disease_events_count": len(disease_events),
        "veterinary_cases_count": len(vet_cases),
        "risk_score": risk_score,
        "risk_category": risk_category,
        "dominant_disease_pattern": dominant_pattern,
        "trend": trend,
        "confidence": confidence,
        "contributing_factors": contributing_factors,
        "affected_animal_tags": affected_tags,
        "generated_at": now.isoformat()
    }

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from bson import ObjectId
from pymongo.database import Database

from app.database import get_database


def _parse_date(value: Any) -> Optional[date]:
    """Safely parse a date from datetime, date, or ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    val_str = str(value).strip()
    if not val_str:
        return None
    try:
        return date.fromisoformat(val_str[:10])
    except ValueError:
        return None


def _get_user_scope_query(
    db: Database,
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> tuple[dict[str, Any], list[str], list[str]]:
    """
    Determine the authorized query filter and accessible farm/animal IDs.
    Returns (animal_query, accessible_farm_ids, accessible_animal_ids).
    """
    role = (role or "farmer").lower()
    farm_ids: list[str] = []

    if role == "admin":
        if farm_id and farm_id != "all":
            farm_ids = [farm_id]
            animal_query: dict[str, Any] = {"farm_id": {"$in": [farm_id, ObjectId(farm_id) if ObjectId.is_valid(farm_id) else farm_id]}}
        else:
            animal_query = {}
    elif role == "veterinarian":
        if farm_id and farm_id != "all":
            farm_ids = [farm_id]
            animal_query = {"farm_id": {"$in": [farm_id, ObjectId(farm_id) if ObjectId.is_valid(farm_id) else farm_id]}}
        else:
            animal_query = {}
    else:  # Farmer
        user_farms = list(db.farms.find({
            "$or": [
                {"owner_id": user_id},
                {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}
            ]
        }))
        for f in user_farms:
            f_str_id = str(f["_id"])
            farm_ids.append(f_str_id)
            if f.get("farm_id"):
                farm_ids.append(str(f["farm_id"]))

        if farm_id and farm_id != "all":
            # Verify farmer owns this farm
            if farm_id in farm_ids:
                animal_query = {"$or": [{"farm_id": farm_id}, {"farm_id": ObjectId(farm_id) if ObjectId.is_valid(farm_id) else farm_id}]}
            else:
                animal_query = {"_id": None}  # Unauthorized
        else:
            animal_query = {
                "$or": [
                    {"owner_id": user_id},
                    {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id},
                    {"farm_id": {"$in": farm_ids}}
                ]
            }

    # Fetch accessible animal IDs
    animals = list(db.animals.find(animal_query, {"_id": 1, "animal_id": 1, "tag_id": 1}))
    animal_ids = []
    for a in animals:
        animal_ids.append(str(a["_id"]))
        if a.get("animal_id"):
            animal_ids.append(str(a["animal_id"]))
        if a.get("tag_id"):
            animal_ids.append(str(a["tag_id"]))

    return animal_query, farm_ids, animal_ids


def get_overview_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None,
    species: Optional[str] = None,
    days: int = 7
) -> dict[str, Any]:
    """
    Compute real-time operational KPIs for the Command Center.
    Calculates animal health states, active alerts, preventive workload,
    veterinary cases, devices, and the Herd Health Index.
    """
    db = get_database()
    animal_query, farm_ids, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    if species and species.lower() != "all":
        animal_query["species"] = {"$regex": f"^{species}$", "$options": "i"}

    # 1. Animal Counts & Health Status
    animals = list(db.animals.find(animal_query))
    total_animals = len(animals)

    healthy_count = 0
    monitoring_count = 0
    at_risk_count = 0
    critical_count = 0

    for a in animals:
        status_val = str(a.get("health_status", "healthy")).strip().lower().replace(" ", "_")
        if status_val in ["healthy", "normal"]:
            healthy_count += 1
        elif status_val in ["monitoring", "watch"]:
            monitoring_count += 1
        elif status_val in ["at_risk", "high", "high_risk", "warning"]:
            at_risk_count += 1
        elif status_val in ["critical", "emergency"]:
            critical_count += 1
        else:
            healthy_count += 1

    # 2. Total Farms
    if role == "farmer":
        total_farms = db.farms.count_documents({
            "$or": [
                {"owner_id": user_id},
                {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}
            ]
        })
    else:
        total_farms = db.farms.count_documents({})

    # 3. Alerts
    alert_query: dict[str, Any] = {"status": "active"}
    if animal_ids:
        alert_query["animal_id"] = {"$in": animal_ids}
    elif role == "farmer":
        alert_query["owner_id"] = user_id

    active_alerts = list(db.alerts.find(alert_query))
    active_alerts_count = len(active_alerts)
    critical_alerts_count = sum(1 for al in active_alerts if str(al.get("severity", "")).lower() == "critical")
    high_alerts_count = sum(1 for al in active_alerts if str(al.get("severity", "")).lower() == "high")

    # 4. Preventive Workload
    prevention_summary = get_prevention_analytics(user_id, role, farm_id)
    preventive_due_count = prevention_summary["due_today_count"] + prevention_summary["overdue_count"]
    preventive_compliance = prevention_summary["compliance_rate"]

    # 5. Veterinary Cases
    vet_summary = get_veterinary_analytics(user_id, role, farm_id)
    open_cases_count = vet_summary["open_cases"]

    # 6. Devices Online & Telemetry Volume
    device_summary = get_device_analytics(user_id, role, farm_id)
    devices_online = device_summary["online_devices"]
    total_devices = device_summary["total_devices"]

    # Telemetry volume in selected days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reading_query: dict[str, Any] = {
        "$or": [
            {"recorded_at": {"$gte": cutoff}},
            {"timestamp": {"$gte": cutoff}}
        ]
    }
    if animal_ids:
        reading_query["animal_id"] = {"$in": animal_ids}
    telemetry_volume = db.health_readings.count_documents(reading_query)

    # 7. Herd Health Index
    hhi = get_herd_health_index(
        total_animals=total_animals,
        healthy_count=healthy_count,
        monitoring_count=monitoring_count,
        at_risk_count=at_risk_count,
        critical_count=critical_count,
        critical_alerts=critical_alerts_count,
        high_alerts=high_alerts_count,
        active_alerts=active_alerts_count,
        overdue_preventive=prevention_summary["overdue_count"],
        open_cases=open_cases_count,
        preventive_compliance=preventive_compliance,
        devices_online_pct=device_summary["sensor_coverage_pct"]
    )

    # Risk Distribution Breakdown
    risk_distribution = {
        "low": {"count": healthy_count, "percentage": round((healthy_count / total_animals * 100) if total_animals > 0 else 0, 1)},
        "medium": {"count": monitoring_count, "percentage": round((monitoring_count / total_animals * 100) if total_animals > 0 else 0, 1)},
        "high": {"count": at_risk_count, "percentage": round((at_risk_count / total_animals * 100) if total_animals > 0 else 0, 1)},
        "critical": {"count": critical_count, "percentage": round((critical_count / total_animals * 100) if total_animals > 0 else 0, 1)}
    }

    return {
        "kpis": {
            "total_farms": total_farms,
            "total_animals": total_animals,
            "healthy_animals": healthy_count,
            "animals_under_monitoring": monitoring_count,
            "high_risk_animals": at_risk_count,
            "critical_animals": critical_count,
            "active_alerts": active_alerts_count,
            "critical_alerts": critical_alerts_count,
            "high_alerts": high_alerts_count,
            "preventive_actions_due": preventive_due_count,
            "open_veterinary_cases": open_cases_count,
            "devices_online": devices_online,
            "total_devices": total_devices,
            "telemetry_volume": telemetry_volume,
            "preventive_compliance": preventive_compliance
        },
        "risk_distribution": risk_distribution,
        "herd_health_index": hhi,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def get_herd_health_index(
    total_animals: int,
    healthy_count: int,
    monitoring_count: int,
    at_risk_count: int,
    critical_count: int,
    critical_alerts: int,
    high_alerts: int,
    active_alerts: int,
    overdue_preventive: int,
    open_cases: int,
    preventive_compliance: float,
    devices_online_pct: float
) -> dict[str, Any]:
    """
    Transparent, documented formula for Herd Health Index (0 - 100).
    Starts at 100 baseline.
    Deductions are proportionally weighted by herd size where appropriate:
    - Critical animal: -15 pts
    - High-risk animal: -8 pts
    - Monitoring animal: -2 pts
    - Critical active alert: -5 pts
    - High active alert: -3 pts
    - Overdue preventive task: -3 pts
    - Open clinical case: -2 pts
    Bonuses:
    - High compliance (>=85%): +5 pts
    - All animals healthy: +5 pts
    Scale:
    90–100: Excellent
    75–89: Good
    50–74: Attention Required
    25–49: High Risk
    0–24: Critical
    """
    if total_animals == 0:
        return {
            "score": 100,
            "band": "Excellent",
            "summary": "No livestock currently registered in selected scope.",
            "contributing_positive": ["Clean operational slate"],
            "contributing_negative": [],
            "trend": "neutral"
        }

    score = 100.0
    positive_factors = []
    negative_factors = []

    # Penalties
    if critical_count > 0:
        penalty = min(35.0, critical_count * 15.0)
        score -= penalty
        negative_factors.append(f"{critical_count} animal(s) in critical physiological state (-{penalty:.0f} pts)")

    if at_risk_count > 0:
        penalty = min(25.0, at_risk_count * 8.0)
        score -= penalty
        negative_factors.append(f"{at_risk_count} animal(s) exhibiting elevated health risk (-{penalty:.0f} pts)")

    if monitoring_count > 0:
        penalty = min(15.0, monitoring_count * 2.0)
        score -= penalty
        negative_factors.append(f"{monitoring_count} animal(s) under observation for mild variance (-{penalty:.0f} pts)")

    if critical_alerts > 0:
        penalty = min(20.0, critical_alerts * 5.0)
        score -= penalty
        negative_factors.append(f"{critical_alerts} unacknowledged critical alert(s) active (-{penalty:.0f} pts)")

    if high_alerts > 0:
        penalty = min(15.0, high_alerts * 3.0)
        score -= penalty
        negative_factors.append(f"{high_alerts} high-severity active alert(s) (-{penalty:.0f} pts)")

    if overdue_preventive > 0:
        penalty = min(15.0, overdue_preventive * 3.0)
        score -= penalty
        negative_factors.append(f"{overdue_preventive} preventive healthcare action(s) overdue (-{penalty:.0f} pts)")

    if open_cases > 0:
        penalty = min(10.0, open_cases * 2.0)
        score -= penalty
        negative_factors.append(f"{open_cases} open veterinary clinical case(s) ongoing (-{penalty:.0f} pts)")

    # Bonuses
    if preventive_compliance >= 85.0 and overdue_preventive == 0:
        score += 5.0
        positive_factors.append(f"High preventive care compliance ({preventive_compliance:.1f}%) (+5 pts)")

    if critical_count == 0 and at_risk_count == 0:
        score += 3.0
        positive_factors.append("No critical or elevated-risk livestock detected (+3 pts)")

    if devices_online_pct >= 80.0:
        positive_factors.append(f"Strong IoT telemetry coverage ({devices_online_pct:.1f}%)")

    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 90.0:
        band = "Excellent"
        summary = "Herd vitals, preventive care, and telemetry streams are within optimal operating parameters."
        trend = "positive"
    elif score >= 75.0:
        band = "Good"
        summary = "Overall herd health is sound; minor variances or pending tasks require scheduled attention."
        trend = "stable"
    elif score >= 50.0:
        band = "Attention Required"
        summary = "Active alerts, observations, or overdue preventive events warrant proactive herd inspection."
        trend = "warning"
    elif score >= 25.0:
        band = "High Risk"
        summary = "Substantial health risks, unresolved clinical cases, or cluster anomalies detected."
        trend = "negative"
    else:
        band = "Critical"
        summary = "Severe physiological emergencies or critical alert concentration requires immediate veterinary intervention."
        trend = "critical"

    return {
        "score": score,
        "band": band,
        "summary": summary,
        "contributing_positive": positive_factors if positive_factors else ["Baseline vitals maintained"],
        "contributing_negative": negative_factors,
        "trend": trend
    }


def get_health_trends(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    species: Optional[str] = None,
    days: int = 7
) -> dict[str, Any]:
    """
    Time-series physiological analytics aggregated by hour or day.
    Supports 24h (hourly), 7d (daily), 30d (daily), 90d (daily) windows.
    Averages temperature, heart rate, respiration, activity, rumination.
    """
    db = get_database()
    _, _, accessible_animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    match_stage: dict[str, Any] = {
        "$or": [
            {"recorded_at": {"$gte": cutoff}},
            {"timestamp": {"$gte": cutoff}}
        ]
    }

    if animal_id and animal_id != "all":
        # Validate access to this animal
        if role == "farmer" and animal_id not in accessible_animal_ids:
            return {"readings": [], "summary": {}, "empty": True, "message": "Access denied to animal."}
        match_stage["animal_id"] = animal_id
    elif accessible_animal_ids:
        match_stage["animal_id"] = {"$in": accessible_animal_ids}

    # Fetch readings
    cursor = db.health_readings.find(match_stage).sort([("recorded_at", 1), ("timestamp", 1)]).limit(1000)
    raw_readings = list(cursor)

    if not raw_readings:
        return {
            "period_days": days,
            "total_readings": 0,
            "time_series": [],
            "averages": {
                "temperature_c": 0.0,
                "heart_rate_bpm": 0.0,
                "respiratory_rate": 0.0,
                "activity_level": 0.0,
                "rumination_level": 0.0
            },
            "empty": True,
            "message": f"No physiological telemetry recorded in the last {days} days."
        }

    # Bucket grouping in Python for flexibility and handling multiple field aliases
    bucket_format = "%Y-%m-%d %H:00" if days <= 1 else "%Y-%m-%d"
    buckets: dict[str, dict[str, Any]] = {}

    for r in raw_readings:
        dt = r.get("recorded_at") or r.get("timestamp")
        if not dt:
            continue
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                continue

        b_key = dt.strftime(bucket_format)
        if b_key not in buckets:
            buckets[b_key] = {
                "time": b_key,
                "temp_sum": 0.0,
                "temp_cnt": 0,
                "hr_sum": 0.0,
                "hr_cnt": 0,
                "resp_sum": 0.0,
                "resp_cnt": 0,
                "act_sum": 0.0,
                "act_cnt": 0,
                "rum_sum": 0.0,
                "rum_cnt": 0,
            }

        b = buckets[b_key]
        if r.get("temperature_c") is not None:
            b["temp_sum"] += float(r["temperature_c"])
            b["temp_cnt"] += 1
        if r.get("heart_rate_bpm") is not None:
            b["hr_sum"] += float(r["heart_rate_bpm"])
            b["hr_cnt"] += 1
        if r.get("respiratory_rate") is not None:
            b["resp_sum"] += float(r["respiratory_rate"])
            b["resp_cnt"] += 1
        act = r.get("activity_level") if r.get("activity_level") is not None else r.get("activity_percent")
        if act is not None:
            b["act_sum"] += float(act)
            b["act_cnt"] += 1
        rum = r.get("rumination_level") if r.get("rumination_level") is not None else r.get("rumination_percent")
        if rum is not None:
            b["rum_sum"] += float(rum)
            b["rum_cnt"] += 1

    time_series = []
    all_temps, all_hrs, all_resps, all_acts, all_rums = [], [], [], [], []

    for key in sorted(buckets.keys()):
        b = buckets[key]
        t_avg = round(b["temp_sum"] / b["temp_cnt"], 2) if b["temp_cnt"] > 0 else None
        h_avg = round(b["hr_sum"] / b["hr_cnt"], 1) if b["hr_cnt"] > 0 else None
        r_avg = round(b["resp_sum"] / b["resp_cnt"], 1) if b["resp_cnt"] > 0 else None
        a_avg = round(b["act_sum"] / b["act_cnt"], 1) if b["act_cnt"] > 0 else None
        ru_avg = round(b["rum_sum"] / b["rum_cnt"], 1) if b["rum_cnt"] > 0 else None

        if t_avg is not None:
            all_temps.append(t_avg)
        if h_avg is not None:
            all_hrs.append(h_avg)
        if r_avg is not None:
            all_resps.append(r_avg)
        if a_avg is not None:
            all_acts.append(a_avg)
        if ru_avg is not None:
            all_rums.append(ru_avg)

        time_series.append({
            "timestamp": key,
            "time": key,
            "temperature_c": t_avg,
            "heart_rate_bpm": h_avg,
            "respiratory_rate": r_avg,
            "activity_level": a_avg,
            "rumination_level": ru_avg
        })

    averages = {
        "temperature_c": round(sum(all_temps) / len(all_temps), 2) if all_temps else 0.0,
        "heart_rate_bpm": round(sum(all_hrs) / len(all_hrs), 1) if all_hrs else 0.0,
        "respiratory_rate": round(sum(all_resps) / len(all_resps), 1) if all_resps else 0.0,
        "activity_level": round(sum(all_acts) / len(all_acts), 1) if all_acts else 0.0,
        "rumination_level": round(sum(all_rums) / len(all_rums), 1) if all_rums else 0.0,
    }

    return {
        "period_days": days,
        "total_readings": len(raw_readings),
        "time_series": time_series,
        "averages": averages,
        "empty": False,
        "safe_zones": {
            "temperature": {"min": 38.0, "max": 39.5, "unit": "°C"},
            "heart_rate": {"min": 60, "max": 80, "unit": "BPM"},
            "respiratory_rate": {"min": 15, "max": 30, "unit": "/min"},
            "activity": {"min": 40.0, "unit": "%"},
            "rumination": {"min": 50.0, "unit": "%"}
        }
    }


def get_alert_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None,
    days: int = 30
) -> dict[str, Any]:
    """
    Analyze operational alert logs:
    - Total, active, acknowledged, resolved counts
    - Severity breakdown (critical, high, medium, low)
    - Alert type breakdown
    - Time-series trend of alerts
    - Mean Time to Acknowledge (MTTA) and Resolve (MTTR)
    """
    db = get_database()
    _, _, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query: dict[str, Any] = {"created_at": {"$gte": cutoff}}

    if animal_ids:
        query["animal_id"] = {"$in": animal_ids}
    elif role == "farmer":
        query["owner_id"] = user_id

    alerts = list(db.alerts.find(query).sort("created_at", -1))

    total_alerts = len(alerts)
    active_count = 0
    ack_count = 0
    res_count = 0

    severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    type_counts: dict[str, int] = {}
    time_series: dict[str, int] = {}

    mtta_deltas = []
    mttr_deltas = []

    for al in alerts:
        status_val = str(al.get("status", "active")).lower()
        if status_val == "active":
            active_count += 1
        elif status_val == "acknowledged":
            ack_count += 1
        elif status_val == "resolved":
            res_count += 1

        sev = str(al.get("severity", "medium")).lower()
        if sev in severity_dist:
            severity_dist[sev] += 1
        else:
            severity_dist["medium"] += 1

        a_type = al.get("alert_type") or "other"
        type_counts[a_type] = type_counts.get(a_type, 0) + 1

        # Dates for trend
        created_at = al.get("created_at")
        if isinstance(created_at, datetime):
            d_str = created_at.strftime("%Y-%m-%d")
            time_series[d_str] = time_series.get(d_str, 0) + 1

            # MTTA
            ack_at = al.get("acknowledged_at")
            if isinstance(ack_at, datetime) and ack_at >= created_at:
                mtta_deltas.append((ack_at - created_at).total_seconds())

            # MTTR
            res_at = al.get("resolved_at")
            if isinstance(res_at, datetime) and res_at >= created_at:
                mttr_deltas.append((res_at - created_at).total_seconds())

    # Calculate MTTA & MTTR in minutes
    mtta_minutes = round((sum(mtta_deltas) / len(mtta_deltas)) / 60.0, 1) if mtta_deltas else None
    mttr_minutes = round((sum(mttr_deltas) / len(mttr_deltas)) / 60.0, 1) if mttr_deltas else None

    # Sort types by frequency
    sorted_types = sorted([{"type": k, "count": v} for k, v in type_counts.items()], key=lambda x: x["count"], reverse=True)
    sorted_trends = [{"date": k, "count": v} for k, v in sorted(time_series.items())]

    return {
        "period_days": days,
        "total_alerts": total_alerts,
        "active_alerts": active_count,
        "acknowledged_alerts": ack_count,
        "resolved_alerts": res_count,
        "severity_distribution": severity_dist,
        "type_distribution": sorted_types[:10],
        "trends_over_time": sorted_trends,
        "mtta_minutes": mtta_minutes,
        "mttr_minutes": mttr_minutes,
        "mtta_display": f"{mtta_minutes} min" if mtta_minutes is not None else "Insufficient historical data",
        "mttr_display": f"{mttr_minutes} min" if mttr_minutes is not None else "Insufficient historical data",
        "empty": total_alerts == 0
    }


def get_prevention_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Analyze preventive healthcare actions across:
    - Vaccinations, deworming, vet visits/follow-ups, treatments.
    Genuine Preventive Compliance formula:
    Compliance = Completed Actions / (Completed Actions + Overdue Actions) * 100
    Safe handling when denominator is 0: returns 100.0% if overdue == 0, else 0.0%.
    """
    db = get_database()
    _, _, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    query: dict[str, Any] = {}
    if animal_ids:
        query["animal_id"] = {"$in": animal_ids}
    elif role == "farmer":
        query["owner_id"] = user_id

    today = datetime.now(timezone.utc).date()

    # 1. Vaccinations
    vaccs = list(db.vaccinations.find(query))
    # 2. Deworming
    deworms = list(db.deworming.find(query))
    # 3. Vet Visits
    visits = list(db.vet_visits.find(query))
    # 4. Treatments
    treatments = list(db.treatments.find(query))

    def evaluate_schedules(items: list[dict], due_date_key: str, cat_name: str):
        completed = len(items)  # Administered records count as completed events
        due_today = 0
        due_soon = 0
        overdue = 0
        upcoming = 0
        due_items = []

        for item in items:
            due_val = item.get(due_date_key)
            d = _parse_date(due_val)
            if not d:
                continue

            days_diff = (d - today).days
            title = item.get("vaccine_name") or item.get("medicine_name") or f"Vet Follow-up ({item.get('veterinarian_name', 'Dr.')})"
            item_info = {
                "category": cat_name,
                "title": title,
                "animal_id": item.get("animal_id"),
                "due_date": d.isoformat(),
                "days_diff": days_diff
            }

            if days_diff < 0:
                overdue += 1
                item_info["status"] = "overdue"
                due_items.append(item_info)
            elif days_diff == 0:
                due_today += 1
                item_info["status"] = "due_today"
                due_items.append(item_info)
            elif days_diff <= 30:
                due_soon += 1
                item_info["status"] = "due_soon"
                due_items.append(item_info)
            else:
                upcoming += 1
                item_info["status"] = "upcoming"

        return completed, due_today, due_soon, overdue, upcoming, due_items

    v_comp, v_today, v_soon, v_over, v_up, v_items = evaluate_schedules(vaccs, "next_due_date", "Vaccination")
    d_comp, d_today, d_soon, d_over, d_up, d_items = evaluate_schedules(deworms, "next_due_date", "Deworming")
    vs_comp, vs_today, vs_soon, vs_over, vs_up, vs_items = evaluate_schedules(visits, "follow_up_date", "Vet Follow-up")

    t_completed = sum(1 for t in treatments if str(t.get("outcome", "")).lower() in ["completed", "resolved", "success"])
    t_ongoing = len(treatments) - t_completed

    total_completed = v_comp + d_comp + vs_comp + t_completed
    total_due_today = v_today + d_today + vs_today
    total_due_soon = v_soon + d_soon + vs_soon
    total_overdue = v_over + d_over + vs_over
    total_upcoming = v_up + d_up + vs_up

    # Genuine Preventive Compliance Calculation
    denominator = total_completed + total_overdue
    if denominator > 0:
        compliance_rate = round((total_completed / denominator) * 100.0, 1)
    else:
        compliance_rate = 100.0 if total_overdue == 0 else 0.0

    all_due_actions = sorted(v_items + d_items + vs_items, key=lambda x: x["days_diff"])

    return {
        "total_records": len(vaccs) + len(deworms) + len(visits) + len(treatments),
        "completed_count": total_completed,
        "due_today_count": total_due_today,
        "due_soon_count": total_due_soon,
        "overdue_count": total_overdue,
        "upcoming_count": total_upcoming,
        "compliance_rate": compliance_rate,
        "categories": {
            "vaccination": {
                "total": len(vaccs),
                "completed": v_comp,
                "due_today": v_today,
                "due_soon": v_soon,
                "overdue": v_over,
                "compliance": round((v_comp / (v_comp + v_over) * 100.0), 1) if (v_comp + v_over) > 0 else 100.0
            },
            "deworming": {
                "total": len(deworms),
                "completed": d_comp,
                "due_today": d_today,
                "due_soon": d_soon,
                "overdue": d_over,
                "compliance": round((d_comp / (d_comp + d_over) * 100.0), 1) if (d_comp + d_over) > 0 else 100.0
            },
            "veterinary_follow_up": {
                "total": len(visits),
                "completed": vs_comp,
                "due_today": vs_today,
                "due_soon": vs_soon,
                "overdue": vs_over,
                "compliance": round((vs_comp / (vs_comp + vs_over) * 100.0), 1) if (vs_comp + vs_over) > 0 else 100.0
            },
            "treatments": {
                "total": len(treatments),
                "completed": t_completed,
                "ongoing": t_ongoing
            }
        },
        "due_actions": all_due_actions[:20],
        "empty": (len(vaccs) + len(deworms) + len(visits) + len(treatments)) == 0
    }


def get_veterinary_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Clinical case workload, status breakdown, priority distribution,
    average resolution time, and workload per veterinarian.
    Role-aware: Farmers do NOT see private vet workload distribution.
    """
    db = get_database()
    _, _, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    query: dict[str, Any] = {}
    if animal_ids:
        query["animal_id"] = {"$in": animal_ids}
    elif role == "farmer":
        query["owner_id"] = user_id

    cases = list(db.veterinary_cases.find(query).sort("created_at", -1))
    total_cases = len(cases)

    status_counts = {
        "open": 0,
        "assigned": 0,
        "in_review": 0,
        "treatment": 0,
        "follow_up": 0,
        "resolved": 0,
        "closed": 0
    }

    priority_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    }

    type_counts: dict[str, int] = {}
    resolution_times_hours = []
    vet_workload: dict[str, dict[str, Any]] = {}

    for c in cases:
        st = str(c.get("status", "open")).lower()
        if st in status_counts:
            status_counts[st] += 1
        else:
            status_counts["open"] += 1

        pri = str(c.get("priority", "medium")).lower()
        if pri in priority_counts:
            priority_counts[pri] += 1
        else:
            priority_counts["medium"] += 1

        c_type = c.get("case_type") or "general_consultation"
        type_counts[c_type] = type_counts.get(c_type, 0) + 1

        # Resolution Time
        created_at = c.get("created_at")
        closed_at = c.get("closed_at") or (c.get("updated_at") if st in ["resolved", "closed"] else None)
        if isinstance(created_at, datetime) and isinstance(closed_at, datetime) and closed_at >= created_at:
            delta_hrs = (closed_at - created_at).total_seconds() / 3600.0
            resolution_times_hours.append(delta_hrs)

        # Vet Workload (only compiled if vet/admin or assigned)
        v_id = c.get("assigned_veterinarian_id")
        v_name = c.get("assigned_veterinarian_name") or "Unassigned"
        if v_id:
            v_key = str(v_id)
            if v_key not in vet_workload:
                vet_workload[v_key] = {"id": v_key, "name": v_name, "total": 0, "active": 0, "resolved": 0}
            vet_workload[v_key]["total"] += 1
            if st in ["resolved", "closed"]:
                vet_workload[v_key]["resolved"] += 1
            else:
                vet_workload[v_key]["active"] += 1

    open_cases = sum(status_counts[k] for k in ["open", "assigned", "in_review", "treatment", "follow_up"])
    avg_resolution_hours = round(sum(resolution_times_hours) / len(resolution_times_hours), 1) if resolution_times_hours else None

    # Role privacy: farmers should NOT see overall vet workload breakdown
    visible_vet_workload = list(vet_workload.values()) if role in ["veterinarian", "admin"] else []

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "resolved_cases": status_counts["resolved"] + status_counts["closed"],
        "status_distribution": status_counts,
        "priority_distribution": priority_counts,
        "type_distribution": [{"type": k, "count": v} for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)],
        "avg_resolution_hours": avg_resolution_hours,
        "avg_resolution_display": f"{avg_resolution_hours} hrs" if avg_resolution_hours is not None else "Insufficient historical data",
        "vet_workload": visible_vet_workload,
        "empty": total_cases == 0
    }


def get_device_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> dict[str, Any]:
    """
    IoT telemetry & hardware health analytics:
    - Online vs Offline nodes (stale threshold: >30 min heartbeat)
    - Battery distribution
    - Telemetry freshness
    - Animal sensor pairing coverage
    """
    db = get_database()
    animal_query, farm_ids, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    dev_query: dict[str, Any] = {}
    if farm_id and farm_id != "all":
        dev_query["farm_id"] = {"$in": [farm_id, ObjectId(farm_id) if ObjectId.is_valid(farm_id) else farm_id]}
    elif role == "farmer":
        if farm_ids:
            dev_query["farm_id"] = {"$in": farm_ids}

    devices = list(db.devices.find(dev_query))
    total_devices = len(devices)

    now = datetime.now(timezone.utc)
    stale_threshold_seconds = 30 * 60  # 30 minutes

    online_count = 0
    offline_count = 0
    battery_levels = []
    low_battery_count = 0

    device_items = []
    latest_reading_time = None

    for d in devices:
        d_id = d.get("device_id") or str(d.get("_id"))
        status_val = str(d.get("status", "offline")).lower()
        last_seen = d.get("last_seen") or d.get("last_heartbeat")

        is_online = False
        if status_val == "online":
            if isinstance(last_seen, datetime):
                # Check stale threshold
                age = (now - (last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc))).total_seconds()
                if age <= stale_threshold_seconds:
                    is_online = True
                else:
                    is_online = False  # Stale heartbeat
            else:
                is_online = True
        else:
            is_online = False

        if is_online:
            online_count += 1
        else:
            offline_count += 1

        batt = float(d.get("battery_level", 85.0))
        battery_levels.append(batt)
        if batt < 20.0:
            low_battery_count += 1

        device_items.append({
            "device_id": d_id,
            "animal_id": d.get("animal_id"),
            "status": "online" if is_online else "offline",
            "battery_level": batt,
            "last_seen": last_seen.isoformat() if isinstance(last_seen, datetime) else str(last_seen or "")
        })

    # Telemetry Freshness from health_readings
    latest_reading = db.health_readings.find_one(
        {"animal_id": {"$in": animal_ids}} if animal_ids else {},
        sort=[("recorded_at", -1), ("timestamp", -1)]
    )

    freshness_minutes = None
    if latest_reading:
        dt = latest_reading.get("recorded_at") or latest_reading.get("timestamp")
        if isinstance(dt, datetime):
            latest_reading_time = dt.isoformat()
            dt_aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            freshness_minutes = max(0.0, round((now - dt_aware).total_seconds() / 60.0, 1))

    total_animals_count = db.animals.count_documents(animal_query)
    sensor_coverage = round((online_count / total_animals_count * 100.0), 1) if total_animals_count > 0 else 0.0

    return {
        "total_devices": total_devices,
        "online_devices": online_count,
        "offline_devices": offline_count,
        "avg_battery": round(sum(battery_levels) / len(battery_levels), 1) if battery_levels else 0.0,
        "low_battery_count": low_battery_count,
        "sensor_coverage_pct": sensor_coverage,
        "latest_reading_time": latest_reading_time,
        "freshness_minutes": freshness_minutes,
        "freshness_display": f"{freshness_minutes} min ago" if freshness_minutes is not None else "No telemetry received",
        "devices": device_items[:30],
        "empty": total_devices == 0
    }


def get_disease_risk_analytics(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Aggregate AI Disease Intelligence screening signals.
    Decision-support positioning: Screens physiological abnormalities
    without claiming definitive veterinary diagnosis.
    """
    db = get_database()
    animal_query, _, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    animals = list(db.animals.find(animal_query))
    total = len(animals)

    risk_levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    suspected_patterns: dict[str, int] = {}
    early_warnings = {"normal": 0, "watch": 0, "warning": 0, "critical": 0}

    for a in animals:
        aid = str(a["_id"])
        # Check animal status or recent alerts to evaluate risk signals
        st = str(a.get("health_status", "healthy")).lower()
        if st in ["critical"]:
            risk_levels["critical"] += 1
            early_warnings["critical"] += 1
        elif st in ["at_risk", "high"]:
            risk_levels["high"] += 1
            early_warnings["warning"] += 1
        elif st in ["monitoring"]:
            risk_levels["medium"] += 1
            early_warnings["watch"] += 1
        else:
            risk_levels["low"] += 1
            early_warnings["normal"] += 1

    # Extract patterns from active alerts
    alerts = list(db.alerts.find({"animal_id": {"$in": animal_ids}, "status": "active"} if animal_ids else {"status": "active"}))
    for al in alerts:
        a_type = al.get("alert_type", "")
        if "temperature" in a_type:
            suspected_patterns["Fever / Inflammatory Signal"] = suspected_patterns.get("Fever / Inflammatory Signal", 0) + 1
        elif "respiratory" in a_type:
            suspected_patterns["Respiratory Variance Pattern"] = suspected_patterns.get("Respiratory Variance Pattern", 0) + 1
        elif "rumination" in a_type or "activity" in a_type:
            suspected_patterns["Digestive / Rumination Drop Signal"] = suspected_patterns.get("Digestive / Rumination Drop Signal", 0) + 1
        elif "multiple" in a_type:
            suspected_patterns["Multi-System Stress Indication"] = suspected_patterns.get("Multi-System Stress Indication", 0) + 1

    return {
        "total_screened": total,
        "disease_risk_distribution": risk_levels,
        "early_warning_distribution": early_warnings,
        "suspected_patterns": [{"pattern": k, "count": v} for k, v in suspected_patterns.items()],
        "disclaimer": "AI disease-risk signals represent screening decision-support indicators based on physiological telemetry, not definitive clinical diagnoses. Veterinary physical examination is required."
    }


def get_farm_performance(user_id: str, role: str) -> list[dict[str, Any]]:
    """
    Comparative multi-farm operational and health metrics.
    Neutral presentation for farm owners or admins.
    """
    db = get_database()
    if role == "farmer":
        farms = list(db.farms.find({
            "$or": [
                {"owner_id": user_id},
                {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}
            ]
        }))
    else:
        farms = list(db.farms.find())

    comparisons = []
    for f in farms:
        f_id = str(f["_id"])
        alt_id = f.get("farm_id")
        f_name = f.get("name", "Unnamed Farm")
        f_loc = f.get("location", "Not specified")

        # Animal stats
        q = {"$or": [{"farm_id": f_id}, {"farm_id": alt_id}]}
        animals = list(db.animals.find(q))
        a_count = len(animals)

        healthy = sum(1 for a in animals if str(a.get("health_status", "")).lower() in ["healthy", "normal"])
        critical = sum(1 for a in animals if str(a.get("health_status", "")).lower() == "critical")
        at_risk = sum(1 for a in animals if str(a.get("health_status", "")).lower() in ["at_risk", "high"])

        # Alerts
        a_ids = [str(a["_id"]) for a in animals] + [str(a.get("animal_id")) for a in animals if a.get("animal_id")]
        active_alerts = db.alerts.count_documents({"animal_id": {"$in": a_ids}, "status": "active"}) if a_ids else 0

        # Cases
        open_cases = db.veterinary_cases.count_documents({
            "farm_id": {"$in": [f_id, alt_id]},
            "status": {"$in": ["open", "assigned", "in_review", "treatment", "follow_up"]}
        })

        # Calculate HHI for farm
        hhi = get_herd_health_index(
            total_animals=a_count,
            healthy_count=healthy,
            monitoring_count=max(0, a_count - healthy - critical - at_risk),
            at_risk_count=at_risk,
            critical_count=critical,
            critical_alerts=0,
            high_alerts=0,
            active_alerts=active_alerts,
            overdue_preventive=0,
            open_cases=open_cases,
            preventive_compliance=90.0,
            devices_online_pct=85.0
        )

        comparisons.append({
            "farm_id": f_id,
            "farm_name": f_name,
            "location": f_loc,
            "total_animals": a_count,
            "health_index": hhi["score"],
            "health_band": hhi["band"],
            "active_alerts": active_alerts,
            "open_cases": open_cases,
            "critical_animals": critical,
            "at_risk_animals": at_risk
        })

    return comparisons


def get_watchlist(
    user_id: str,
    role: str,
    farm_id: Optional[str] = None
) -> dict[str, list[dict[str, Any]]]:
    """
    Generate targeted operational watchlists:
    - Critical Attention
    - High Risk
    - Under Monitoring
    - Preventive Due
    """
    db = get_database()
    animal_query, _, animal_ids = _get_user_scope_query(db, user_id, role, farm_id)

    animals = list(db.animals.find(animal_query))

    critical_list = []
    high_risk_list = []
    monitoring_list = []
    preventive_due_list = []

    # Get active alerts map
    active_alerts = list(db.alerts.find({"animal_id": {"$in": animal_ids}, "status": "active"} if animal_ids else {"status": "active"}))
    alert_map: dict[str, list[dict]] = {}
    for al in active_alerts:
        aid = al.get("animal_id")
        if aid:
            alert_map.setdefault(aid, []).append(al)

    # Get overdue preventive map
    today = datetime.now(timezone.utc).date()
    preventive_map: dict[str, str] = {}
    for col_name, date_field in [("vaccinations", "next_due_date"), ("deworming", "next_due_date"), ("vet_visits", "follow_up_date")]:
        for rec in db[col_name].find({"animal_id": {"$in": animal_ids}} if animal_ids else {}):
            d = _parse_date(rec.get(date_field))
            if d and d <= today:
                preventive_map[rec.get("animal_id")] = f"{col_name.title()} overdue ({d.isoformat()})"

    for a in animals:
        aid = str(a["_id"])
        tag = a.get("tag_id") or a.get("animal_id") or aid[:8]
        name = a.get("name") or "Unnamed"
        species = a.get("species") or "Cattle"
        st = str(a.get("health_status", "healthy")).lower()

        a_alerts = alert_map.get(aid, []) + alert_map.get(str(a.get("animal_id")), []) + alert_map.get(str(a.get("tag_id")), [])
        prev_note = preventive_map.get(aid) or preventive_map.get(str(a.get("animal_id")))

        item = {
            "id": aid,
            "animal_id": aid,
            "tag_id": tag,
            "name": name,
            "species": species,
            "health_status": st.upper().replace("_", " "),
            "active_alerts_count": len(a_alerts),
            "top_alert": a_alerts[0].get("title") if a_alerts else None,
            "preventive_status": prev_note or "Up to date",
            "reason": prev_note or (a_alerts[0].get("title") if a_alerts else f"Health status: {st.upper()}")
        }

        if st in ["critical"] or any(al.get("severity") == "critical" for al in a_alerts):
            critical_list.append(item)
        elif st in ["at_risk", "high"] or any(al.get("severity") == "high" for al in a_alerts):
            high_risk_list.append(item)
        elif st in ["monitoring"]:
            monitoring_list.append(item)

        if prev_note:
            preventive_due_list.append(item)

    return {
        "critical_attention": critical_list,
        "high_risk": high_risk_list,
        "monitoring": monitoring_list,
        "preventive_due": preventive_due_list
    }

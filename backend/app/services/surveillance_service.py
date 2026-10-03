import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from bson import ObjectId

from app.database import get_database
from app.services.disease_cluster_engine import detect_disease_clusters
from app.services.farm_risk_engine import compute_farm_disease_risk
from app.services.geospatial_service import detect_hotspots, find_nearby_farms, haversine_distance
from app.services.websocket_manager import manager


def ensure_surveillance_indexes():
    """
    Ensure essential MongoDB indexes exist for disease surveillance collections.
    Safe and non-destructive.
    """
    try:
        db = get_database()
        # disease_events indexes
        db.disease_events.create_index("event_number", unique=True, sparse=True)
        db.disease_events.create_index("farm_id")
        db.disease_events.create_index("animal_id")
        db.disease_events.create_index("disease_name")
        db.disease_events.create_index("status")
        db.disease_events.create_index("severity")
        db.disease_events.create_index([("created_at", -1)])
        db.disease_events.create_index("onset_date")

        # disease_observations indexes
        db.disease_observations.create_index("farm_id")
        db.disease_observations.create_index("animal_id")
        db.disease_observations.create_index([("timestamp", -1)])
        db.disease_observations.create_index("indicator")

        # disease_clusters indexes
        db.disease_clusters.create_index("status")
        db.disease_clusters.create_index("risk_score")
        db.disease_clusters.create_index([("first_detected", -1)])

        # farm_risk indexes
        db.farm_risk_profiles.create_index("farm_id", unique=True)
        db.farm_risk_profiles.create_index("risk_score")
        db.farm_risk_profiles.create_index([("updated_at", -1)])
    except Exception:
        pass


def generate_event_number(db) -> str:
    """
    Generate unique human-readable event number: DE-YYYY-XXXX.
    """
    year = datetime.now(timezone.utc).year
    count = db.disease_events.count_documents({})
    candidate_num = count + 1

    while True:
        candidate_str = f"DE-{year}-{candidate_num:04d}"
        if not db.disease_events.find_one({"event_number": candidate_str}):
            return candidate_str
        candidate_num += 1


def serialize_disease_event(item: dict) -> dict[str, Any]:
    """
    Transform MongoDB disease event into JSON-compatible dictionary.
    """
    created_at = item.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")

    updated_at = item.get("updated_at")
    updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at or created_at_str)

    return {
        "id": str(item["_id"]),
        "event_number": item.get("event_number", ""),
        "farm_id": str(item.get("farm_id", "")),
        "farm_name": item.get("farm_name", "Unknown Farm"),
        "animal_id": str(item.get("animal_id")) if item.get("animal_id") else None,
        "animal_tag": item.get("animal_tag"),
        "animal_name": item.get("animal_name"),
        "disease_name": item.get("disease_name", "Unspecified Syndrome"),
        "disease_category": item.get("disease_category", "general"),
        "symptoms": item.get("symptoms", []),
        "observed_signs": item.get("observed_signs", []),
        "severity": item.get("severity", "medium"),
        "confidence": float(item.get("confidence", 0.7)),
        "source": item.get("source", "manual_report"),
        "status": item.get("status", "suspected"),
        "reported_by": item.get("reported_by", "System"),
        "reporter_role": item.get("reporter_role", "user"),
        "veterinarian_id": str(item.get("veterinarian_id")) if item.get("veterinarian_id") else None,
        "veterinarian_name": item.get("veterinarian_name"),
        "veterinary_case_id": str(item.get("veterinary_case_id")) if item.get("veterinary_case_id") else None,
        "onset_date": item.get("onset_date"),
        "investigation_started_at": item.get("investigation_started_at"),
        "investigation_completed_at": item.get("investigation_completed_at"),
        "notes": item.get("notes"),
        "created_at": created_at_str,
        "updated_at": updated_at_str,
    }


def create_disease_event(
    data: dict[str, Any],
    current_user: dict[str, Any],
    db: Any
) -> dict[str, Any]:
    """
    Register a new disease surveillance event and broadcast to WebSocket.
    """
    now = datetime.now(timezone.utc)
    event_num = generate_event_number(db)

    farm_id = str(data["farm_id"])
    farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else None
    if not farm:
        farm = db.farms.find_one({"_id": farm_id})
    farm_name = farm.get("name", "Unknown Farm") if farm else "Unknown Farm"

    animal_id = str(data.get("animal_id")) if data.get("animal_id") else None
    animal_tag = None
    animal_name = None
    if animal_id:
        animal = db.animals.find_one({"_id": ObjectId(animal_id)}) if ObjectId.is_valid(animal_id) else None
        if not animal:
            animal = db.animals.find_one({"_id": animal_id})
        if animal:
            animal_tag = animal.get("tag_id")
            animal_name = animal.get("name")

    doc = {
        "event_number": event_num,
        "farm_id": farm_id,
        "farm_name": farm_name,
        "animal_id": animal_id,
        "animal_tag": animal_tag,
        "animal_name": animal_name,
        "disease_name": data["disease_name"],
        "disease_category": data.get("disease_category", "general"),
        "symptoms": data.get("symptoms", []),
        "observed_signs": data.get("observed_signs", []),
        "severity": data.get("severity", "medium"),
        "confidence": float(data.get("confidence", 0.7)),
        "source": data.get("source", "manual_report"),
        "status": "suspected",
        "reported_by": current_user.get("sub") or current_user.get("username", "Unknown"),
        "reporter_role": current_user.get("role", "farmer"),
        "veterinarian_id": None,
        "veterinarian_name": None,
        "veterinary_case_id": None,
        "onset_date": data.get("onset_date") or now.strftime("%Y-%m-%d"),
        "investigation_started_at": None,
        "investigation_completed_at": None,
        "notes": data.get("notes"),
        "created_at": now,
        "updated_at": now,
    }

    result = db.disease_events.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Broadcast via WebSocket (safe async dispatch if event loop is active)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "surveillance_event",
                "action": "created",
                "event_number": event_num,
                "farm_name": farm_name,
                "disease_name": data["disease_name"],
                "severity": data.get("severity", "medium")
            }))
    except Exception:
        pass

    return serialize_disease_event(doc)


def update_disease_event(
    event_id: str,
    update_data: dict[str, Any],
    current_user: dict[str, Any],
    db: Any
) -> Optional[dict[str, Any]]:
    """
    Update a disease event (status, severity, notes, linked vet case, etc.)
    """
    now = datetime.now(timezone.utc)
    query = {"_id": ObjectId(event_id)} if ObjectId.is_valid(event_id) else {"_id": event_id}
    existing = db.disease_events.find_one(query)
    if not existing:
        return None

    update_fields = {"updated_at": now}
    for k, v in update_data.items():
        if v is not None:
            update_fields[k] = v

    if update_data.get("status") == "under_investigation" and not existing.get("investigation_started_at"):
        update_fields["investigation_started_at"] = now.isoformat()
    elif update_data.get("status") in ["confirmed", "ruled_out", "resolved"] and not existing.get("investigation_completed_at"):
        update_fields["investigation_completed_at"] = now.isoformat()

    db.disease_events.update_one(query, {"$set": update_fields})
    updated = db.disease_events.find_one(query)

    # Broadcast via WebSocket
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({
                "type": "surveillance_event",
                "action": "updated",
                "event_number": updated.get("event_number"),
                "status": updated.get("status")
            }))
    except Exception:
        pass

    return serialize_disease_event(updated)


def get_disease_event(event_id: str, db: Any) -> Optional[dict[str, Any]]:
    query = {"_id": ObjectId(event_id)} if ObjectId.is_valid(event_id) else {"_id": event_id}
    item = db.disease_events.find_one(query)
    if not item and not ObjectId.is_valid(event_id):
        item = db.disease_events.find_one({"event_number": event_id})
    return serialize_disease_event(item) if item else None


def list_disease_events(
    db: Any,
    farm_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if farm_id:
        query["farm_id"] = farm_id
    if status:
        query["status"] = status

    cursor = db.disease_events.find(query).sort("created_at", -1).limit(limit)
    return [serialize_disease_event(doc) for doc in cursor]


def extract_disease_observations(
    db: Any,
    farm_id: Optional[str] = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    """
    Extract dynamic disease observations from existing health readings & alerts
    without duplicating raw telemetry.
    """
    query: dict[str, Any] = {
        "$or": [
            {"status": {"$in": ["abnormal", "critical"]}},
            {"alert_triggered": True},
            {"temperature_c": {"$gte": 39.5}},
            {"temperature_c": {"$lt": 37.0}},
            {"respiratory_rate": {"$gte": 38}}
        ]
    }
    if farm_id:
        query["farm_id"] = farm_id

    readings = list(db.health_readings.find(query).sort("timestamp", -1).limit(limit))

    # Fetch animals map
    animal_ids = list(set(r.get("animal_id") for r in readings if r.get("animal_id")))
    animals = list(db.animals.find({"_id": {"$in": [ObjectId(a) for a in animal_ids if ObjectId.is_valid(a)]}}))
    animal_map = {str(a["_id"]): a for a in animals}

    farms = list(db.farms.find({}))
    farm_map = {str(f["_id"]): f.get("name", "Holding") for f in farms}

    observations = []
    for r in readings:
        aid = str(r.get("animal_id"))
        animal = animal_map.get(aid, {})
        fid = str(r.get("farm_id") or animal.get("farm_id", ""))
        ts = r.get("timestamp")
        ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts or "")

        temp = r.get("temperature_c", 38.5)
        resp = r.get("respiratory_rate", 24)
        rum = r.get("rumination_level", 450)

        indicator = "Temperature Anomaly"
        val = f"{temp:.1f} °C"
        ref = "38.0 - 39.3 °C"
        sev = "medium"

        if temp >= 40.5:
            indicator = "Critically Elevated Core Temp (Fever)"
            sev = "critical"
        elif temp >= 39.5:
            indicator = "Hyperthermia / Febrile Indicator"
            sev = "high"
        elif resp >= 40:
            indicator = "Tachypnea / Respiratory Stress"
            val = f"{resp:.0f} bpm"
            ref = "15 - 35 bpm"
            sev = "high"
        elif rum < 300:
            indicator = "Rumination Depression"
            val = f"{rum:.0f} min/day"
            ref = "400 - 600 min/day"
            sev = "medium"

        observations.append({
            "id": str(r["_id"]),
            "animal_id": aid,
            "animal_tag": animal.get("tag_id") or aid[:6],
            "animal_name": animal.get("name"),
            "farm_id": fid,
            "farm_name": farm_map.get(fid, "Holding"),
            "timestamp": ts_str,
            "indicator": indicator,
            "value": val,
            "threshold_or_reference": ref,
            "severity": sev,
            "source": "health_telemetry",
            "confidence": 0.88
        })

    return observations


def get_farm_risk_profiles(
    db: Any,
    current_user: dict[str, Any],
    window_days: int = 7
) -> list[dict[str, Any]]:
    """
    Compute and return farm risk profiles adhering to RBAC.
    """
    user_role = current_user.get("role")
    user_id = current_user.get("sub")

    if user_role == "farmer":
        query = {"$or": [{"owner_id": user_id}, {"owner_id": ObjectId(user_id)}]} if ObjectId.is_valid(user_id) else {"owner_id": user_id}
        farms = list(db.farms.find(query))
    else:
        farms = list(db.farms.find({}))

    profiles = []
    for farm in farms:
        profile = compute_farm_disease_risk(farm, db, window_days=window_days)
        profiles.append(profile)

    profiles.sort(key=lambda x: x["risk_score"], reverse=True)
    return profiles


def get_surveillance_overview(
    db: Any,
    current_user: dict[str, Any],
    window_days: int = 7
) -> dict[str, Any]:
    """
    Top-level KPI summary for Surveillance Command Center.
    """
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    clusters = detect_disease_clusters(profiles, db, window_days=window_days)
    hotspots = detect_hotspots(profiles, max_radius_km=30.0)

    farms_count = len(profiles)
    animals_count = sum(p.get("total_animals", 0) for p in profiles)
    high_risk_farms = sum(1 for p in profiles if p.get("risk_category") in ["HIGH", "CRITICAL"])

    event_query = {"status": {"$in": ["suspected", "under_investigation"]}}
    if current_user.get("role") == "farmer":
        farm_ids = [p["farm_id"] for p in profiles]
        event_query["farm_id"] = {"$in": farm_ids}
    active_events = db.disease_events.count_documents(event_query)

    if high_risk_farms > 0 or len(clusters) > 0:
        surv_status = "ELEVATED_SURVEILLANCE"
        advisory = (
            f"{high_risk_farms} farm(s) show elevated surveillance risk with {len(clusters)} potential cluster(s). "
            "Veterinary field investigation prioritized."
        )
    else:
        surv_status = "ROUTINE_MONITORING"
        advisory = "No significant surveillance escalation detected across monitored holdings."

    now = datetime.now(timezone.utc)
    return {
        "farms_monitored": farms_count,
        "animals_monitored": animals_count,
        "high_risk_farms_count": high_risk_farms,
        "active_events_count": active_events,
        "potential_clusters_count": len(clusters),
        "geographic_hotspots_count": len(hotspots),
        "surveillance_status": surv_status,
        "advisory": advisory,
        "clinical_safety_notice": (
            "VETRA Surveillance tracks statistical physiological clustering and risk patterns. "
            "Official epidemiological confirmation requires licensed veterinary pathology review."
        ),
        "generated_at": now.isoformat()
    }


def get_surveillance_watchlist(
    db: Any,
    current_user: dict[str, Any],
    window_days: int = 7
) -> list[dict[str, Any]]:
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    watchlist = []
    for p in profiles:
        action = "Routine Monitoring"
        if p["risk_category"] == "CRITICAL":
            action = "Emergency veterinary inspection; quarantine symptomatic livestock."
        elif p["risk_category"] == "HIGH":
            action = "Dispatch field veterinarian; check thermal and respiratory vitals."
        elif p["risk_category"] == "MODERATE":
            action = "Increase telemetry logging; inspect water troughs and feed."

        watchlist.append({
            "farm_id": p["farm_id"],
            "farm_name": p["farm_name"],
            "location": p["location"],
            "risk_score": p["risk_score"],
            "risk_category": p["risk_category"],
            "affected_animals": p["affected_animals_count"],
            "active_alerts": p["active_alerts_count"],
            "dominant_pattern": p["dominant_disease_pattern"],
            "last_signal": p.get("trend", "stable").capitalize(),
            "recommended_action": action
        })

    return watchlist


def get_surveillance_risk_map(
    db: Any,
    current_user: dict[str, Any],
    window_days: int = 7
) -> list[dict[str, Any]]:
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    map_items = []

    for p in profiles:
        has_coords = p.get("latitude") is not None and p.get("longitude") is not None
        cat = p.get("risk_category", "LOW")
        color = "#10B981"  # green
        if cat == "CRITICAL":
            color = "#EF4444"  # red
        elif cat == "HIGH":
            color = "#F97316"  # orange
        elif cat == "MODERATE":
            color = "#FBBF24"  # amber

        map_items.append({
            "farm_id": p["farm_id"],
            "farm_name": p["farm_name"],
            "location": p["location"],
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "has_coordinates": has_coords,
            "risk_score": p["risk_score"],
            "risk_category": cat,
            "affected_animals": p["affected_animals_count"],
            "active_alerts": p["active_alerts_count"],
            "status_color": color
        })

    return map_items


def get_regional_surveillance(
    db: Any,
    current_user: dict[str, Any],
    window_days: int = 7
) -> list[dict[str, Any]]:
    """
    Regional aggregation by district or state.
    """
    profiles = get_farm_risk_profiles(db, current_user, window_days=window_days)
    clusters = detect_disease_clusters(profiles, db, window_days=window_days)

    region_map: dict[str, list[dict]] = {}
    for p in profiles:
        key = p.get("district") or p.get("state") or "Unspecified District"
        region_map.setdefault(key, []).append(p)

    regions = []
    for reg_key, farm_list in region_map.items():
        farms_count = len(farm_list)
        animals_count = sum(f.get("total_animals", 0) for f in farm_list)
        high_risk_count = sum(1 for f in farm_list if f.get("risk_category") in ["HIGH", "CRITICAL"])
        alerts_count = sum(f.get("active_alerts_count", 0) for f in farm_list)
        events_count = sum(f.get("active_disease_events_count", 0) for f in farm_list)
        avg_risk = sum(f.get("risk_score", 0.0) for f in farm_list) / farms_count if farms_count > 0 else 0.0

        # Patterns in region
        patterns = [f.get("dominant_disease_pattern") for f in farm_list if f.get("dominant_disease_pattern") and f.get("dominant_disease_pattern") != "Normal / Baseline"]

        # Clusters involving farms in this region
        fids = set(f["farm_id"] for f in farm_list)
        reg_clusters = [c for c in clusters if any(fid in fids for fid in c.get("farm_ids", []))]

        surv_level = "ROUTINE"
        if avg_risk >= 50.0 or high_risk_count > 0 or len(reg_clusters) > 0:
            surv_level = "ELEVATED"
        if avg_risk >= 75.0:
            surv_level = "URGENT"

        regions.append({
            "region_key": reg_key,
            "farms_count": farms_count,
            "animals_count": animals_count,
            "high_risk_farms_count": high_risk_count,
            "active_alerts_count": alerts_count,
            "active_disease_events_count": events_count,
            "active_clusters_count": len(reg_clusters),
            "average_risk_score": round(avg_risk, 1),
            "surveillance_level": surv_level,
            "dominant_patterns": list(set(patterns)) if patterns else ["Baseline"],
            "trend": "stable" if avg_risk < 50 else "monitoring"
        })

    regions.sort(key=lambda x: x["average_risk_score"], reverse=True)
    return regions


def _normalize_dt(dt: Any) -> Optional[datetime]:
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def get_surveillance_trends(
    db: Any,
    current_user: dict[str, Any],
    period_days: int = 30
) -> dict[str, Any]:
    """
    Calculate day-by-day surveillance trends across the requested period (max 90 days).
    """
    period_days = min(max(period_days, 1), 90)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = now_naive - timedelta(days=period_days)

    # Fetch readings in this bounded window
    readings = list(db.health_readings.find(
        {"timestamp": {"$gte": start_date}},
        {"timestamp": 1, "status": 1, "alert_triggered": 1, "farm_id": 1, "animal_id": 1}
    ).limit(2000))

    # Fetch alerts created in window
    alerts = list(db.alerts.find(
        {"created_at": {"$gte": start_date}},
        {"created_at": 1, "farm_id": 1}
    ).limit(500))

    # Fetch vet cases created in window
    cases = list(db.veterinary_cases.find(
        {"created_at": {"$gte": start_date}},
        {"created_at": 1, "farm_id": 1}
    ).limit(500))

    # Group by day
    time_series = []
    total_obs = 0
    total_aff_animals = set()
    total_aff_farms = set()

    for d in range(period_days):
        day_start = (start_date + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_str = day_start.strftime("%Y-%m-%d")

        day_readings = [
            r for r in readings
            if _normalize_dt(r.get("timestamp")) and day_start <= _normalize_dt(r.get("timestamp")) < day_end
        ]
        abnormal_day = [
            r for r in day_readings
            if r.get("status") in ["abnormal", "critical"] or r.get("alert_triggered") is True
        ]

        day_alerts = [
            a for a in alerts
            if _normalize_dt(a.get("created_at")) and day_start <= _normalize_dt(a.get("created_at")) < day_end
        ]
        day_cases = [
            c for c in cases
            if _normalize_dt(c.get("created_at")) and day_start <= _normalize_dt(c.get("created_at")) < day_end
        ]


        aff_animals = set(str(r["animal_id"]) for r in abnormal_day if r.get("animal_id"))
        aff_farms = set(str(r["farm_id"]) for r in abnormal_day if r.get("farm_id"))

        total_obs += len(abnormal_day)
        total_aff_animals.update(aff_animals)
        total_aff_farms.update(aff_farms)

        avg_risk = round(min(15.0 + (len(aff_animals) * 12.0) + (len(day_alerts) * 5.0), 95.0), 1)

        time_series.append({
            "date": day_str,
            "observation_count": len(abnormal_day),
            "affected_animals": len(aff_animals),
            "affected_farms": len(aff_farms),
            "average_risk_score": avg_risk,
            "alert_count": len(day_alerts),
            "case_count": len(day_cases)
        })

    summary = {
        "total_observations": total_obs,
        "total_affected_animals": len(total_aff_animals),
        "total_affected_farms": len(total_aff_farms),
        "period_days": period_days
    }

    return {
        "period_days": period_days,
        "time_series": time_series,
        "summary": summary
    }


def trigger_surveillance_analysis(
    farm_id: Optional[str],
    current_user: dict[str, Any],
    db: Any
) -> dict[str, Any]:
    """
    Recompute surveillance profiles and generate an AI-backed clinical narrative.
    """
    from ai_engine.disease_intelligence import generate_surveillance_explanation

    profiles = get_farm_risk_profiles(db, current_user)
    if farm_id:
        target_profile = next((p for p in profiles if p["farm_id"] == farm_id), None)
        if not target_profile:
            farm = db.farms.find_one({"_id": ObjectId(farm_id)}) if ObjectId.is_valid(farm_id) else db.farms.find_one({"_id": farm_id})
            target_profile = compute_farm_disease_risk(farm or {"_id": farm_id, "name": "Holding"}, db)
    else:
        target_profile = profiles[0] if profiles else {
            "farm_name": "Aggregated Holdings",
            "risk_score": 12.0,
            "risk_category": "LOW",
            "total_animals": 0,
            "affected_animals_count": 0,
            "dominant_disease_pattern": "Baseline",
            "contributing_factors": ["System nominal."]
        }

    clusters = detect_disease_clusters(profiles, db)
    observations = extract_disease_observations(db, farm_id=farm_id, limit=20)
    explanation = generate_surveillance_explanation(target_profile, clusters, observations)

    return {
        "target_farm": target_profile,
        "clusters_detected": clusters,
        "ai_explanation": explanation,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

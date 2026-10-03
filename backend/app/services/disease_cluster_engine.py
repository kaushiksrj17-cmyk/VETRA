from datetime import datetime, timedelta, timezone
from typing import Any
from bson import ObjectId

from app.services.geospatial_service import haversine_distance


CLINICAL_SAFETY_DISCLAIMER = (
    "Decision Support Only: Potential statistical cluster. "
    "Requires authorized veterinary confirmation before declaring outbreak. "
    "No confirmed outbreak."
)


def detect_disease_clusters(
    farm_profiles: list[dict[str, Any]],
    db: Any,
    window_days: int = 7
) -> list[dict[str, Any]]:
    """
    Detect statistical disease clusters across monitored holdings.

    Detects:
    1. Intra-Farm Clusters:
       >= 2 animals in the same holding demonstrating correlated physiological anomalies
       or similar disease events within the surveillance window.
    2. Cross-Farm Proximity Clusters:
       >= 2 holdings within 25 km (or same district) with elevated risk scores
       and matching clinical/syndromic patterns.

    Safety:
    Adheres strictly to clinical decision-support rules. Clusters are always flagged
    as 'Potential Cluster' or 'Elevated Surveillance Cluster' and require licensed
    veterinary confirmation.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    clusters = []
    cluster_counter = 1

    # -------------------------------------------------------------
    # 1. Intra-Farm Clustering
    # -------------------------------------------------------------
    for profile in farm_profiles:
        farm_id = profile["farm_id"]
        farm_name = profile["farm_name"]
        affected_count = profile.get("affected_animals_count", 0)
        dominant_pattern = profile.get("dominant_disease_pattern", "Normal")

        # Check if >= 2 animals are affected with an abnormal pattern
        if affected_count >= 2 and dominant_pattern not in ["Normal", "Normal / Baseline"]:
            # Retrieve recent abnormal readings or alerts for these animals
            animals = list(db.animals.find({"farm_id": farm_id}))
            if not animals and ObjectId.is_valid(farm_id):
                animals = list(db.animals.find({"farm_id": ObjectId(farm_id)}))

            animal_map = {str(a["_id"]): a.get("tag_id") or a.get("name") or "Unknown" for a in animals}
            animal_ids = list(animal_map.keys())

            query = {
                "animal_id": {"$in": animal_ids},
                "timestamp": {"$gte": cutoff},
                "$or": [
                    {"status": {"$in": ["abnormal", "critical"]}},
                    {"alert_triggered": True},
                    {"temperature_c": {"$gte": 39.5}},
                    {"respiratory_rate": {"$gte": 38}}
                ]
            }
            abnormal_readings = list(db.health_readings.find(query).sort("timestamp", 1))

            obs_count = len(abnormal_readings)
            first_detected = (
                abnormal_readings[0]["timestamp"].isoformat()
                if abnormal_readings and isinstance(abnormal_readings[0]["timestamp"], datetime)
                else cutoff.isoformat()
            )
            last_detected = (
                abnormal_readings[-1]["timestamp"].isoformat()
                if abnormal_readings and isinstance(abnormal_readings[-1]["timestamp"], datetime)
                else now.isoformat()
            )

            distinct_affected = list(set(str(r["animal_id"]) for r in abnormal_readings))
            affected_tags = [animal_map.get(aid, aid) for aid in distinct_affected]

            cluster_risk = min(profile.get("risk_score", 40.0) + 10.0, 95.0)

            clusters.append({
                "cluster_id": f"CLUSTER-{now.year}-{cluster_counter:03d}",
                "title": f"Potential Intra-Farm Cluster: {dominant_pattern}",
                "disease_pattern": dominant_pattern,
                "farm_ids": [farm_id],
                "farm_names": [farm_name],
                "animal_ids": distinct_affected,
                "animal_tags": affected_tags,
                "observation_count": max(obs_count, len(distinct_affected)),
                "affected_animal_count": len(distinct_affected),
                "first_detected": first_detected,
                "last_detected": last_detected,
                "geographic_spread": "Single Holding (Intra-farm)",
                "risk_score": round(cluster_risk, 1),
                "confidence": round(min(0.70 + (len(distinct_affected) * 0.05), 0.92), 2),
                "status": "under_investigation" if cluster_risk >= 60 else "monitoring",
                "recommended_action": (
                    f"Initiate veterinary physical examination of {len(distinct_affected)} affected animals "
                    f"on {farm_name}. Implement syndromic isolation pending clinical evaluation."
                ),
                "contributing_factors": [
                    f"{len(distinct_affected)} animals displaying synchronous {dominant_pattern} indicators.",
                    f"Holding risk level is currently {profile.get('risk_category', 'MODERATE')}."
                ],
                "clinical_disclaimer": CLINICAL_SAFETY_DISCLAIMER
            })
            cluster_counter += 1

    # -------------------------------------------------------------
    # 2. Cross-Farm Geospatial Clustering
    # -------------------------------------------------------------
    elevated_farms = [
        p for p in farm_profiles
        if p.get("risk_category") in ["MODERATE", "HIGH", "CRITICAL"]
        and p.get("dominant_disease_pattern") not in ["Normal", "Normal / Baseline"]
    ]

    for i, lead in enumerate(elevated_farms):
        lead_lat = lead.get("latitude")
        lead_lon = lead.get("longitude")
        lead_pattern = lead.get("dominant_disease_pattern")
        lead_dist = lead.get("district")

        matched_farms = [lead]
        for other in elevated_farms[i + 1:]:
            other_lat = other.get("latitude")
            other_lon = other.get("longitude")
            other_pattern = other.get("dominant_disease_pattern")
            other_dist = other.get("district")

            is_pattern_similar = (
                lead_pattern == other_pattern
                or ("Thermal" in str(lead_pattern) and "Thermal" in str(other_pattern))
                or ("Respiratory" in str(lead_pattern) and "Respiratory" in str(other_pattern))
            )

            if not is_pattern_similar:
                continue

            # Check geographic proximity if coordinates exist
            is_proximate = False
            spread_desc = "Regional Association"
            if lead_lat is not None and lead_lon is not None and other_lat is not None and other_lon is not None:
                dist = haversine_distance(lead_lat, lead_lon, other_lat, other_lon)
                if dist is not None and dist <= 25.0:
                    is_proximate = True
                    spread_desc = f"Localized ({dist:.1f} km)"
            elif lead_dist and other_dist and lead_dist.lower() == other_dist.lower():
                is_proximate = True
                spread_desc = f"District-level ({lead_dist})"

            if is_proximate:
                matched_farms.append(other)

        if len(matched_farms) >= 2:
            fids = [f["farm_id"] for f in matched_farms]
            fnames = [f["farm_name"] for f in matched_farms]
            tot_affected = sum(f.get("affected_animals_count", 0) for f in matched_farms)
            avg_risk = sum(f.get("risk_score", 0.0) for f in matched_farms) / len(matched_farms)

            clusters.append({
                "cluster_id": f"CLUSTER-{now.year}-{cluster_counter:03d}",
                "title": f"Potential Multi-Farm Cluster: {lead_pattern}",
                "disease_pattern": lead_pattern or "Mixed Syndromic Pattern",
                "farm_ids": fids,
                "farm_names": fnames,
                "animal_ids": [],
                "animal_tags": [],
                "observation_count": tot_affected * 2,
                "affected_animal_count": tot_affected,
                "first_detected": cutoff.isoformat(),
                "last_detected": now.isoformat(),
                "geographic_spread": spread_desc,
                "risk_score": round(min(avg_risk + 12.0, 95.0), 1),
                "confidence": 0.82,
                "status": "under_investigation",
                "recommended_action": (
                    f"Coordinate cross-holding veterinary surveillance across {len(fnames)} farms ({', '.join(fnames)}). "
                    f"Audit biosecurity and livestock movements between holdings."
                ),
                "contributing_factors": [
                    f"{len(matched_farms)} proximate holdings demonstrating matching {lead_pattern} patterns.",
                    f"Geographic proximity or shared district indicates potential surveillance relationship."
                ],
                "clinical_disclaimer": CLINICAL_SAFETY_DISCLAIMER
            })
            cluster_counter += 1

    return clusters

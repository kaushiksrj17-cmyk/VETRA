import math
from typing import Any, Optional


EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float]
) -> Optional[float]:
    """
    Calculate the great-circle distance between two points on Earth (in km)
    using the Haversine formula.

    Returns None if any coordinate is missing or invalid.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    try:
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = EARTH_RADIUS_KM * c
        return round(distance, 2)
    except (ValueError, TypeError):
        return None


def find_nearby_farms(
    target_farm_id: str,
    farms: list[dict[str, Any]],
    max_distance_km: float = 25.0
) -> list[dict[str, Any]]:
    """
    Find farms geographically close to the target farm within max_distance_km.
    Farms without valid coordinates are safely omitted.
    """
    target = next((f for f in farms if str(f.get("_id") or f.get("id")) == target_farm_id), None)
    if not target:
        return []

    target_lat = target.get("latitude")
    target_lon = target.get("longitude")

    if target_lat is None or target_lon is None:
        return []

    nearby = []
    for farm in farms:
        fid = str(farm.get("_id") or farm.get("id"))
        if fid == target_farm_id:
            continue

        lat = farm.get("latitude")
        lon = farm.get("longitude")
        if lat is None or lon is None:
            continue

        dist = haversine_distance(target_lat, target_lon, lat, lon)
        if dist is not None and dist <= max_distance_km:
            nearby.append({
                "farm_id": fid,
                "farm_name": farm.get("name", "Unknown Farm"),
                "distance_km": dist,
                "latitude": lat,
                "longitude": lon,
                "district": farm.get("district"),
                "state": farm.get("state")
            })

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby


def detect_hotspots(
    farm_profiles: list[dict[str, Any]],
    max_radius_km: float = 30.0,
    min_farms_per_hotspot: int = 1
) -> list[dict[str, Any]]:
    """
    Identify geographic disease hotspots from elevated-risk farms.

    Rules:
    - Only farms with verified coordinates and elevated risk (score >= 50 or HIGH/CRITICAL)
      are considered candidates.
    - If coordinates are unavailable, returns an empty list (NEVER fabricates coordinates).
    - Clusters candidate farms within max_radius_km of each other.
    """
    candidates = [
        f for f in farm_profiles
        if f.get("latitude") is not None
        and f.get("longitude") is not None
        and (f.get("risk_score", 0) >= 45 or f.get("risk_category") in ["HIGH", "CRITICAL"])
    ]

    if not candidates:
        return []

    visited = set()
    hotspots = []
    hotspot_counter = 1

    for i, lead_farm in enumerate(candidates):
        lead_id = lead_farm.get("farm_id")
        if lead_id in visited:
            continue

        cluster_farms = [lead_farm]
        visited.add(lead_id)

        for other_farm in candidates[i + 1:]:
            other_id = other_farm.get("farm_id")
            if other_id in visited:
                continue

            dist = haversine_distance(
                lead_farm["latitude"], lead_farm["longitude"],
                other_farm["latitude"], other_farm["longitude"]
            )
            if dist is not None and dist <= max_radius_km:
                cluster_farms.append(other_farm)
                visited.add(other_id)

        if len(cluster_farms) >= min_farms_per_hotspot:
            # Calculate centroid
            avg_lat = sum(f["latitude"] for f in cluster_farms) / len(cluster_farms)
            avg_lon = sum(f["longitude"] for f in cluster_farms) / len(cluster_farms)

            # Max spread radius
            radii = [
                haversine_distance(avg_lat, avg_lon, f["latitude"], f["longitude"]) or 0.0
                for f in cluster_farms
            ]
            radius = max(radii) if radii else 5.0
            radius = max(radius, 5.0)  # Min visual radius 5 km

            total_affected_animals = sum(f.get("affected_animals_count", 0) for f in cluster_farms)
            avg_risk = sum(f.get("risk_score", 0.0) for f in cluster_farms) / len(cluster_farms)

            # Dominant pattern
            patterns = [f.get("dominant_disease_pattern") for f in cluster_farms if f.get("dominant_disease_pattern")]
            dominant_pattern = max(set(patterns), key=patterns.count) if patterns else "Mixed Physiological Anomaly"

            hotspots.append({
                "hotspot_id": f"HOTSPOT-{hotspot_counter:03d}",
                "center_latitude": round(avg_lat, 5),
                "center_longitude": round(avg_lon, 5),
                "radius_km": round(radius, 1),
                "affected_farm_ids": [f["farm_id"] for f in cluster_farms],
                "affected_farm_names": [f["farm_name"] for f in cluster_farms],
                "affected_animal_count": total_affected_animals,
                "risk_score": round(avg_risk, 1),
                "dominant_disease_pattern": dominant_pattern,
                "confidence": round(min(0.65 + (len(cluster_farms) * 0.1), 0.95), 2),
                "status": "active" if avg_risk >= 50 else "monitored",
                "recommendation": (
                    f"Prioritize veterinary field surveillance within {round(radius, 1)} km radius. "
                    f"Inspect {len(cluster_farms)} associated holdings for syndromic signs."
                )
            })
            hotspot_counter += 1

    return hotspots

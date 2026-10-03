from datetime import datetime, timezone
import sys
from pathlib import Path
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

# Ensure root workspace directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai_engine.health_analyzer import analyze_animal_health
from app.database import get_database
from app.permissions import require_any_authenticated_user


router = APIRouter(
    prefix="/ai",
    tags=["AI Health Intelligence"]
)


@router.get(
    "/health-assessment/{animal_id}",
    status_code=status.HTTP_200_OK
)
def get_animal_ai_assessment(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Run the VETRA AI Health Intelligence pipeline on recent telemetry readings
    for a specific animal and return a structured decision-support report.
    """
    db = get_database()
    user_id = current_user["sub"]
    user_role = current_user.get("role")

    if not ObjectId.is_valid(animal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid animal ID format."
        )

    animal = db.animals.find_one({"_id": ObjectId(animal_id)})
    if not animal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found."
        )

    # Farmers can only access assessments for their own animals
    if user_role == "farmer" and animal.get("owner_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or access denied."
        )

    # Fetch up to 50 recent health readings
    readings_cursor = db.health_readings.find(
        {"animal_id": animal_id}
    ).sort("recorded_at", -1).limit(50)

    readings = list(readings_cursor)

    animal_dict = {
        "id": str(animal["_id"]),
        "tag_id": animal.get("tag_id"),
        "name": animal.get("name"),
        "species": animal.get("species"),
        "breed": animal.get("breed"),
        "gender": animal.get("gender"),
        "health_status": animal.get("health_status", "healthy")
    }

    # Run AI pipeline
    report = analyze_animal_health(animal_dict, readings)
    report["timestamp"] = datetime.now(timezone.utc).isoformat()

    return report


@router.get(
    "/surveillance",
    status_code=status.HTTP_200_OK
)
def get_herd_risk_surveillance(
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Compute population-level risk surveillance metrics across monitored livestock.
    Evaluates abnormality clusters and signals without claiming epidemiological certainty.
    """
    db = get_database()
    user_id = current_user["sub"]
    user_role = current_user.get("role")

    query = {}
    if user_role == "farmer":
        query["owner_id"] = user_id

    total_animals = db.animals.count_documents(query)
    healthy_count = db.animals.count_documents({**query, "health_status": "healthy"})
    monitoring_count = db.animals.count_documents({**query, "health_status": "monitoring"})
    at_risk_count = db.animals.count_documents({**query, "health_status": "at_risk"})
    critical_count = db.animals.count_documents({**query, "health_status": "critical"})

    # Check alert concentrations
    active_alerts = db.alerts.count_documents({**query, "status": "active"})
    critical_alerts = db.alerts.count_documents({**query, "status": "active", "severity": "critical"})

    # Evaluate surveillance signal
    if critical_alerts >= 3 or critical_count >= 2:
        signal = "High Risk Concentration"
        level = "elevated"
        advisory = "Multiple critical physiological anomalies detected. Herd-level veterinary walk-through advised."
    elif active_alerts >= 2 or at_risk_count >= 1:
        signal = "Localized Abnormality Signal"
        level = "moderate"
        advisory = "Isolated physiological variance detected. Maintain increased monitoring frequency."
    else:
        signal = "Baseline Normal"
        level = "normal"
        advisory = "Herd parameters are consistent with expected physiological reference values."

    return {
        "surveillance_signal": signal,
        "risk_level": level,
        "advisory": advisory,
        "total_animals": total_animals,
        "health_distribution": {
            "healthy": healthy_count,
            "monitoring": monitoring_count,
            "at_risk": at_risk_count,
            "critical": critical_count
        },
        "active_alerts_count": active_alerts,
        "critical_alerts_count": critical_alerts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

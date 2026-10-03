from pymongo import MongoClient
from datetime import datetime, timedelta
import random

from backend.app.config import settings


client = MongoClient(settings.MONGODB_URL)
db = client[settings.MONGODB_DATABASE]


print("Connected to MongoDB.")


# Clear only VETRA demo collections.
collections = [
    "users",
    "farms",
    "animals",
    "health_readings",
    "alerts",
    "preventive_tasks",
    "veterinary_cases",
    "devices",
    "notifications",
    "audit_logs"
]

for collection in collections:
    db[collection].delete_many({})


# --------------------------------------------------
# FARM
# --------------------------------------------------

farm = {
    "farm_id": "FARM-001",
    "name": "VETRA Demo Dairy Farm",
    "location": "Tamil Nadu, India",
    "animal_count": 10,
    "created_at": datetime.utcnow()
}

db.farms.insert_one(farm)


# --------------------------------------------------
# ANIMALS
# --------------------------------------------------

breeds = [
    "Holstein Friesian",
    "Jersey",
    "Gir",
    "Sahiwal"
]


animals = []

for i in range(1, 11):

    animal = {
        "animal_id": f"COW-{i:03d}",
        "farm_id": "FARM-001",
        "species": "cattle",
        "breed": random.choice(breeds),
        "sex": random.choice(["Female", "Male"]),
        "age_months": random.randint(18, 72),
        "weight_kg": random.randint(250, 550),
        "health_status": "Healthy",
        "monitoring_enabled": True,
        "created_at": datetime.utcnow()
    }

    animals.append(animal)


db.animals.insert_many(animals)


# --------------------------------------------------
# DEVICES
# --------------------------------------------------

devices = []

for i in range(1, 11):

    devices.append({
        "device_id": f"DEV-{i:03d}",
        "animal_id": f"COW-{i:03d}",
        "farm_id": "FARM-001",
        "type": "livestock_health_sensor",
        "status": "online",
        "last_seen": datetime.utcnow()
    })


db.devices.insert_many(devices)


# --------------------------------------------------
# HEALTH READINGS
# --------------------------------------------------

readings = []

for animal in animals:

    for j in range(10):

        timestamp = (
            datetime.utcnow()
            - timedelta(minutes=(10 - j) * 10)
        )

        readings.append({
            "animal_id": animal["animal_id"],
            "farm_id": "FARM-001",
            "timestamp": timestamp,
            "temperature_c": round(
                random.uniform(38.0, 39.0),
                2
            ),
            "heart_rate_bpm": random.randint(
                60,
                85
            ),
            "activity_percent": random.randint(
                65,
                100
            ),
            "feed_intake_percent": random.randint(
                70,
                100
            ),
            "water_intake_percent": random.randint(
                65,
                100
            ),
            "rumination_percent": random.randint(
                60,
                100
            ),
            "source": "SIMULATED"
        })


db.health_readings.insert_many(readings)


# --------------------------------------------------
# PREVENTIVE TASK
# --------------------------------------------------

db.preventive_tasks.insert_one({
    "task_id": "TASK-001",
    "animal_id": "COW-003",
    "farm_id": "FARM-001",
    "type": "vaccination",
    "title": "Routine vaccination",
    "due_date": datetime.utcnow()
    + timedelta(days=7),
    "status": "upcoming"
})


print()
print("====================================")
print("VETRA DATABASE SEEDED SUCCESSFULLY")
print("====================================")

print(
    "Farms:",
    db.farms.count_documents({})
)

print(
    "Animals:",
    db.animals.count_documents({})
)

print(
    "Health readings:",
    db.health_readings.count_documents({})
)

print(
    "Devices:",
    db.devices.count_documents({})
)

print(
    "Preventive tasks:",
    db.preventive_tasks.count_documents({})
)

print()
print("Synthetic data is marked as SIMULATED.")
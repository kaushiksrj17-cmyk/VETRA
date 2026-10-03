from datetime import datetime, timezone

from app.database import get_database
from app.security import hash_password


DEMO_USERS = [
    {
        "full_name": "Dr. Ananya Veterinary",
        "email": "vet@vetra.demo",
        "password": "VetraVet@2026",
        "role": "veterinarian"
    },
    {
        "full_name": "VETRA System Administrator",
        "email": "admin@vetra.demo",
        "password": "VetraAdmin@2026",
        "role": "admin"
    }
]


def create_demo_users():
    db = get_database()

    for user in DEMO_USERS:

        existing_user = db.users.find_one({
            "email": user["email"]
        })

        if existing_user:
            print(
                f"Already exists: "
                f"{user['email']} "
                f"({existing_user.get('role')})"
            )
            continue

        now = datetime.now(timezone.utc)

        new_user = {
            "full_name": user["full_name"],
            "email": user["email"],
            "password_hash": hash_password(
                user["password"]
            ),
            "role": user["role"],
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }

        db.users.insert_one(new_user)

        print(
            f"Created: "
            f"{user['email']} "
            f"({user['role']})"
        )


if __name__ == "__main__":
    create_demo_users()
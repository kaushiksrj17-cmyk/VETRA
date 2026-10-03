from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.database import get_database


PREVENTIVE_ALERT_TYPES = {
    "vaccination": "preventive_vaccination",
    "deworming": "preventive_deworming",
    "veterinary_follow_up": "preventive_veterinary_follow_up",
}


def _parse_date(value: Any) -> date | None:
    """
    Convert supported date values into a Python date.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _get_today() -> date:
    """
    Return the current UTC date.
    """

    return datetime.now(timezone.utc).date()


def _get_preventive_status(due_date: date) -> str:
    """
    Determine the current preventive schedule status.

    overdue:
        Due before today.

    due_today:
        Due today.

    due_soon:
        Due within the next 30 days.

    upcoming:
        More than 30 days away.
    """

    today = _get_today()

    if due_date < today:
        return "overdue"

    if due_date == today:
        return "due_today"

    days_until_due = (due_date - today).days

    if days_until_due <= 30:
        return "due_soon"

    return "upcoming"


def _severity_for_status(status: str) -> str:
    """
    Convert preventive schedule status into alert severity.
    """

    if status == "overdue":
        return "high"

    if status == "due_today":
        return "medium"

    return "low"


def _get_action_name(
    category: str,
    record: dict[str, Any],
) -> str:
    """
    Get a human-readable preventive action name.
    """

    if category == "vaccination":
        return str(
            record.get(
                "vaccine_name",
                "Vaccination",
            )
        )

    if category == "deworming":
        return str(
            record.get(
                "medicine_name",
                "Deworming",
            )
        )

    return "Veterinary Follow-up"


def _get_alert_title(category: str) -> str:
    """
    Get a standardized alert title.
    """

    if category == "vaccination":
        return "Vaccination Preventive Reminder"

    if category == "deworming":
        return "Deworming Preventive Reminder"

    return "Veterinary Follow-up Reminder"


def _build_alert_message(
    category: str,
    record: dict[str, Any],
    animal: dict[str, Any],
    due_date: date,
    status: str,
) -> str:
    """
    Build the human-readable preventive alert message.
    """

    action_name = _get_action_name(
        category,
        record,
    )

    animal_label = (
        animal.get("tag_id")
        or animal.get("name")
        or str(animal.get("_id"))
    )

    if status == "overdue":
        return (
            f"{action_name} for animal "
            f"{animal_label} was due on "
            f"{due_date.isoformat()} and is now overdue."
        )

    if status == "due_today":
        return (
            f"{action_name} for animal "
            f"{animal_label} is due today."
        )

    days_until_due = (
        due_date - _get_today()
    ).days

    return (
        f"{action_name} for animal "
        f"{animal_label} is due in "
        f"{days_until_due} day(s) on "
        f"{due_date.isoformat()}."
    )


def _build_preventive_alert(
    category: str,
    record: dict[str, Any],
    animal: dict[str, Any],
    due_date: date,
    status: str,
) -> dict[str, Any]:
    """
    Build a standardized VETRA preventive alert document.
    """

    animal_id = str(animal["_id"])

    farm_id = str(
        animal.get(
            "farm_id",
            record.get("farm_id", ""),
        )
    )

    owner_id = str(
        animal.get(
            "owner_id",
            record.get("owner_id", ""),
        )
    )

    record_id = str(record["_id"])

    alert_type = PREVENTIVE_ALERT_TYPES.get(
        category,
        "preventive_care",
    )

    title = _get_alert_title(category)

    message = _build_alert_message(
        category=category,
        record=record,
        animal=animal,
        due_date=due_date,
        status=status,
    )

    preventive_event_key = (
        f"{alert_type}:"
        f"{animal_id}:"
        f"{record_id}:"
        f"{due_date.isoformat()}"
    )

    return {
        "animal_id": animal_id,
        "farm_id": farm_id,
        "owner_id": owner_id,

        # System-generated preventive alert.
        "device_id": "PREVENTIVE-SYSTEM",

        "alert_type": alert_type,
        "severity": _severity_for_status(status),

        "title": title,
        "message": message,

        "triggered_by": [
            "preventive_scheduler",
            category,
            status,
        ],

        "status": "active",

        # This is not a physiological health reading.
        "health_reading_id": None,

        # Preventive metadata.
        "preventive_record_id": record_id,
        "preventive_category": category,
        "preventive_status": status,
        "preventive_due_date": due_date.isoformat(),
        "preventive_event_key": preventive_event_key,

        "created_at": datetime.now(timezone.utc),
    }


def _create_alert_if_needed(
    db,
    alert_document: dict[str, Any],
) -> tuple[bool, str]:
    """
    Create a preventive alert if it does not already exist.

    Returns:
        (True, "created")
        (False, "duplicate")
        (False, "error")
    """

    event_key = alert_document[
        "preventive_event_key"
    ]

    existing = db.alerts.find_one(
        {
            "preventive_event_key": event_key
        }
    )

    if existing:
        return False, "duplicate"

    try:
        result = db.alerts.insert_one(
            alert_document
        )

        if result.inserted_id:
            return True, "created"

        return False, "error"

    except DuplicateKeyError:
        return False, "duplicate"

    except Exception as exc:
        print(
            "[VETRA PREVENTIVE ALERT ERROR]"
            f" Failed to insert alert: {exc}"
        )

        return False, "error"


def _process_records(
    db,
    collection_name: str,
    category: str,
    due_field: str,
    owner_filter: str | None = None,
) -> dict[str, int]:
    """
    Process vaccination, deworming or veterinary records.

    Returns diagnostic counts so Phase 6.5 can be
    verified without silently hiding failures.
    """

    collection = db[collection_name]

    query: dict[str, Any] = {
        due_field: {
            "$exists": True,
            "$nin": [
                None,
                "",
            ],
        }
    }

    if owner_filter:
        query["owner_id"] = owner_filter

    records = collection.find(query)

    scanned = 0
    eligible = 0
    created = 0
    duplicates = 0
    skipped = 0
    errors = 0

    for record in records:

        scanned += 1

        record_id = str(
            record.get("_id", "")
        )

        due_date = _parse_date(
            record.get(due_field)
        )

        if due_date is None:
            skipped += 1

            print(
                "[VETRA PREVENTIVE ALERT]"
                f" Skipped {category} record "
                f"{record_id}: invalid due date."
            )

            continue

        preventive_status = (
            _get_preventive_status(
                due_date
            )
        )

        # Upcoming actions more than 30 days away
        # should not generate alerts.
        if preventive_status == "upcoming":
            skipped += 1
            continue

        eligible += 1

        animal_id = record.get(
            "animal_id"
        )

        if not animal_id:
            skipped += 1

            print(
                "[VETRA PREVENTIVE ALERT]"
                f" Skipped {category} record "
                f"{record_id}: missing animal_id."
            )

            continue

        if not ObjectId.is_valid(
            str(animal_id)
        ):
            skipped += 1

            print(
                "[VETRA PREVENTIVE ALERT]"
                f" Skipped {category} record "
                f"{record_id}: invalid animal_id "
                f"{animal_id}."
            )

            continue

        animal = db.animals.find_one(
            {
                "_id": ObjectId(
                    str(animal_id)
                )
            }
        )

        if not animal:
            skipped += 1

            print(
                "[VETRA PREVENTIVE ALERT]"
                f" Skipped {category} record "
                f"{record_id}: animal not found."
            )

            continue

        # Farmer-specific safety check.
        if owner_filter:
            if (
                animal.get("owner_id")
                != owner_filter
            ):
                skipped += 1

                print(
                    "[VETRA PREVENTIVE ALERT]"
                    f" Skipped {category} record "
                    f"{record_id}: owner mismatch."
                )

                continue

        alert_document = _build_preventive_alert(
            category=category,
            record=record,
            animal=animal,
            due_date=due_date,
            status=preventive_status,
        )

        was_created, result_status = (
            _create_alert_if_needed(
                db=db,
                alert_document=alert_document,
            )
        )

        if was_created:
            created += 1

            print(
                "[VETRA PREVENTIVE ALERT]"
                f" CREATED | {category} | "
                f"{alert_document['title']} | "
                f"animal={animal.get('tag_id', animal_id)} | "
                f"status={preventive_status}"
            )

        elif result_status == "duplicate":
            duplicates += 1

        else:
            errors += 1

    return {
        "scanned": scanned,
        "eligible": eligible,
        "created": created,
        "duplicates": duplicates,
        "skipped": skipped,
        "errors": errors,
    }


def generate_preventive_alerts(
    owner_id: str | None = None,
) -> dict[str, Any]:
    """
    Scan all preventive-care records and automatically
    create alerts for:

    - overdue
    - due today
    - due within 30 days

    Preventive actions more than 30 days away do not
    generate alerts.

    Duplicate preventive alerts are prevented using
    preventive_event_key.
    """

    db = get_database()

    print(
        "[VETRA PREVENTIVE ALERT]"
        " Starting preventive alert synchronization..."
    )

    vaccination_result = _process_records(
        db=db,
        collection_name="vaccinations",
        category="vaccination",
        due_field="next_due_date",
        owner_filter=owner_id,
    )

    deworming_result = _process_records(
        db=db,
        collection_name="deworming",
        category="deworming",
        due_field="next_due_date",
        owner_filter=owner_id,
    )

    veterinary_result = _process_records(
        db=db,
        collection_name="vet_visits",
        category="veterinary_follow_up",
        due_field="follow_up_date",
        owner_filter=owner_id,
    )

    total_created = (
        vaccination_result["created"]
        + deworming_result["created"]
        + veterinary_result["created"]
    )

    total_duplicates = (
        vaccination_result["duplicates"]
        + deworming_result["duplicates"]
        + veterinary_result["duplicates"]
    )

    total_scanned = (
        vaccination_result["scanned"]
        + deworming_result["scanned"]
        + veterinary_result["scanned"]
    )

    total_eligible = (
        vaccination_result["eligible"]
        + deworming_result["eligible"]
        + veterinary_result["eligible"]
    )

    total_skipped = (
        vaccination_result["skipped"]
        + deworming_result["skipped"]
        + veterinary_result["skipped"]
    )

    total_errors = (
        vaccination_result["errors"]
        + deworming_result["errors"]
        + veterinary_result["errors"]
    )

    result = {
        "vaccination_alerts_created": vaccination_result[
            "created"
        ],
        "deworming_alerts_created": deworming_result[
            "created"
        ],
        "veterinary_follow_up_alerts_created": veterinary_result[
            "created"
        ],
        "total_created": total_created,

        "total_scanned": total_scanned,
        "total_eligible": total_eligible,
        "total_duplicates": total_duplicates,
        "total_skipped": total_skipped,
        "total_errors": total_errors,

        "vaccination_details": vaccination_result,
        "deworming_details": deworming_result,
        "veterinary_follow_up_details": veterinary_result,
    }

    print(
        "[VETRA PREVENTIVE ALERT]"
        f" Synchronization complete: "
        f"created={total_created}, "
        f"duplicates={total_duplicates}, "
        f"eligible={total_eligible}, "
        f"errors={total_errors}"
    )

    return result
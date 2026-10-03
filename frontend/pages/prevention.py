from datetime import date, datetime

import pandas as pd
import streamlit as st

import api_client


# ============================================================
# DATE HELPERS
# ============================================================

def _parse_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).date()
    except (ValueError, TypeError):
        try:
            return date.fromisoformat(
                str(value)[:10]
            )
        except (ValueError, TypeError):
            return None


def _date_text(value):
    parsed = _parse_date(value)

    if not parsed:
        return "-"

    return parsed.strftime("%d %b %Y")


def _get_status(due_date):
    parsed = _parse_date(due_date)

    if not parsed:
        return "UNKNOWN"

    today = date.today()

    if parsed < today:
        return "OVERDUE"

    if parsed == today:
        return "DUE TODAY"

    days_until = (parsed - today).days

    if days_until <= 30:
        return "DUE SOON"

    return "UPCOMING"


def _status_message(status):
    if status == "OVERDUE":
        return "Overdue"

    if status == "DUE TODAY":
        return "Due Today"

    if status == "DUE SOON":
        return "Due Soon"

    if status == "UPCOMING":
        return "Upcoming"

    return "Unknown"


# ============================================================
# GENERAL HELPERS
# ============================================================

def _animal_name(animal_map, animal_id):
    animal = animal_map.get(animal_id)

    if not animal:
        return "Unknown Animal"

    name = animal.get("name") or "Unnamed Animal"
    tag = animal.get("tag_id") or "No Tag"

    return f"{name} ({tag})"


def _animal_display(animal):
    return (
        f"{animal.get('name') or 'Unnamed Animal'} "
        f"({animal.get('tag_id') or 'No Tag'})"
    )


# ============================================================
# REMINDER TABLE
# ============================================================

def _build_reminder_rows(reminders, animal_map):
    rows = []

    for reminder in reminders:

        animal_id = reminder.get("animal_id")

        due_date = (
            reminder.get("due_date")
            or reminder.get("next_due_date")
            or reminder.get("next_visit_date")
        )

        action = (
            reminder.get("title")
            or reminder.get("action")
            or reminder.get("type")
            or reminder.get("reminder_type")
            or reminder.get("category")
            or "Preventive Action"
        )

        category = (
            reminder.get("category")
            or reminder.get("type")
            or "Preventive Care"
        )

        rows.append(
            {
                "Animal": _animal_name(
                    animal_map,
                    animal_id
                ),
                "Category": str(category).replace(
                    "_",
                    " "
                ).title(),
                "Action": str(action).replace(
                    "_",
                    " "
                ).title(),
                "Due Date": _date_text(due_date),
                "Status": _status_message(
                    _get_status(due_date)
                ),
            }
        )

    return rows


# ============================================================
# RECORD SUMMARY
# ============================================================

def _show_record_summary(title, records):

    st.markdown(
        f"#### {title}"
    )

    if not records:

        st.info(
            f"No {title.lower()} available."
        )

        return

    for record in records:

        with st.container(border=True):

            primary_name = (
                record.get("vaccine_name")
                or record.get("medicine_name")
                or record.get("condition_diagnosed")
                or record.get("veterinarian_name")
                or "Record"
            )

            st.markdown(
                f"**{primary_name}**"
            )

            cols = st.columns(3)

            with cols[0]:

                record_date = (
                    record.get("administered_date")
                    or record.get("start_date")
                    or record.get("visit_date")
                )

                st.write(
                    f"Date: {_date_text(record_date)}"
                )

            with cols[1]:

                due_date = (
                    record.get("next_due_date")
                    or record.get("end_date")
                    or record.get("follow_up_date")
                )

                st.write(
                    f"Next Due / Follow-up: {_date_text(due_date)}"
                )

            with cols[2]:

                veterinarian = (
                    record.get("veterinarian_name")
                    or "-"
                )

                st.write(
                    f"Veterinarian: {veterinarian}"
                )

            if record.get("dosage"):

                st.write(
                    f"Dosage: {record.get('dosage')}"
                )

            if record.get("medication"):

                st.write(
                    f"Medication: {record.get('medication')}"
                )

            if record.get("observations"):

                st.write(
                    f"Observations: {record.get('observations')}"
                )

            if record.get("recommendations"):

                st.write(
                    f"Recommendations: {record.get('recommendations')}"
                )

            if record.get("outcome"):

                st.write(
                    f"Outcome: {record.get('outcome')}"
                )

            if record.get("notes"):

                st.caption(
                    f"Notes: {record.get('notes')}"
                )


# ============================================================
# PREVENTIVE INTELLIGENCE ENGINE
# ============================================================

def _calculate_preventive_intelligence(
    vaccinations,
    deworming,
    treatments,
    vet_visits,
):
    """
    Rule-based preventive decision-support engine.

    This does not diagnose disease.
    It identifies preventive-care gaps and follow-up needs.
    """

    categories = {
        "Vaccination": vaccinations,
        "Deworming": deworming,
        "Treatment": treatments,
        "Veterinary Visit": vet_visits,
    }

    overdue = []
    due_today = []
    due_soon = []
    upcoming = []

    for category, records in categories.items():

        for record in records:

            due_date = (
                record.get("next_due_date")
                or record.get("follow_up_date")
            )

            parsed = _parse_date(due_date)

            if not parsed:
                continue

            item = {
                "category": category,
                "record": record,
                "date": parsed,
            }

            status = _get_status(parsed)

            if status == "OVERDUE":

                overdue.append(item)

            elif status == "DUE TODAY":

                due_today.append(item)

            elif status == "DUE SOON":

                due_soon.append(item)

            elif status == "UPCOMING":

                upcoming.append(item)

    risk_points = 0

    risk_points += min(
        len(overdue) * 25,
        60
    )

    risk_points += min(
        len(due_today) * 15,
        30
    )

    risk_points += min(
        len(due_soon) * 8,
        20
    )

    if not vaccinations:

        risk_points += 10

    if not deworming:

        risk_points += 10

    if not vet_visits:

        risk_points += 5

    risk_points = min(
        risk_points,
        100
    )

    if risk_points >= 60:

        risk_level = "HIGH"

    elif risk_points >= 30:

        risk_level = "MODERATE"

    else:

        risk_level = "LOW"

    actions = []

    if overdue:

        actions.append(
            "Review overdue preventive-care actions "
            "and arrange follow-up."
        )

    if due_today:

        actions.append(
            "Complete preventive actions scheduled for today."
        )

    if due_soon:

        actions.append(
            "Prepare for preventive actions due within 30 days."
        )

    if not vaccinations:

        actions.append(
            "Review vaccination history with a veterinarian."
        )

    if not deworming:

        actions.append(
            "Review deworming history and preventive schedule."
        )

    if not vet_visits:

        actions.append(
            "Consider establishing a routine veterinary "
            "review schedule."
        )

    if not actions:

        actions.append(
            "Preventive records appear up to date. "
            "Continue routine preventive monitoring."
        )

    return {
        "risk_score": risk_points,
        "risk_level": risk_level,
        "overdue": overdue,
        "due_today": due_today,
        "due_soon": due_soon,
        "upcoming": upcoming,
        "actions": actions,
    }


# ============================================================
# AI PREVENTIVE RECOMMENDATION
# ============================================================

def _build_ai_preventive_recommendation(
    animal,
    ai_assessment,
    intelligence,
    vaccinations,
    deworming,
    treatments,
    vet_visits,
):
    """
    Combines the existing VETRA AI health assessment
    with preventive-care information.

    This is decision-support and does not diagnose disease.
    """

    animal_name = (
        animal.get("name")
        or animal.get("tag_id")
        or "Selected Animal"
    )

    health_risk = str(
        ai_assessment.get(
            "risk_category",
            "low"
        )
    ).upper()

    health_score = ai_assessment.get(
        "risk_score",
        0
    )

    disease_risk = str(
        ai_assessment.get(
            "disease_risk_level",
            "low"
        )
    ).upper()

    early_warning = str(
        ai_assessment.get(
            "early_warning_level",
            "LOW"
        )
    ).upper()

    deterioration = bool(
        ai_assessment.get(
            "deterioration_detected",
            False
        )
    )

    preventive_risk = intelligence.get(
        "risk_level",
        "LOW"
    )

    preventive_score = intelligence.get(
        "risk_score",
        0
    )

    gaps = []

    if not vaccinations:

        gaps.append(
            "No vaccination history is currently recorded."
        )

    if not deworming:

        gaps.append(
            "No deworming history is currently recorded."
        )

    if not vet_visits:

        gaps.append(
            "No veterinary visit history is currently recorded."
        )

    if not treatments:

        gaps.append(
            "No treatment history is currently recorded."
        )

    overdue_count = len(
        intelligence.get(
            "overdue",
            []
        )
    )

    due_today_count = len(
        intelligence.get(
            "due_today",
            []
        )
    )

    due_soon_count = len(
        intelligence.get(
            "due_soon",
            []
        )
    )

    if (
        health_risk == "CRITICAL"
        or disease_risk == "HIGH"
        or early_warning == "CRITICAL"
        or deterioration
        or overdue_count >= 2
    ):

        priority = "HIGH"

    elif (
        health_risk == "HIGH"
        or disease_risk == "MODERATE"
        or early_warning == "HIGH"
        or overdue_count == 1
        or due_today_count > 0
    ):

        priority = "MODERATE"

    else:

        priority = "ROUTINE"

    if priority == "HIGH":

        recommendation = (
            f"{animal_name} requires prompt preventive "
            "and veterinary review. Recent health-risk "
            "indicators or preventive-care gaps suggest "
            "that follow-up should be prioritized."
        )

        monitoring = (
            "Increase monitoring frequency and review "
            "recent health telemetry together with "
            "preventive records."
        )

    elif priority == "MODERATE":

        recommendation = (
            f"{animal_name} has preventive-care items "
            "that should be reviewed in the near term. "
            "Maintain regular health monitoring while "
            "completing pending preventive actions."
        )

        monitoring = (
            "Continue close routine monitoring and review "
            "upcoming preventive-care dates."
        )

    else:

        recommendation = (
            f"{animal_name} currently shows no major "
            "combined health or preventive-care warning. "
            "Maintain the routine preventive healthcare "
            "schedule."
        )

        monitoring = (
            "Continue regular telemetry monitoring and "
            "scheduled preventive healthcare."
        )

    return {
        "animal_name": animal_name,
        "health_risk_level": health_risk,
        "health_risk_score": health_score,
        "disease_risk": disease_risk,
        "early_warning": early_warning,
        "deterioration_detected": deterioration,
        "preventive_risk": preventive_risk,
        "preventive_score": preventive_score,
        "priority": priority,
        "gaps": gaps,
        "overdue_count": overdue_count,
        "due_today_count": due_today_count,
        "due_soon_count": due_soon_count,
        "recommendation": recommendation,
        "monitoring": monitoring,
    }


# ============================================================
# PRIORITY ACTION CARD
# ============================================================

def _show_intelligence_action(item):

    category = item["category"]

    record = item["record"]

    due_date = item["date"]

    if category == "Vaccination":

        name = (
            record.get("vaccine_name")
            or "Vaccination"
        )

    elif category == "Deworming":

        name = (
            record.get("medicine_name")
            or "Deworming"
        )

    elif category == "Treatment":

        name = (
            record.get("condition_diagnosed")
            or "Treatment Follow-up"
        )

    else:

        name = (
            record.get("veterinarian_name")
            or "Veterinary Visit"
        )

    status = _get_status(
        due_date
    )

    if status == "OVERDUE":

        st.error(
            f"🔴 {category} — {name} — "
            f"Overdue since {_date_text(due_date)}"
        )

    elif status == "DUE TODAY":

        st.warning(
            f"🟠 {category} — {name} — Due today"
        )

    elif status == "DUE SOON":

        st.info(
            f"🟡 {category} — {name} — "
            f"Due {_date_text(due_date)}"
        )

    else:

        st.success(
            f"🟢 {category} — {name} — "
            f"Scheduled {_date_text(due_date)}"
        )


# ============================================================
# DATA ENTRY — VACCINATION
# ============================================================

def _render_vaccination_form(animal_id):

    st.markdown(
        "#### 💉 Add Vaccination"
    )

    with st.form(
        "add_vaccination_form",
        clear_on_submit=False
    ):

        vaccine_name = st.text_input(
            "Vaccine Name *",
            placeholder="Example: FMD Vaccine"
        )

        administered_date = st.date_input(
            "Administered Date *",
            value=date.today()
        )

        set_next_due = st.checkbox(
            "Set next vaccination due date",
            key="vaccination_next_due_enabled"
        )

        next_due_date = None

        if set_next_due:

            next_due = st.date_input(
                "Next Due Date",
                value=date.today(),
                key="vaccination_next_due_date"
            )

            next_due_date = next_due.isoformat()

        veterinarian_name = st.text_input(
            "Veterinarian Name",
            placeholder="Example: Dr. Kumar"
        )

        batch_number = st.text_input(
            "Batch Number",
            placeholder="Optional vaccine batch number"
        )

        notes = st.text_area(
            "Notes",
            placeholder="Additional vaccination notes..."
        )

        submitted = st.form_submit_button(
            "💾 Save Vaccination",
            use_container_width=True,
            type="primary"
        )

    if submitted:

        if len(vaccine_name.strip()) < 2:

            st.error(
                "Please enter a valid vaccine name."
            )

            return False

        if (
            next_due_date
            and _parse_date(next_due_date)
            and _parse_date(next_due_date) < administered_date
        ):

            st.error(
                "Next due date cannot be earlier than "
                "the administered date."
            )

            return False

        payload = {
            "animal_id": animal_id,
            "vaccine_name": vaccine_name.strip(),
            "administered_date": (
                administered_date.isoformat()
            ),
            "next_due_date": next_due_date,
            "veterinarian_name": (
                veterinarian_name.strip()
                or None
            ),
            "batch_number": (
                batch_number.strip()
                or None
            ),
            "notes": (
                notes.strip()
                or None
            ),
        }

        success, result = (
            api_client.create_vaccination(
                payload
            )
        )

        if success:

            st.success(
                "Vaccination record saved successfully."
            )

            st.session_state[
                "prevention_refresh_message"
            ] = "Vaccination record added."

            st.rerun()

        else:

            st.error(
                f"Unable to save vaccination: {result}"
            )

            return False

    return None


# ============================================================
# DATA ENTRY — DEWORMING
# ============================================================

def _render_deworming_form(animal_id):

    st.markdown(
        "#### 🪱 Add Deworming Record"
    )

    with st.form(
        "add_deworming_form",
        clear_on_submit=False
    ):

        medicine_name = st.text_input(
            "Medicine Name *",
            placeholder="Example: Albendazole"
        )

        dosage = st.text_input(
            "Dosage *",
            placeholder="Example: 10 ml"
        )

        administered_date = st.date_input(
            "Administered Date *",
            value=date.today()
        )

        set_next_due = st.checkbox(
            "Set next deworming due date",
            key="deworming_next_due_enabled"
        )

        next_due_date = None

        if set_next_due:

            next_due = st.date_input(
                "Next Due Date",
                value=date.today(),
                key="deworming_next_due_date"
            )

            next_due_date = next_due.isoformat()

        veterinarian_name = st.text_input(
            "Veterinarian Name",
            placeholder="Example: Dr. Kumar"
        )

        notes = st.text_area(
            "Notes",
            placeholder="Additional deworming notes..."
        )

        submitted = st.form_submit_button(
            "💾 Save Deworming",
            use_container_width=True,
            type="primary"
        )

    if submitted:

        if len(medicine_name.strip()) < 2:

            st.error(
                "Please enter a valid medicine name."
            )

            return False

        if not dosage.strip():

            st.error(
                "Please enter the dosage."
            )

            return False

        if (
            next_due_date
            and _parse_date(next_due_date)
            and _parse_date(next_due_date) < administered_date
        ):

            st.error(
                "Next due date cannot be earlier than "
                "the administered date."
            )

            return False

        payload = {
            "animal_id": animal_id,
            "medicine_name": medicine_name.strip(),
            "dosage": dosage.strip(),
            "administered_date": (
                administered_date.isoformat()
            ),
            "next_due_date": next_due_date,
            "veterinarian_name": (
                veterinarian_name.strip()
                or None
            ),
            "notes": (
                notes.strip()
                or None
            ),
        }

        success, result = (
            api_client.create_deworming(
                payload
            )
        )

        if success:

            st.success(
                "Deworming record saved successfully."
            )

            st.session_state[
                "prevention_refresh_message"
            ] = "Deworming record added."

            st.rerun()

        else:

            st.error(
                f"Unable to save deworming: {result}"
            )

            return False

    return None


# ============================================================
# DATA ENTRY — TREATMENT
# ============================================================

def _render_treatment_form(animal_id):

    st.markdown(
        "#### 💊 Add Treatment Record"
    )

    with st.form(
        "add_treatment_form",
        clear_on_submit=False
    ):

        condition_diagnosed = st.text_input(
            "Condition / Clinical Issue *",
            placeholder="Example: Respiratory infection"
        )

        medication = st.text_input(
            "Medication *",
            placeholder="Example: Veterinary antibiotic"
        )

        dosage = st.text_input(
            "Dosage *",
            placeholder="Example: 5 ml twice daily"
        )

        start_date = st.date_input(
            "Treatment Start Date *",
            value=date.today()
        )

        set_end_date = st.checkbox(
            "Set treatment end date",
            key="treatment_end_enabled"
        )

        end_date = None

        if set_end_date:

            selected_end_date = st.date_input(
                "Treatment End Date",
                value=date.today(),
                key="treatment_end_date"
            )

            end_date = selected_end_date.isoformat()

        veterinarian_name = st.text_input(
            "Veterinarian Name",
            placeholder="Example: Dr. Kumar"
        )

        outcome = st.selectbox(
            "Treatment Outcome",
            options=[
                "ongoing",
                "improving",
                "recovered",
                "referred",
                "discontinued",
            ]
        )

        alert_id = st.text_input(
            "Related Alert ID",
            placeholder="Optional VETRA alert ID"
        )

        notes = st.text_area(
            "Treatment Notes",
            placeholder="Additional treatment information..."
        )

        submitted = st.form_submit_button(
            "💾 Save Treatment",
            use_container_width=True,
            type="primary"
        )

    if submitted:

        if len(condition_diagnosed.strip()) < 2:

            st.error(
                "Please enter the condition or clinical issue."
            )

            return False

        if len(medication.strip()) < 2:

            st.error(
                "Please enter the medication."
            )

            return False

        if not dosage.strip():

            st.error(
                "Please enter the dosage."
            )

            return False

        if (
            end_date
            and _parse_date(end_date)
            and _parse_date(end_date) < start_date
        ):

            st.error(
                "Treatment end date cannot be earlier "
                "than the start date."
            )

            return False

        payload = {
            "animal_id": animal_id,
            "condition_diagnosed": (
                condition_diagnosed.strip()
            ),
            "medication": medication.strip(),
            "dosage": dosage.strip(),
            "start_date": start_date.isoformat(),
            "end_date": end_date,
            "veterinarian_name": (
                veterinarian_name.strip()
                or None
            ),
            "alert_id": (
                alert_id.strip()
                or None
            ),
            "outcome": outcome,
            "notes": (
                notes.strip()
                or None
            ),
        }

        success, result = (
            api_client.create_treatment(
                payload
            )
        )

        if success:

            st.success(
                "Treatment record saved successfully."
            )

            st.session_state[
                "prevention_refresh_message"
            ] = "Treatment record added."

            st.rerun()

        else:

            st.error(
                f"Unable to save treatment: {result}"
            )

            return False

    return None


# ============================================================
# DATA ENTRY — VETERINARY VISIT
# ============================================================

def _render_vet_visit_form(animal_id):

    st.markdown(
        "#### 🩺 Record Veterinary Visit"
    )

    with st.form(
        "add_vet_visit_form",
        clear_on_submit=False
    ):

        veterinarian_name = st.text_input(
            "Veterinarian Name *",
            placeholder="Example: Dr. Kumar"
        )

        visit_date = st.date_input(
            "Visit Date *",
            value=date.today()
        )

        observations = st.text_area(
            "Clinical Observations *",
            placeholder=(
                "Enter the veterinarian's observations "
                "during the visit..."
            )
        )

        recommendations = st.text_area(
            "Recommendations *",
            placeholder=(
                "Enter recommended care, monitoring, "
                "medication or preventive actions..."
            )
        )

        set_follow_up = st.checkbox(
            "Set follow-up date",
            key="vet_followup_enabled"
        )

        follow_up_date = None

        if set_follow_up:

            selected_followup = st.date_input(
                "Follow-up Date",
                value=date.today(),
                key="vet_followup_date"
            )

            follow_up_date = selected_followup.isoformat()

        alert_id = st.text_input(
            "Related Alert ID",
            placeholder="Optional VETRA alert ID"
        )

        submitted = st.form_submit_button(
            "💾 Save Veterinary Visit",
            use_container_width=True,
            type="primary"
        )

    if submitted:

        if len(veterinarian_name.strip()) < 2:

            st.error(
                "Please enter the veterinarian name."
            )

            return False

        if len(observations.strip()) < 2:

            st.error(
                "Please enter the clinical observations."
            )

            return False

        if len(recommendations.strip()) < 2:

            st.error(
                "Please enter the recommendations."
            )

            return False

        if (
            follow_up_date
            and _parse_date(follow_up_date)
            and _parse_date(follow_up_date) < visit_date
        ):

            st.error(
                "Follow-up date cannot be earlier "
                "than the visit date."
            )

            return False

        payload = {
            "animal_id": animal_id,
            "veterinarian_name": (
                veterinarian_name.strip()
            ),
            "visit_date": visit_date.isoformat(),
            "observations": observations.strip(),
            "recommendations": recommendations.strip(),
            "follow_up_date": follow_up_date,
            "alert_id": (
                alert_id.strip()
                or None
            ),
        }

        success, result = (
            api_client.create_vet_visit(
                payload
            )
        )

        if success:

            st.success(
                "Veterinary visit saved successfully."
            )

            st.session_state[
                "prevention_refresh_message"
            ] = "Veterinary visit recorded."

            st.rerun()

        else:

            st.error(
                f"Unable to save veterinary visit: {result}"
            )

            return False

    return None


# ============================================================
# DATA ENTRY CENTER
# ============================================================

def _render_data_entry_center(animal_id):

    st.divider()

    st.markdown(
        "### ➕ Preventive Care Data Entry"
    )

    st.caption(
        "Record vaccinations, deworming, treatments and "
        "veterinary visits directly in the VETRA health record."
    )

    entry_tabs = st.tabs(
        [
            "💉 Vaccination",
            "🪱 Deworming",
            "💊 Treatment",
            "🩺 Veterinary Visit",
        ]
    )

    with entry_tabs[0]:

        _render_vaccination_form(
            animal_id
        )

    with entry_tabs[1]:

        _render_deworming_form(
            animal_id
        )

    with entry_tabs[2]:

        _render_treatment_form(
            animal_id
        )

    with entry_tabs[3]:

        _render_vet_visit_form(
            animal_id
        )


# ============================================================
# SMART PREVENTIVE SCHEDULER
# ============================================================

def _build_scheduler_events(
    vaccinations,
    deworming,
    vet_visits,
):
    events = []

    for record in vaccinations:

        due_date = record.get(
            "next_due_date"
        )

        if due_date:

            events.append(
                {
                    "category": "Vaccination",
                    "action": record.get(
                        "vaccine_name",
                        "Vaccination"
                    ),
                    "date": due_date,
                    "provider": record.get(
                        "veterinarian_name"
                    ) or "-",
                }
            )

    for record in deworming:

        due_date = record.get(
            "next_due_date"
        )

        if due_date:

            events.append(
                {
                    "category": "Deworming",
                    "action": record.get(
                        "medicine_name",
                        "Deworming"
                    ),
                    "date": due_date,
                    "provider": record.get(
                        "veterinarian_name"
                    ) or "-",
                }
            )

    for record in vet_visits:

        follow_up_date = record.get(
            "follow_up_date"
        )

        if follow_up_date:

            events.append(
                {
                    "category": "Veterinary Follow-up",
                    "action": "Veterinary Review",
                    "date": follow_up_date,
                    "provider": record.get(
                        "veterinarian_name"
                    ) or "-",
                }
            )

    events.sort(
        key=lambda item: (
            _parse_date(
                item.get("date")
            )
            or date.max
        )
    )

    return events


def _render_smart_scheduler(
    vaccinations,
    deworming,
    vet_visits,
):
    events = _build_scheduler_events(
        vaccinations,
        deworming,
        vet_visits,
    )

    st.divider()

    st.markdown(
        "### 📅 Smart Preventive Scheduler"
    )

    st.caption(
        "Unified preventive-care schedule generated from "
        "recorded vaccination, deworming and veterinary "
        "follow-up dates."
    )

    if not events:

        st.info(
            "No future preventive dates are currently "
            "recorded for this animal."
        )

        return

    overdue = 0
    due_today = 0
    due_soon = 0
    upcoming = 0

    for event in events:

        status = _get_status(
            event["date"]
        )

        if status == "OVERDUE":

            overdue += 1

        elif status == "DUE TODAY":

            due_today += 1

        elif status == "DUE SOON":

            due_soon += 1

        elif status == "UPCOMING":

            upcoming += 1

    total_scheduled = len(
        events
    )

    current_schedule = (
        total_scheduled - overdue
    )

    compliance = (
        (
            current_schedule
            / total_scheduled
        )
        * 100
        if total_scheduled
        else 100
    )

    compliance = round(
        max(
            0,
            min(
                100,
                compliance
            )
        ),
        1
    )

    scheduler_col1, scheduler_col2, scheduler_col3, scheduler_col4 = (
        st.columns(4)
    )

    with scheduler_col1:

        st.metric(
            "Scheduled",
            total_scheduled
        )

    with scheduler_col2:

        st.metric(
            "Overdue",
            overdue
        )

    with scheduler_col3:

        st.metric(
            "Due Soon",
            due_soon + due_today
        )

    with scheduler_col4:

        st.metric(
            "Schedule Health",
            f"{compliance}%"
        )

    if overdue > 0:

        st.error(
            f"🔴 {overdue} preventive action(s) are overdue."
        )

    elif due_today > 0:

        st.warning(
            f"🟠 {due_today} preventive action(s) are due today."
        )

    elif due_soon > 0:

        st.info(
            f"🟡 {due_soon} preventive action(s) are due "
            "within the next 30 days."
        )

    else:

        st.success(
            "🟢 Preventive schedule is currently up to date."
        )

    st.markdown(
        "#### Preventive Care Timeline"
    )

    timeline_rows = []

    for event in events:

        status = _get_status(
            event["date"]
        )

        timeline_rows.append(
            {
                "Category": event["category"],
                "Action": event["action"],
                "Scheduled Date": _date_text(
                    event["date"]
                ),
                "Status": _status_message(
                    status
                ),
                "Veterinarian": event["provider"],
            }
        )

    dataframe = pd.DataFrame(
        timeline_rows
    )

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_prevention_page():

    """
    VETRA Preventive Health Center.

    Includes:
    - Farm-level preventive queue
    - Preventive risk intelligence
    - Existing VETRA AI health assessment
    - Preventive gaps
    - Preventive recommendations
    - Vaccination/deworming/treatment/vet history
    - Preventive-care data entry
    - Smart preventive scheduler
    """

    # ========================================================
    # HEADER
    # ========================================================

    st.title(
        "Preventive Health Center"
    )

    st.caption(
        "Intelligent vaccination, deworming, treatment "
        "and veterinary follow-up management"
    )

    refresh_message = st.session_state.pop(
        "prevention_refresh_message",
        None
    )

    if refresh_message:

        st.success(
            "Preventive health data updated successfully."
        )

    # ========================================================
    # LOAD FARM DATA
    # ========================================================

    with st.spinner(
        "Loading preventive health intelligence..."
    ):

        animals = api_client.get_animals()

        reminders = api_client.get_reminders()

    animal_map = {
        animal.get("id"): animal
        for animal in animals
        if animal.get("id")
    }

    # ========================================================
    # FARM KPI CALCULATION
    # ========================================================

    overdue_count = 0
    due_today_count = 0
    due_soon_count = 0
    upcoming_count = 0

    for reminder in reminders:

        due_date = (
            reminder.get("due_date")
            or reminder.get("next_due_date")
            or reminder.get("next_visit_date")
        )

        status = _get_status(
            due_date
        )

        if status == "OVERDUE":

            overdue_count += 1

        elif status == "DUE TODAY":

            due_today_count += 1

        elif status == "DUE SOON":

            due_soon_count += 1

        elif status == "UPCOMING":

            upcoming_count += 1

    total_actions = len(
        reminders
    )

    due_count = (
        overdue_count
        + due_today_count
        + due_soon_count
    )

    # ========================================================
    # FARM KPI DASHBOARD
    # ========================================================

    st.markdown(
        "### Preventive Care Overview"
    )

    kpi1, kpi2, kpi3, kpi4, kpi5 = (
        st.columns(5)
    )

    with kpi1:

        st.metric(
            "Total Actions",
            total_actions
        )

    with kpi2:

        st.metric(
            "Needs Attention",
            due_count
        )

    with kpi3:

        st.metric(
            "Overdue",
            overdue_count
        )

    with kpi4:

        st.metric(
            "Due Soon",
            due_soon_count
        )

    with kpi5:

        st.metric(
            "Upcoming",
            upcoming_count
        )

    st.divider()

    # ========================================================
    # ACTION QUEUE
    # ========================================================

    st.markdown(
        "### Preventive Action Queue"
    )

    if reminders:

        reminder_rows = _build_reminder_rows(
            reminders,
            animal_map
        )

        if reminder_rows:

            dataframe = pd.DataFrame(
                reminder_rows
            )

            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.success(
            "No preventive actions are currently scheduled."
        )

    st.divider()

    # ========================================================
    # PRIORITY ATTENTION
    # ========================================================

    st.markdown(
        "### Priority Attention"
    )

    priority_reminders = []

    for reminder in reminders:

        due_date = (
            reminder.get("due_date")
            or reminder.get("next_due_date")
            or reminder.get("next_visit_date")
        )

        status = _get_status(
            due_date
        )

        if status in {
            "OVERDUE",
            "DUE TODAY",
            "DUE SOON",
        }:

            priority_reminders.append(
                reminder
            )

    if not priority_reminders:

        st.success(
            "No immediate preventive-care action "
            "requires attention."
        )

    else:

        for reminder in priority_reminders:

            due_date = (
                reminder.get("due_date")
                or reminder.get("next_due_date")
                or reminder.get("next_visit_date")
            )

            status = _get_status(
                due_date
            )

            animal_id = reminder.get(
                "animal_id"
            )

            action = (
                reminder.get("title")
                or reminder.get("action")
                or reminder.get("type")
                or reminder.get("reminder_type")
                or reminder.get("category")
                or "Preventive Action"
            )

            if status == "OVERDUE":

                st.error(
                    f"OVERDUE — "
                    f"{_animal_name(animal_map, animal_id)} — "
                    f"{action} — "
                    f"Due {_date_text(due_date)}"
                )

            elif status == "DUE TODAY":

                st.warning(
                    f"DUE TODAY — "
                    f"{_animal_name(animal_map, animal_id)} — "
                    f"{action}"
                )

            else:

                st.info(
                    f"DUE SOON — "
                    f"{_animal_name(animal_map, animal_id)} — "
                    f"{action} — "
                    f"{_date_text(due_date)}"
                )

    st.divider()

    # ========================================================
    # ANIMAL SELECTION
    # ========================================================

    st.markdown(
        "### Animal Preventive Intelligence"
    )

    if not animals:

        st.info(
            "No livestock records are available."
        )

        return

    animal_options = {
        animal.get("id"): _animal_display(animal)
        for animal in animals
        if animal.get("id")
    }

    selected_animal_id = st.selectbox(
        "Select Animal",
        options=list(
            animal_options.keys()
        ),
        format_func=lambda animal_id:
            animal_options[animal_id],
        key="prevention_animal_selector"
    )

    selected_animal = animal_map.get(
        selected_animal_id,
        {}
    )

    # ========================================================
    # LOAD PREVENTIVE + AI DATA
    # ========================================================

    with st.spinner(
        "Loading animal health and preventive intelligence..."
    ):

        vaccinations = (
            api_client.get_vaccinations(
                selected_animal_id
            )
        )

        deworming = (
            api_client.get_deworming(
                selected_animal_id
            )
        )

        treatments = (
            api_client.get_treatments(
                selected_animal_id
            )
        )

        vet_visits = (
            api_client.get_vet_visits(
                selected_animal_id
            )
        )

        try:

            ai_assessment = (
                api_client.get_ai_assessment(
                    selected_animal_id
                )
            )

        except Exception:

            ai_assessment = {}

    if not ai_assessment:

        ai_assessment = {}

    # ========================================================
    # PREVENTIVE INTELLIGENCE
    # ========================================================

    intelligence = (
        _calculate_preventive_intelligence(
            vaccinations=vaccinations,
            deworming=deworming,
            treatments=treatments,
            vet_visits=vet_visits,
        )
    )

    ai_preventive = (
        _build_ai_preventive_recommendation(
            animal=selected_animal,
            ai_assessment=ai_assessment,
            intelligence=intelligence,
            vaccinations=vaccinations,
            deworming=deworming,
            treatments=treatments,
            vet_visits=vet_visits,
        )
    )

    risk_score = intelligence[
        "risk_score"
    ]

    risk_level = intelligence[
        "risk_level"
    ]

    # ========================================================
    # ANIMAL HEADER
    # ========================================================

    st.markdown(
        f"#### {_animal_display(selected_animal)}"
    )

    st.caption(
        "Preventive decision-support is based on available "
        "preventive-care records and scheduled follow-ups."
    )

    # ========================================================
    # PREVENTIVE RISK
    # ========================================================

    score_col1, score_col2, score_col3 = (
        st.columns(3)
    )

    with score_col1:

        st.metric(
            "Preventive Risk Score",
            f"{risk_score}/100"
        )

    with score_col2:

        st.metric(
            "Preventive Risk Level",
            risk_level
        )

    with score_col3:

        st.metric(
            "Overdue Actions",
            len(
                intelligence["overdue"]
            )
        )

    if risk_level == "HIGH":

        st.error(
            "HIGH PREVENTIVE RISK — one or more preventive "
            "care gaps require prompt review."
        )

    elif risk_level == "MODERATE":

        st.warning(
            "MODERATE PREVENTIVE RISK — preventive follow-up "
            "should be reviewed."
        )

    else:

        st.success(
            "LOW PREVENTIVE RISK — no major preventive-care "
            "gap was identified from the available records."
        )

    st.divider()

    # ========================================================
    # AI PREVENTIVE ASSESSMENT
    # ========================================================

    st.markdown(
        "### 🧠 AI Preventive Assessment"
    )

    st.caption(
        "Combined decision-support view using VETRA health "
        "intelligence and preventive-care records."
    )

    ai_col1, ai_col2, ai_col3, ai_col4 = (
        st.columns(4)
    )

    with ai_col1:

        st.metric(
            "Health Risk",
            ai_preventive[
                "health_risk_level"
            ]
        )

    with ai_col2:

        st.metric(
            "Disease Risk",
            ai_preventive[
                "disease_risk"
            ]
        )

    with ai_col3:

        st.metric(
            "Early Warning",
            ai_preventive[
                "early_warning"
            ]
        )

    with ai_col4:

        st.metric(
            "Priority",
            ai_preventive[
                "priority"
            ]
        )

    if ai_preventive[
        "priority"
    ] == "HIGH":

        st.error(
            f"🔴 HIGH PRIORITY — "
            f"{ai_preventive['recommendation']}"
        )

    elif ai_preventive[
        "priority"
    ] == "MODERATE":

        st.warning(
            f"🟠 MODERATE PRIORITY — "
            f"{ai_preventive['recommendation']}"
        )

    else:

        st.success(
            f"🟢 ROUTINE PRIORITY — "
            f"{ai_preventive['recommendation']}"
        )

    # ========================================================
    # PREVENTIVE GAPS
    # ========================================================

    if ai_preventive[
        "gaps"
    ]:

        st.markdown(
            "#### Preventive Gaps"
        )

        for gap in ai_preventive[
            "gaps"
        ]:

            st.write(
                f"• {gap}"
            )

    # ========================================================
    # MONITORING RECOMMENDATION
    # ========================================================

    st.markdown(
        "#### Monitoring Recommendation"
    )

    st.info(
        ai_preventive[
            "monitoring"
        ]
    )

    # ========================================================
    # DATA ENTRY
    # ========================================================

    _render_data_entry_center(
        selected_animal_id
    )

    # ========================================================
    # PREVENTIVE INTELLIGENCE STATUS
    # ========================================================

    st.divider()

    st.markdown(
        "### Preventive Intelligence"
    )

    intelligence_cols = st.columns(4)

    with intelligence_cols[0]:

        st.metric(
            "Overdue",
            len(
                intelligence["overdue"]
            )
        )

    with intelligence_cols[1]:

        st.metric(
            "Due Today",
            len(
                intelligence["due_today"]
            )
        )

    with intelligence_cols[2]:

        st.metric(
            "Due Soon",
            len(
                intelligence["due_soon"]
            )
        )

    with intelligence_cols[3]:

        st.metric(
            "Upcoming",
            len(
                intelligence["upcoming"]
            )
        )

    # ========================================================
    # RECOMMENDED ACTIONS
    # ========================================================

    st.markdown(
        "#### Recommended Preventive Actions"
    )

    for action in intelligence[
        "actions"
    ]:

        st.write(
            f"• {action}"
        )

    # ========================================================
    # PRIORITY PREVENTIVE ACTIONS
    # ========================================================

    priority_items = (
        intelligence["overdue"]
        + intelligence["due_today"]
        + intelligence["due_soon"]
    )

    if priority_items:

        st.markdown(
            "#### Priority Preventive Actions"
        )

        for item in priority_items:

            _show_intelligence_action(
                item
            )

    # ========================================================
    # RECORD TABS
    # ========================================================

    st.divider()

    (
        vaccination_tab,
        deworming_tab,
        treatment_tab,
        veterinary_tab,
    ) = st.tabs(
        [
            "Vaccinations",
            "Deworming",
            "Treatments",
            "Veterinary Visits",
        ]
    )

    with vaccination_tab:

        _show_record_summary(
            "Vaccination History",
            vaccinations
        )

    with deworming_tab:

        _show_record_summary(
            "Deworming History",
            deworming
        )

    with treatment_tab:

        _show_record_summary(
            "Treatment History",
            treatments
        )

    with veterinary_tab:

        _show_record_summary(
            "Veterinary Visit History",
            vet_visits
        )

    # ========================================================
    # SMART PREVENTIVE SCHEDULER
    # ========================================================

    _render_smart_scheduler(
        vaccinations=vaccinations,
        deworming=deworming,
        vet_visits=vet_visits,
    )

    # ========================================================
    # PREVENTIVE HEALTH SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### Preventive Health Summary"
    )

    (
        summary_col1,
        summary_col2,
        summary_col3,
        summary_col4,
    ) = st.columns(4)

    with summary_col1:

        st.metric(
            "Vaccination Records",
            len(vaccinations)
        )

    with summary_col2:

        st.metric(
            "Deworming Records",
            len(deworming)
        )

    with summary_col3:

        st.metric(
            "Treatment Records",
            len(treatments)
        )

    with summary_col4:

        st.metric(
            "Veterinary Visits",
            len(vet_visits)
        )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    st.caption(
        "VETRA preventive intelligence is a decision-support "
        "system based on recorded preventive-care information "
        "and existing health intelligence. It does not diagnose "
        "disease or replace professional veterinary judgment."
    )
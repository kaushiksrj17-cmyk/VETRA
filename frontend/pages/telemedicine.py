"""
frontend/pages/telemedicine.py
==============================
VETRA Phase 12 — Veterinary Telemedicine & Clinical Collaboration Platform.

Sections:
1. My Cases
2. Consultation Requests
3. Scheduled Consultations
4. Active Consultations
5. Clinical Evidence
6. Clinical Notes
7. Treatment
8. Follow-Up
9. Consultation History
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st
import api_client
from session import get_user_info


def render_telemedicine_page():
    """Renders the comprehensive Veterinary Telemedicine page."""
    user_info = get_user_info()
    user_role = str(user_info.get("role", "farmer")).lower()
    user_id = str(user_info.get("user_id") or user_info.get("_id") or "")
    user_farm_id = user_info.get("farm_id")

    # ============================================================
    # HEADER & CLINICAL SAFETY BANNER
    # ============================================================
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 1rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.1rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
                    🩺 Veterinary Telemedicine
                </h1>
                <div style="color: #94A3B8; font-size: 0.95rem; font-weight: 500; margin-top: 0.2rem;">
                    Remote Clinical Assessment, Multi-Evidence Review & Institutional Veterinary Collaboration
                </div>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.35); font-size: 0.8rem; font-weight: 700; padding: 0.35rem 0.85rem; border-radius: 9999px;">
                    🟢 TELEMEDICINE SUBSYSTEM ACTIVE
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.warning(
        "⚠️ **Clinical Telemedicine Safety Notice:** "
        "Telemedicine assessment may be limited when physical examination, laboratory testing, imaging, or on-site assessment is required. "
        "VETRA Telemedicine provides clinical decision-support and evidence communication; it does not replace urgent emergency surgical intervention."
    )

    # Tabs for the 9 core sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📋 1. My Cases",
        "📥 2. Consultation Requests",
        "📅 3. Scheduled",
        "🔴 4. Active Consultations",
        "🔬 5. Clinical Evidence",
        "📝 6. Clinical Notes",
        "💊 7. Treatment",
        "⏰ 8. Follow-Up",
        "📜 9. Consultation History"
    ])

    # Fetch relevant consultations and cases
    all_consultations = api_client.get_telemedicine_consultations() or []
    all_cases = api_client.get_cases() or []
    vets_directory = api_client.get_veterinary_profiles() or []

    # ============================================================
    # TAB 1: MY CASES
    # ============================================================
    with tab1:
        st.subheader("1. Clinical Veterinary Cases")
        st.caption("Active livestock clinical cases linked to remote telemedicine workflows.")

        if not all_cases:
            st.info("No active veterinary cases found. Cases can be created from Alerts, Predictive AI, or Visual Health.")
        else:
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            open_cases = [c for c in all_cases if c.get("status") not in ["resolved", "closed"]]
            tele_cases = [c for c in all_cases if c.get("status") == "teleconsultation"]
            escalated_cases = [c for c in all_cases if c.get("source_type") in ["predictive_assessment", "surveillance", "visual_health"]]

            with col_kpi1:
                st.metric("Total Open Cases", len(open_cases))
            with col_kpi2:
                st.metric("In Teleconsultation", len(tele_cases))
            with col_kpi3:
                st.metric("AI / Evidence Escalated", len(escalated_cases))

            st.markdown("---")
            for c in all_cases[:10]:
                c_num = c.get("case_number", c.get("_id", "Unknown"))
                with st.expander(f"Case {c_num}: {c.get('title', 'Clinical Case')} ({c.get('status', 'open').upper()})"):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.write(f"**Animal ID:** `{c.get('animal_id')}` | **Farm ID:** `{c.get('farm_id')}`")
                        st.write(f"**Priority:** `{c.get('priority')}` | **Status:** `{c.get('status')}`")
                        if c.get("source_type"):
                            st.info(f"Escalation Provenance: **{c.get('source_type')}** (ID: `{c.get('source_id', 'N/A')}`)")
                        st.write(f"**Description:** {c.get('description', 'No details provided.')}")
                    with col_b:
                        st.write(f"**Assigned Vet:** `{c.get('assigned_veterinarian_id', 'Unassigned')}`")
                        if user_role in ["veterinarian", "admin"]:
                            new_status = st.selectbox(
                                "Update Status",
                                ["unassigned", "assigned", "accepted", "in_review", "teleconsultation", "farm_visit_required", "follow_up", "resolved", "closed"],
                                index=0,
                                key=f"sel_status_{c_num}"
                            )
                            if st.button("Apply Status", key=f"btn_st_{c_num}"):
                                ok, res = api_client.update_case_status(c.get("case_number") or str(c.get("_id")), new_status)
                                if ok:
                                    st.success(f"Status updated to {new_status}")
                                    st.rerun()
                                else:
                                    st.error(f"Update failed: {res}")

    # ============================================================
    # TAB 2: CONSULTATION REQUESTS
    # ============================================================
    with tab2:
        st.subheader("2. Consultation Requests")
        st.caption("Request a new teleconsultation or review pending farmer consultation requests.")

        with st.expander("➕ Request New Telemedicine Consultation", expanded=(user_role == "farmer")):
            with st.form("form_request_teleconsult"):
                req_case_id = st.text_input("Veterinary Case ID / Number (Optional)", placeholder="CASE-2026-0001")
                req_animal_id = st.text_input("Animal ID *", placeholder="COW-001")
                req_farm_id = st.text_input("Farm ID *", value=str(user_farm_id or "FARM-001"))
                req_complaint = st.text_area("Chief Complaint / Observed Symptoms *", placeholder="Describe appetite reduction, coughing, gait changes, or fever...")
                req_mode = st.selectbox("Preferred Consultation Mode", ["telemedicine", "farm_visit", "emergency", "follow_up"])
                req_sched = st.text_input("Requested Date & Time (Optional)", placeholder="2026-10-05T10:00:00Z")

                submitted = st.form_submit_button("Submit Consultation Request")
                if submitted:
                    if not req_animal_id or not req_farm_id or not req_complaint:
                        st.error("Please fill in Animal ID, Farm ID, and Chief Complaint.")
                    else:
                        payload = {
                            "animal_id": req_animal_id,
                            "farm_id": req_farm_id,
                            "chief_complaint": req_complaint,
                            "mode": req_mode,
                        }
                        if req_case_id:
                            payload["case_id"] = req_case_id
                        if req_sched:
                            payload["scheduled_at"] = req_sched
                        ok, res = api_client.create_telemedicine_consultation(payload)
                        if ok:
                            st.success(f"Consultation requested successfully: ID `{res.get('consultation_id')}`")
                            st.rerun()
                        else:
                            st.error(f"Request failed: {res}")

        st.markdown("#### Pending Requests")
        pending_requests = [c for c in all_consultations if c.get("status") in ["requested", "pending"]]
        if not pending_requests:
            st.info("No pending consultation requests waiting for veterinarian acceptance.")
        else:
            for pr in pending_requests:
                with st.container():
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; background: #fafafa;">
                            <div style="display: flex; justify-content: space-between;">
                                <strong>Consultation {pr.get('consultation_id')}</strong>
                                <span style="background: #fef3c7; color: #b45309; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">{pr.get('status').upper()}</span>
                            </div>
                            <div style="font-size: 0.9rem; color: #475569; margin-top: 0.4rem;">
                                <b>Animal:</b> {pr.get('animal_id')} | <b>Farm:</b> {pr.get('farm_id')} | <b>Mode:</b> {pr.get('mode')}
                            </div>
                            <div style="margin-top: 0.4rem; font-size: 0.95rem;">
                                <i>Complaint:</i> {pr.get('chief_complaint')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if user_role in ["veterinarian", "admin"]:
                        col_acc1, col_acc2 = st.columns([1, 1])
                        with col_acc1:
                            acc_notes = st.text_input("Acceptance Notes", key=f"notes_{pr.get('consultation_id')}")
                        with col_acc2:
                            if st.button("✅ Accept Consultation", key=f"btn_acc_{pr.get('consultation_id')}"):
                                ok, res = api_client.accept_telemedicine_consultation(pr.get("consultation_id"), notes=acc_notes)
                                if ok:
                                    st.success(f"Consultation accepted!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {res}")

    # ============================================================
    # TAB 3: SCHEDULED CONSULTATIONS
    # ============================================================
    with tab3:
        st.subheader("3. Scheduled Consultations")
        st.caption("Confirmed teleconsultations on the clinical calendar.")

        sched_cons = [c for c in all_consultations if c.get("status") in ["scheduled", "accepted"]]
        if not sched_cons:
            st.info("No consultations currently scheduled.")
        else:
            for sc in sched_cons:
                with st.expander(f"📅 {sc.get('consultation_id')}: Animal {sc.get('animal_id')} ({sc.get('scheduled_at') or 'Time TBD'})"):
                    st.write(f"**Chief Complaint:** {sc.get('chief_complaint')}")
                    st.write(f"**Mode:** `{sc.get('mode')}` | **Assigned Vet:** `{sc.get('veterinarian_id') or 'Self/Assigned'}`")
                    if user_role in ["veterinarian", "admin"]:
                        if st.button("🚀 Start Live Consultation Session", key=f"start_{sc.get('consultation_id')}"):
                            ok, res = api_client.start_telemedicine_consultation(sc.get("consultation_id"))
                            if ok:
                                st.success("Consultation session marked in progress.")
                                st.rerun()
                            else:
                                st.error(f"Error: {res}")

    # ============================================================
    # TAB 4: ACTIVE CONSULTATIONS
    # ============================================================
    with tab4:
        st.subheader("4. Active In-Progress Consultations")
        st.caption("Real-time clinical review sessions currently in progress.")

        active_cons = [c for c in all_consultations if c.get("status") == "in_progress"]
        if not active_cons:
            st.info("No consultation sessions currently active.")
        else:
            for ac in active_cons:
                st.markdown(
                    f"""
                    <div style="border-left: 4px solid #ef4444; background: #fff1f2; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
                        <h4 style="margin: 0; color: #991b1b;">🔴 LIVE SESSION: {ac.get('consultation_id')}</h4>
                        <div style="font-size: 0.9rem; color: #7f1d1d; margin-top: 0.2rem;">
                            Animal: <b>{ac.get('animal_id')}</b> | Farm: <b>{ac.get('farm_id')}</b> | Started: <b>{ac.get('started_at') or 'Active'}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                with st.expander(f"Complete / Conclude Session {ac.get('consultation_id')}", expanded=True):
                    with st.form(f"form_complete_{ac.get('consultation_id')}"):
                        comp_summary = st.text_area("Clinical Findings / Summary *", value=ac.get("clinical_summary") or "")
                        comp_notes = st.text_area("Veterinarian Medical Notes *", value=ac.get("veterinarian_notes") or "")
                        comp_recom = st.text_area("Treatment Recommendations *", value=ac.get("recommendations") or "")
                        comp_follow_up = st.checkbox("Requires Follow-Up", value=False)
                        comp_follow_date = st.text_input("Follow-Up Target Date (Optional)", placeholder="2026-10-15")

                        if st.form_submit_button("🏁 Complete Consultation"):
                            if not comp_summary or not comp_notes:
                                st.error("Summary and notes are required to complete consultation.")
                            else:
                                ok, res = api_client.complete_telemedicine_consultation(
                                    consultation_id=ac.get("consultation_id"),
                                    clinical_summary=comp_summary,
                                    veterinarian_notes=comp_notes,
                                    recommendations=comp_recom,
                                    follow_up_date=comp_follow_date if comp_follow_up else None,
                                    follow_up_required=comp_follow_up
                                )
                                if ok:
                                    st.success(f"Consultation completed successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {res}")

    # ============================================================
    # TAB 5: CLINICAL EVIDENCE
    # ============================================================
    with tab5:
        st.subheader("5. Clinical Evidence Sharing")
        st.caption("Inspect referenced IoT vitals, predictive assessments, camera events, and visual health telemetry.")

        sel_cons_id = st.selectbox(
            "Select Consultation to View Evidence",
            options=[c.get("consultation_id") for c in all_consultations] if all_consultations else ["None"]
        )

        if sel_cons_id and sel_cons_id != "None":
            cons_obj = api_client.get_telemedicine_consultation(sel_cons_id)
            if cons_obj:
                col_ev1, col_ev2 = st.columns(2)
                with col_ev1:
                    st.markdown("##### Referenced IoT Health Readings")
                    readings = cons_obj.get("health_reading_ids") or []
                    if readings:
                        for r in readings:
                            st.write(f"- Reading ID: `{r}`")
                    else:
                        st.caption("No specific reading IDs explicitly tagged.")

                    st.markdown("##### Referenced Predictive AI Assessments")
                    preds = cons_obj.get("predictive_assessment_ids") or []
                    if preds:
                        for p in preds:
                            st.write(f"- Assessment ID: `{p}`")
                    else:
                        st.caption("No predictive assessment IDs explicitly tagged.")

                with col_ev2:
                    st.markdown("##### Visual Health & Camera Evidence")
                    visuals = cons_obj.get("visual_evidence_ids") or []
                    if visuals:
                        for v in visuals:
                            st.write(f"- Visual Analysis / Image ID: `{v}`")
                    else:
                        st.caption("No visual evidence IDs tagged.")

                    st.markdown("##### Surveillance Context")
                    surv = cons_obj.get("surveillance_context") or {}
                    if surv:
                        st.json(surv)
                    else:
                        st.caption("Standard low-risk surveillance baseline.")

    # ============================================================
    # TAB 6: CLINICAL NOTES
    # ============================================================
    with tab6:
        st.subheader("6. Clinical Notes & Observations")
        st.caption("Multi-party clinical notes. Farmers record symptom observations; Veterinarians record objective assessment.")

        sel_note_cons = st.selectbox(
            "Select Consultation for Notes",
            options=[c.get("consultation_id") for c in all_consultations] if all_consultations else ["None"],
            key="sel_note_cons"
        )

        if sel_note_cons and sel_note_cons != "None":
            notes = api_client.get_clinical_notes(sel_note_cons) or []
            st.markdown(f"**Existing Notes ({len(notes)}):**")
            for n in notes:
                author_badge = "🩺 VETERINARIAN" if n.get("author_role") == "veterinarian" else "🌾 FARMER"
                assessment_part = f"<div style='margin-top: 0.35rem; font-size: 0.85rem; color: #38BDF8;'><b>Assessment:</b> {n.get('assessment')}</div>" if n.get('assessment') else ""
                note_html = (
                    f'<div style="border: 1px solid #273449; border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.6rem; background: #151F2E;">'
                    f'<div style="display: flex; justify-content: space-between; font-size: 0.85rem;">'
                    f'<b style="color: #F8FAFC;">{n.get("author_name", "Author")} <span style="color: #38BDF8; font-weight: 600;">({author_badge})</span></b>'
                    f'<span style="color: #94A3B8;">{n.get("created_at", "")}</span>'
                    f'</div>'
                    f'<div style="margin-top: 0.4rem; font-size: 0.92rem; color: #CBD5E1; line-height: 1.5;">{n.get("note_text")}</div>'
                    f'{assessment_part}'
                    f'</div>'
                )
                st.markdown(note_html, unsafe_allow_html=True)

            with st.expander("✍️ Add Clinical Note", expanded=True):
                with st.form("form_add_note"):
                    note_content = st.text_area("Note / Observations *", placeholder="Enter symptoms or clinical progress...")
                    if user_role in ["veterinarian", "admin"]:
                        note_subj = st.text_input("Subjective Findings (Optional)")
                        note_obj = st.text_input("Objective Clinical Findings (Optional)")
                        note_assess = st.text_input("Medical Assessment / Diagnosis (Vet Only)")
                    else:
                        st.info("ℹ️ As a farmer, you may enter symptom observations. Clinical medical diagnosis is reserved for licensed veterinarians.")
                        note_subj, note_obj, note_assess = None, None, None

                    if st.form_submit_button("Post Note"):
                        if not note_content:
                            st.error("Note content is required.")
                        else:
                            ndata = {"note_text": note_content}
                            if note_subj:
                                ndata["subjective"] = note_subj
                            if note_obj:
                                ndata["objective"] = note_obj
                            if note_assess:
                                ndata["assessment"] = note_assess

                            ok, res = api_client.add_clinical_note(sel_note_cons, ndata)
                            if ok:
                                st.success("Note added successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to post note: {res}")

    # ============================================================
    # TAB 7: TREATMENT
    # ============================================================
    with tab7:
        st.subheader("7. Treatment Integration")
        st.caption("Veterinarian-guided medication, supportive therapies, and treatment plans.")
        st.info("Treatment plans in VETRA require clinical veterinary oversight and are linked to animal medical history.")

        # Show completed or active consultations with recommendations
        treated_cons = [c for c in all_consultations if c.get("recommendations")]
        if not treated_cons:
            st.info("No active treatment recommendations recorded across consultations.")
        else:
            for tc in treated_cons:
                with st.expander(f"Treatment Plan — Consultation {tc.get('consultation_id')} (Animal {tc.get('animal_id')})"):
                    st.write(f"**Recommendations:** {tc.get('recommendations')}")
                    st.write(f"**Clinical Summary:** {tc.get('clinical_summary') or 'N/A'}")
                    st.write(f"**Follow-Up Target:** `{tc.get('follow_up_date') or 'Not specified'}`")

    # ============================================================
    # TAB 8: FOLLOW-UP
    # ============================================================
    with tab8:
        st.subheader("8. Follow-Up Management")
        st.caption("Scheduled reassessments to verify patient recovery and treatment efficacy.")

        follow_up_cons = [c for c in all_consultations if c.get("follow_up_required") or c.get("follow_up_date")]
        if not follow_up_cons:
            st.info("No consultations currently flagged for clinical follow-up.")
        else:
            for fc in follow_up_cons:
                st.markdown(
                    f"""
                    <div style="border: 1px solid #fed7aa; background: #fff7ed; padding: 0.8rem; border-radius: 6px; margin-bottom: 0.6rem;">
                        <b>Consultation:</b> {fc.get('consultation_id')} | <b>Animal:</b> {fc.get('animal_id')} | <b>Farm:</b> {fc.get('farm_id')}<br>
                        <b>Follow-Up Target Date:</b> <span style="color: #c2410c; font-weight: 700;">{fc.get('follow_up_date') or 'Pending Date'}</span><br>
                        <i>Status:</i> {fc.get('status')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # ============================================================
    # TAB 9: CONSULTATION HISTORY
    # ============================================================
    with tab9:
        st.subheader("9. Telemedicine History & Audit")
        st.caption("Archive of all completed, resolved, and cancelled consultations.")

        historical_cons = [c for c in all_consultations if c.get("status") in ["completed", "cancelled", "resolved"]]
        if not historical_cons:
            st.info("No completed consultation records in the archive yet.")
        else:
            for hc in historical_cons:
                with st.expander(f"{hc.get('consultation_id')} — {hc.get('animal_id')} ({hc.get('status').upper()})"):
                    st.write(f"**Complaint:** {hc.get('chief_complaint')}")
                    st.write(f"**Summary:** {hc.get('clinical_summary') or 'None'}")
                    st.write(f"**Recommendations:** {hc.get('recommendations') or 'None'}")
                    st.write(f"**Completed At:** {hc.get('ended_at') or hc.get('updated_at')}")

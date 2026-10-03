import streamlit as st
from datetime import date, datetime

import api_client
from session import get_user_info
from styles import page_header


def _format_date(val):
    if not val:
        return "-"
    return str(val)[:10]


def render_veterinarian_page():
    """
    Veterinary Workflow & Case Management System (Phase 6.6)
    Connects Alerts -> Animals -> AI Intelligence -> Clinical Cases -> Treatment -> Resolution.
    """
    page_header("🩺 Veterinary Clinical Case Management", "Early warning triage, clinical diagnoses, precision treatments, and medical case tracking")

    user = get_user_info()
    user_role = str(user.get("role", "farmer")).lower()
    user_id = user.get("id")
    is_vet_or_admin = user_role in ["veterinarian", "admin"]

    # Load base lookups
    with st.spinner("Loading clinical registry..."):
        animals = api_client.get_animals()
        vets = api_client.get_veterinarians()
        cases = api_client.get_veterinary_cases(limit=200)

    animal_lookup = {a["id"]: a for a in animals}

    # Case Selection State
    selected_case_id = st.session_state.get("selected_case_id")

    # ============================================================
    # TOP METRICS (COMMAND CENTER)
    # ============================================================
    open_count = sum(1 for c in cases if c.get("status") in ["open", "assigned"])
    crit_count = sum(1 for c in cases if c.get("priority") == "critical" and c.get("status") not in ["resolved", "closed"])
    review_count = sum(1 for c in cases if c.get("status") == "in_review")
    tx_count = sum(1 for c in cases if c.get("status") == "treatment")
    fup_count = sum(1 for c in cases if c.get("status") == "follow_up")
    res_count = sum(1 for c in cases if c.get("status") in ["resolved", "closed"])

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("Open Cases", open_count)
    with m2:
        st.metric("Critical Cases", crit_count)
    with m3:
        st.metric("Awaiting Review", review_count)
    with m4:
        st.metric("In Treatment", tx_count)
    with m5:
        st.metric("Follow-ups Due", fup_count)
    with m6:
        st.metric("Resolved Cases", res_count)

    st.markdown("---")

    # ============================================================
    # IF A CASE IS SELECTED -> RENDER CASE DETAIL VIEW
    # ============================================================
    if selected_case_id:
        current_case = api_client.get_veterinary_case(selected_case_id)
        if not current_case:
            st.error("Case not found or access denied.")
            if st.button("⬅️ Back to Cases Queue"):
                st.session_state["selected_case_id"] = None
                st.rerun()
            return

        _render_case_detail_view(current_case, animal_lookup, vets, is_vet_or_admin, user)
        return

    # ============================================================
    # VETERINARY NETWORK DIRECTORY (PHASE 12)
    # ============================================================
    with st.expander("🌐 Veterinary Network Directory & Availability", expanded=False):
        st.caption("Registered veterinarians, clinical specializations, regional coverage, and real-time consultation availability.")
        vet_profiles = api_client.get_veterinary_profiles() or []
        if not vet_profiles:
            st.info("No veterinary profiles found in the directory.")
        else:
            for vp in vet_profiles:
                avail_color = "rgba(34, 197, 94, 0.15)" if vp.get("availability_status") == "available" else "rgba(148, 163, 184, 0.15)"
                avail_text_color = "#4ade80" if vp.get("availability_status") == "available" else "#94a3b8"
                verif_color = "#22c55e" if vp.get("verification_status") == "verified" else "#f59e0b"
                st.markdown(
                    f"""
                    <div style="border: 1px solid #273449; border-radius: 8px; padding: 0.8rem; margin-bottom: 0.6rem; background: #151F2E;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b style="color: #F8FAFC;">Dr. {vp.get('name', 'Veterinarian')}</b>
                            <span style="background: {avail_color}; color: {avail_text_color}; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                                {str(vp.get('availability_status', 'offline')).upper()}
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 0.3rem; line-height: 1.5;">
                            <b>Specialization:</b> {vp.get('specialization', 'General')} | <b>Experience:</b> {vp.get('experience_years', 0)} yrs<br>
                            <b>Species:</b> {', '.join(vp.get('supported_species') or ['bovine'])}<br>
                            <b>Regions:</b> {', '.join(vp.get('service_regions') or ['All'])}<br>
                            <b>Modes:</b> {', '.join(vp.get('consultation_modes') or ['in_person', 'telemedicine'])}<br>
                            <b>Verification:</b> <span style="color: {verif_color}; font-weight: 600;">{vp.get('verification_status', 'unverified')}</span> | 
                            <b>Registration Ref:</b> <code>{vp.get('registration_reference', 'NOT_PROVIDED')}</code>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # ============================================================
    # CASE QUEUE VIEW
    # ============================================================
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.subheader("📋 Priority Clinical Case Queue")
    with top_col2:
        with st.popover("➕ Open New Case", use_container_width=True):
            st.markdown("##### Create Veterinary Case")
            with st.form("quick_case_create_form", clear_on_submit=True):
                animal_options = {f"{a.get('name', 'Animal')} ({a.get('tag_id', 'TAG')})": a["id"] for a in animals}
                sel_animal_label = st.selectbox("Select Animal", options=list(animal_options.keys()))
                c_title = st.text_input("Case Title", placeholder="e.g. Mastitis Suspect / Fever Triage")
                c_type = st.selectbox(
                    "Case Type",
                    options=["health_alert", "preventive_follow_up", "routine_checkup", "suspected_disease", "treatment", "vaccination", "deworming", "other"],
                    format_func=lambda s: s.replace("_", " ").title()
                )
                c_priority = st.selectbox("Priority", options=["critical", "high", "medium", "low"], format_func=lambda s: s.upper())
                c_desc = st.text_area("Symptoms & Clinical History")

                vet_options = {"Unassigned": None}
                for v in vets:
                    vet_options[f"Dr. {v.get('full_name')} ({v.get('role').title()})"] = v["id"]
                sel_vet_label = st.selectbox("Assign Initial Veterinarian", options=list(vet_options.keys()))

                create_submitted = st.form_submit_button("Submit Case", use_container_width=True, type="primary")
                if create_submitted:
                    if sel_animal_label and c_title:
                        a_id = animal_options[sel_animal_label]
                        assigned_v_id = vet_options[sel_vet_label]
                        assigned_v_name = sel_vet_label if assigned_v_id else None

                        payload = {
                            "animal_id": a_id,
                            "title": c_title.strip(),
                            "description": c_desc.strip() if c_desc else None,
                            "case_type": c_type,
                            "priority": c_priority,
                            "source": "manual",
                            "assigned_veterinarian_id": assigned_v_id,
                            "assigned_veterinarian_name": assigned_v_name
                        }
                        ok, res = api_client.create_veterinary_case(payload)
                        if ok:
                            st.success(f"Case {res.get('case_number')} created successfully!")
                            st.rerun()
                        else:
                            st.error(str(res))
                    else:
                        st.error("Please provide an animal and case title.")

    # Filter row
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        f_status = st.selectbox(
            "Filter Status",
            options=["All", "open", "assigned", "in_review", "treatment", "follow_up", "resolved", "closed"],
            format_func=lambda s: "All Statuses" if s == "All" else s.replace("_", " ").title()
        )
    with f_col2:
        f_priority = st.selectbox(
            "Filter Priority",
            options=["All", "critical", "high", "medium", "low"],
            format_func=lambda s: "All Priorities" if s == "All" else s.upper()
        )
    with f_col3:
        f_type = st.selectbox(
            "Filter Type",
            options=["All", "health_alert", "preventive_follow_up", "routine_checkup", "suspected_disease", "treatment", "vaccination", "deworming", "other"],
            format_func=lambda s: "All Types" if s == "All" else s.replace("_", " ").title()
        )
    with f_col4:
        vet_filter_opts = ["All"] + [f"{v.get('full_name')}" for v in vets]
        f_vet = st.selectbox("Assigned Veterinarian", options=vet_filter_opts)

    # Filter execution
    filtered_cases = cases
    if f_status != "All":
        filtered_cases = [c for c in filtered_cases if c.get("status") == f_status]
    if f_priority != "All":
        filtered_cases = [c for c in filtered_cases if c.get("priority") == f_priority]
    if f_type != "All":
        filtered_cases = [c for c in filtered_cases if c.get("case_type") == f_type]
    if f_vet != "All":
        filtered_cases = [c for c in filtered_cases if c.get("assigned_veterinarian_name") and f_vet in str(c.get("assigned_veterinarian_name"))]

    if not filtered_cases:
        st.info("🟢 No clinical cases matching the selected filters.")
        return

    st.caption(f"Showing {len(filtered_cases)} case(s)")

    # Render cases list
    for c in filtered_cases:
        cid = c["id"]
        cnum = c.get("case_number", "CASE")
        cprio = c.get("priority", "medium").lower()
        cstat = c.get("status", "open").lower()
        ctype = c.get("case_type", "routine_checkup").replace("_", " ").title()
        csource = c.get("source", "manual").replace("_", " ").title()
        animal_id = c.get("animal_id")
        animal = animal_lookup.get(animal_id, {})
        aname = animal.get("name", "Unknown Animal")
        atag = animal.get("tag_id", "TAG-?")

        prio_color = "#dc2626" if cprio == "critical" else ("#ea580c" if cprio == "high" else ("#0284c7" if cprio == "medium" else "#16a34a"))
        stat_color = "#16a34a" if cstat in ["resolved", "closed"] else ("#f59e0b" if cstat in ["treatment", "in_review"] else "#64748b")

        with st.container():
            st.markdown(
                f"""
                <div style="background: #151F2E; border: 1px solid #273449; border-left: 5px solid {prio_color}; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 800; font-size: 1.05rem; color: #F8FAFC;">{cnum}</span>
                            &nbsp;•&nbsp;
                            <span style="background: {prio_color}25; color: {prio_color}; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid {prio_color}50;">{cprio.upper()}</span>
                            &nbsp;
                            <span style="background: {stat_color}25; color: {stat_color}; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid {stat_color}50;">{cstat.replace('_', ' ').upper()}</span>
                            &nbsp;
                            <span style="background: #1B2638; color: #94A3B8; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #273449;">{ctype}</span>
                        </div>
                        <span style="font-size: 0.8rem; color: #94A3B8;">
                            🕒 Created: {_format_date(c.get('created_at'))}
                        </span>
                    </div>
                    <div style="font-size: 1rem; font-weight: 600; color: #F8FAFC; margin-top: 0.5rem;">
                        {c.get('title')}
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 0.35rem;">
                        <strong>Animal:</strong> {aname} (<code>{atag}</code>) &nbsp;•&nbsp; 
                        <strong>Assigned Vet:</strong> {c.get('assigned_veterinarian_name') or '<em>Unassigned</em>'} &nbsp;•&nbsp; 
                        <strong>Source:</strong> {csource} &nbsp;•&nbsp; 
                        <strong>Follow-up:</strong> {_format_date(c.get('follow_up_date'))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 4])
            with col_btn1:
                if st.button("🔍 Open Case Detail", key=f"btn_open_{cid}", use_container_width=True, type="primary"):
                    st.session_state["selected_case_id"] = cid
                    st.rerun()

            with col_btn2:
                if is_vet_or_admin and cstat not in ["resolved", "closed"]:
                    if st.button("✅ Quick Resolve", key=f"btn_qres_{cid}", use_container_width=True):
                        api_client.resolve_veterinary_case(cid, summary="Quick clinical resolution via queue.")
                        st.success("Case marked resolved.")
                        st.rerun()

            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)


# ============================================================
# CASE DETAIL VIEW
# ============================================================
def _render_case_detail_view(case, animal_lookup, vets, is_vet_or_admin, current_user):
    cid = case["id"]
    cnum = case.get("case_number", "CASE")
    cstatus = case.get("status", "open")
    cpriority = case.get("priority", "medium")
    animal_id = case.get("animal_id")
    animal = animal_lookup.get(animal_id, {})

    # Top Navigation Back
    top_nav1, top_nav2 = st.columns([1, 4])
    with top_nav1:
        if st.button("⬅️ Back to Queue", key="back_to_queue_btn", use_container_width=True):
            st.session_state["selected_case_id"] = None
            st.rerun()

    with top_nav2:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; margin-top: 5px;">
                <span style="font-size: 1.3rem; font-weight: 800; color: #F8FAFC;">{cnum}: {case.get('title')}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Detailed Tabs
    tab_overview, tab_ai, tab_clinical, tab_treatment, tab_timeline, tab_actions = st.tabs([
        "📋 Overview & Vitals",
        "🤖 AI Decision Support",
        "🩺 Clinical Assessment",
        "💊 Treatment & Rx",
        "📜 Case Timeline",
        "⚡ Workflow Actions"
    ])

    # ----------------------------------------------------
    # TAB 1: OVERVIEW & VITALS
    # ----------------------------------------------------
    with tab_overview:
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.markdown("##### Case Metadata")
            st.markdown(
                f"""
                - **Case ID:** `{cid}`
                - **Case Number:** `{cnum}`
                - **Type:** {case.get('case_type', '').replace('_', ' ').title()}
                - **Priority:** `{cpriority.upper()}`
                - **Status:** `{cstatus.upper()}`
                - **Source:** {case.get('source', '').replace('_', ' ').title()}
                - **Created At:** {case.get('created_at', '')[:19]}
                - **Follow-up Date:** {_format_date(case.get('follow_up_date'))}
                - **Assigned Veterinarian:** {case.get('assigned_veterinarian_name') or 'Unassigned'}
                """
            )
            if case.get("description"):
                st.info(f"**Case Description / Patient History:**\n\n{case.get('description')}")

            if case.get("alert_id"):
                st.markdown("##### 🚨 Linked Alert Context")
                st.markdown(
                    f"""
                    <div style="background: #fff1f2; border: 1px solid #fecdd3; border-radius: 6px; padding: 0.75rem;">
                        <strong>Linked Alert ID:</strong> <code>{case.get('alert_id')}</code><br>
                        <strong>Escalation Reason:</strong> Automatically generated from abnormal physiological / preventive alert.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with c2:
            st.markdown("##### 🐄 Animal Profile")
            st.markdown(
                f"""
                - **Name:** {animal.get('name', 'Unknown')}
                - **Tag ID:** `{animal.get('tag_id', 'TAG')}`
                - **Species:** {animal.get('species', 'Bovine').title()}
                - **Breed:** {animal.get('breed', 'Unknown')}
                - **Age:** {animal.get('age_years', '-')} years
                - **Gender:** {animal.get('gender', '-').title()}
                - **Farm ID:** `{case.get('farm_id')}`
                """
            )

            # Fetch vitals snapshot
            readings = api_client.get_health_readings(animal_id)
            if readings:
                latest = readings[0]
                st.markdown("##### 📡 Latest Vitals Telemetry")
                v1, v2 = st.columns(2)
                with v1:
                    st.metric("Temperature", f"{latest.get('temperature_c', 0):.1f} °C")
                    st.metric("Heart Rate", f"{latest.get('heart_rate_bpm', 0):.0f} BPM")
                with v2:
                    st.metric("Respiration", f"{latest.get('respiratory_rate', 0):.0f} /min")
                    st.metric("Rumination", f"{latest.get('rumination_level', 0):.1f}%")
            else:
                st.caption("No telemetry readings recorded for this animal.")

    # ----------------------------------------------------
    # TAB 2: AI DECISION SUPPORT
    # ----------------------------------------------------
    with tab_ai:
        st.markdown(
            """
            <div style="background: #151F2E; border: 1px solid #273449; border-left: 4px solid #38BDF8; padding: 0.85rem 1.15rem; border-radius: 8px; margin-bottom: 1rem;">
                <strong style="color: #F8FAFC;">⚠️ AI Decision Support — Veterinary Review Required</strong><br>
                <span style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.5; display: inline-block; margin-top: 0.25rem;">
                    AI generated outputs represent predictive pattern recognition across physiological telemetry and herd data.
                    They are intended solely for triage and decision-support, and do not constitute a confirmed medical diagnosis.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        ai_data = api_client.get_ai_assessment(animal_id)
        if ai_data:
            a_col1, a_col2, a_col3 = st.columns(3)
            with a_col1:
                st.metric("Health Risk Score", f"{ai_data.get('risk_score', 0):.0f}/100")
            with a_col2:
                st.metric("Disease Risk Category", str(ai_data.get("risk_category", "LOW")).upper())
            with a_col3:
                st.metric("Vital Stability", f"{ai_data.get('vital_stability_score', 0):.1f}%")

            st.markdown("##### Clinical Pattern Analysis")
            st.write(ai_data.get("clinical_interpretation", "No interpretation generated."))

            st.markdown("##### Suggested Clinical Action")
            st.info(f"💡 {ai_data.get('recommended_action', 'Continue standard veterinary monitoring.')}")

            if ai_data.get("contributing_factors"):
                st.markdown("##### Contributing Physiological Abnormalities")
                for factor in ai_data.get("contributing_factors", []):
                    st.markdown(f"- ⚠️ {factor}")
        else:
            st.info("AI assessment not available for this case.")

    # ----------------------------------------------------
    # TAB 3: CLINICAL ASSESSMENT & DIAGNOSIS
    # ----------------------------------------------------
    with tab_clinical:
        st.markdown("##### Veterinary Diagnosis & Findings")

        findings = case.get("clinical_findings")
        diagnosis = case.get("diagnosis")

        st.markdown(f"**Objective Clinical Findings:**")
        if findings:
            st.markdown(f"> {findings}")
        else:
            st.caption("No clinical findings recorded yet.")

        st.markdown(f"**Confirmed Diagnosis:**")
        if diagnosis:
            st.success(f"🩺 **Diagnosis:** {diagnosis}")
        else:
            st.caption("No formal diagnosis recorded yet.")

        if is_vet_or_admin:
            st.markdown("---")
            st.markdown("##### 📝 Update Assessment & Diagnosis")
            with st.form(f"update_clinical_form_{cid}"):
                up_findings = st.text_area("Clinical Findings / Examination Notes", value=findings or "")
                up_diagnosis = st.text_input("Definitive / Provisional Diagnosis", value=diagnosis or "")
                up_notes = st.text_input("Timeline Note (Optional)", placeholder="e.g. Physical exam performed, lungs clear")
                submit_clinical = st.form_submit_button("Save Clinical Assessment", type="primary")

                if submit_clinical:
                    ok, res = api_client.update_veterinary_case(cid, {
                        "clinical_findings": up_findings.strip() if up_findings else None,
                        "diagnosis": up_diagnosis.strip() if up_diagnosis else None,
                        "notes": up_notes.strip() if up_notes else None
                    })
                    if ok:
                        st.success("Clinical assessment updated successfully.")
                        st.rerun()
                    else:
                        st.error(str(res))

    # ----------------------------------------------------
    # TAB 4: TREATMENT & RX
    # ----------------------------------------------------
    with tab_treatment:
        st.markdown("##### Treatment Plan & Prescriptions")

        tx_plan = case.get("treatment_plan")
        recs = case.get("recommendations")
        meds = case.get("medications", [])
        fup = case.get("follow_up_date")

        st.markdown(f"**Treatment Strategy:**")
        if tx_plan:
            st.info(tx_plan)
        else:
            st.caption("No treatment plan defined yet.")

        st.markdown(f"**Prescribed Medications:**")
        if meds:
            for idx, m in enumerate(meds, 1):
                st.markdown(
                    f"""
                    <div style="background: #151F2E; border: 1px solid #273449; border-left: 3px solid #38BDF8; padding: 0.65rem 0.85rem; border-radius: 6px; margin-bottom: 0.5rem;">
                        <strong style="color: #F8FAFC;">{idx}. {m.get('name')}</strong> &nbsp;•&nbsp; 
                        <span style="color: #CBD5E1;">Dosage:</span> <code>{m.get('dosage', '-')}</code> &nbsp;•&nbsp; 
                        <span style="color: #CBD5E1;">Frequency:</span> <code>{m.get('frequency', '-')}</code> &nbsp;•&nbsp; 
                        <span style="color: #CBD5E1;">Duration:</span> <code>{m.get('duration', '-')}</code>
                        <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 0.25rem;">Instructions: {m.get('instructions', '-')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.caption("No medications currently prescribed.")

        st.markdown(f"**Herd & Biosecurity Recommendations:**")
        if recs:
            st.markdown(f"> {recs}")
        else:
            st.caption("No special recommendations provided.")

        st.markdown(f"**Scheduled Follow-up Date:** `{_format_date(fup)}`")

        if is_vet_or_admin:
            st.markdown("---")
            st.markdown("##### 💊 Prescribe Intervention / Update Rx")
            with st.form(f"update_treatment_form_{cid}"):
                up_plan = st.text_area("Treatment Plan", value=tx_plan or "")
                up_recs = st.text_area("Recommendations for Herd Manager / Farmer", value=recs or "")
                up_fupdate = st.date_input("Follow-up Review Date", value=date.today())

                st.markdown("**Add Medication (Optional)**")
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    m_name = st.text_input("Medication Name", placeholder="e.g. Enrofloxacin 10%")
                    m_dose = st.text_input("Dosage", placeholder="e.g. 5ml/100kg")
                with m_col2:
                    m_freq = st.text_input("Frequency", placeholder="e.g. Once daily IM")
                    m_dur = st.text_input("Duration", placeholder="e.g. 3 consecutive days")
                m_inst = st.text_input("Special Administration Instructions", placeholder="e.g. Keep animal hydrated, monitor rumination")

                submit_tx = st.form_submit_button("Update Treatment & Prescriptions", type="primary")

                if submit_tx:
                    updated_meds = list(meds)
                    if m_name.strip():
                        updated_meds.append({
                            "name": m_name.strip(),
                            "dosage": m_dose.strip() or None,
                            "frequency": m_freq.strip() or None,
                            "duration": m_dur.strip() or None,
                            "instructions": m_inst.strip() or None
                        })

                    ok, res = api_client.update_veterinary_case(cid, {
                        "treatment_plan": up_plan.strip() if up_plan else None,
                        "recommendations": up_recs.strip() if up_recs else None,
                        "follow_up_date": up_fupdate.isoformat() if up_fupdate else None,
                        "medications": updated_meds
                    })
                    if ok:
                        st.success("Treatment plan updated.")
                        st.rerun()
                    else:
                        st.error(str(res))

    # ----------------------------------------------------
    # TAB 5: CASE TIMELINE
    # ----------------------------------------------------
    with tab_timeline:
        st.markdown("##### 📜 Clinical Audit Timeline")
        timeline = case.get("timeline", [])

        if timeline:
            for ev in reversed(timeline):
                t_title = ev.get("title", "Update")
                t_desc = ev.get("description", "")
                t_user = ev.get("performed_by_name") or ev.get("performed_by", "User")
                t_role = ev.get("performed_by_role", "user").upper()
                t_time = ev.get("timestamp", "")[:19].replace("T", " ")

                st.markdown(
                    f"""
                    <div style="border-left: 3px solid #22C55E; padding-left: 1rem; margin-bottom: 1rem; position: relative;">
                        <div style="font-weight: 700; color: #F8FAFC; font-size: 0.95rem;">{t_title}</div>
                        <div style="color: #CBD5E1; font-size: 0.85rem; margin-top: 0.2rem; line-height: 1.4;">{t_desc}</div>
                        <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 0.25rem;">
                            🕒 {t_time} &nbsp;•&nbsp; By: <strong style="color: #38BDF8;">{t_user}</strong> ({t_role})
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No timeline events recorded.")

        st.markdown("---")
        with st.form(f"add_timeline_note_{cid}", clear_on_submit=True):
            note_text = st.text_input("Add Case Progress Note", placeholder="Enter observation or clinical update...")
            if st.form_submit_button("Post Note"):
                if note_text.strip():
                    ok, res = api_client.update_veterinary_case(cid, {"notes": note_text.strip()})
                    if ok:
                        st.success("Note added to timeline.")
                        st.rerun()
                    else:
                        st.error(str(res))

    # ----------------------------------------------------
    # TAB 6: WORKFLOW ACTIONS
    # ----------------------------------------------------
    with tab_actions:
        st.markdown("##### ⚡ Workflow State Management")

        if is_vet_or_admin:
            act_col1, act_col2 = st.columns(2)

            with act_col1:
                st.markdown("###### Assign Case")
                with st.form(f"assign_form_{cid}"):
                    vet_map = {f"Dr. {v.get('full_name')}": v["id"] for v in vets}
                    sel_v_name = st.selectbox("Select Veterinarian", options=list(vet_map.keys()))
                    assign_note = st.text_input("Assignment Note", placeholder="e.g. Assigned for specialized review")
                    if st.form_submit_button("Assign Case"):
                        v_id = vet_map[sel_v_name]
                        ok, res = api_client.assign_veterinary_case(cid, v_id, sel_v_name, assign_note)
                        if ok:
                            st.success(f"Case assigned to {sel_v_name}.")
                            st.rerun()
                        else:
                            st.error(str(res))

                st.markdown("###### Status Transitions")
                b_c1, b_c2 = st.columns(2)
                with b_c1:
                    if st.button("🔍 Start Review", use_container_width=True):
                        api_client.update_case_status(cid, "in_review", "Veterinarian started clinical review.")
                        st.rerun()
                with b_c2:
                    if st.button("💊 Move to Treatment", use_container_width=True):
                        api_client.update_case_status(cid, "treatment", "Case entered active treatment phase.")
                        st.rerun()

                b_c3, b_c4 = st.columns(2)
                with b_c3:
                    if st.button("📅 Schedule Follow-up", use_container_width=True):
                        api_client.update_case_status(cid, "follow_up", "Case scheduled for follow-up evaluation.")
                        st.rerun()
                with b_c4:
                    if st.button("🔒 Close Case", use_container_width=True):
                        api_client.update_case_status(cid, "closed", "Case officially closed.")
                        st.rerun()

            with act_col2:
                st.markdown("###### Complete & Resolve Case")
                with st.form(f"resolve_form_{cid}"):
                    st.caption("Resolving this case will record final clinical outcomes and resolve any linked alert.")
                    final_dx = st.text_input("Final Diagnosis", value=case.get("diagnosis") or "")
                    res_summary = st.text_area("Resolution Summary", placeholder="e.g. Symptoms resolved after antibiotic therapy; vital signs stabilized.")
                    final_recs = st.text_area("Ongoing Recommendations", value=case.get("recommendations") or "")
                    resolve_btn = st.form_submit_button("✅ Confirm Case Resolution", type="primary", use_container_width=True)

                    if resolve_btn:
                        ok, res = api_client.resolve_veterinary_case(
                            cid,
                            summary=res_summary.strip() if res_summary else None,
                            final_diagnosis=final_dx.strip() if final_dx else None,
                            recommendations=final_recs.strip() if final_recs else None
                        )
                        if ok:
                            st.success("Case resolved successfully!")
                            st.rerun()
                        else:
                            st.error(str(res))

        else:
            st.info("As a Farmer, you can review the clinical progress, recommendations, and post notes on the Case Timeline.")
            with st.form(f"farmer_note_form_{cid}"):
                f_note = st.text_area("Submit Information / Response to Veterinarian", placeholder="e.g. Animal consumed normal feed this morning, temperature checked.")
                if st.form_submit_button("Send Update to Veterinarian"):
                    if f_note.strip():
                        ok, res = api_client.update_veterinary_case(cid, {"notes": f_note.strip()})
                        if ok:
                            st.success("Information submitted to veterinarian.")
                            st.rerun()
                        else:
                            st.error(str(res))

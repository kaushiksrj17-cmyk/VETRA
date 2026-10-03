import io
from datetime import date

import streamlit as st

import api_client


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_date(value):
    if not value:
        return "-"
    return str(value)[:10]


def _display_record(record):
    """
    Generic record display helper.
    Keeps the UI stable even when optional fields are missing.
    """
    if not record:
        st.info("No records available.")
        return

    with st.container(border=True):
        for key, value in record.items():
            if key in {"id", "_id", "animal_id", "farm_id"}:
                continue

            label = str(key).replace("_", " ").title()

            if isinstance(value, dict):
                st.markdown(f"**{label}**")
                st.json(value)
            elif isinstance(value, list):
                st.markdown(f"**{label}**")
                for item in value:
                    st.write(f"- {item}")
            else:
                st.markdown(f"**{label}:** {value}")


def render_animal_profile_page():
    """
    Render the complete VETRA Animal Health Profile.

    Sections:
    - Animal identity
    - QR identity
    - AI health assessment
    - Disease intelligence
    - Early-warning intelligence
    - Vitals telemetry
    - Vaccinations
    - Deworming
    - Treatments
    - Veterinary visits
    """

    # ============================================================
    # LOAD ANIMALS
    # ============================================================

    animals = api_client.get_animals()

    if not animals:
        st.warning("No animals are available.")
        return

    selected_animal_id = st.session_state.get("selected_animal_id")

    if not selected_animal_id:
        selected_animal_id = animals[0].get("id")

    animal_ids = [
        animal.get("id")
        for animal in animals
        if animal.get("id")
    ]

    if selected_animal_id not in animal_ids:
        selected_animal_id = animal_ids[0]

    selected_animal = next(
        (
            animal
            for animal in animals
            if animal.get("id") == selected_animal_id
        ),
        animals[0],
    )

    st.session_state["selected_animal_id"] = selected_animal_id

    # ============================================================
    # PAGE HEADER
    # ============================================================

    animal_name = selected_animal.get("name") or "Unnamed Animal"
    tag_id = selected_animal.get("tag_id") or "N/A"
    species = selected_animal.get("species") or "N/A"
    breed = selected_animal.get("breed") or "N/A"

    st.markdown(
        f"""
        <div class="vetra-header" style="margin-bottom: 1rem;">
            <div class="vetra-brand">
                Animal Health Profile
            </div>
            <div class="vetra-tagline">
                Individual livestock identity, telemetry, AI screening and veterinary history
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # ANIMAL SELECTOR
    # ============================================================

    animal_options = {
        animal.get("id"): (
            f"{animal.get('name') or 'Unnamed Animal'} "
            f"({animal.get('tag_id') or 'No Tag'})"
        )
        for animal in animals
        if animal.get("id")
    }

    selected_animal_id = st.selectbox(
        "Select Animal",
        options=list(animal_options.keys()),
        index=list(animal_options.keys()).index(selected_animal_id),
        format_func=lambda animal_id: animal_options[animal_id],
        key="animal_profile_selector",
    )

    selected_animal = next(
        (
            animal
            for animal in animals
            if animal.get("id") == selected_animal_id
        ),
        animals[0],
    )

    st.session_state["selected_animal_id"] = selected_animal_id

    animal_name = selected_animal.get("name") or "Unnamed Animal"
    tag_id = selected_animal.get("tag_id") or "N/A"
    species = selected_animal.get("species") or "N/A"
    breed = selected_animal.get("breed") or "N/A"

    # ============================================================
    # ANIMAL IDENTITY
    # ============================================================

    st.markdown("### Animal Identity")

    identity_col1, identity_col2 = st.columns([2.5, 1])

    with identity_col1:
        with st.container(border=True):

            status = selected_animal.get(
                "health_status",
                "healthy"
            )

            st.markdown(
                f"""
                <div style="
                    font-size: 1.35rem;
                    font-weight: 800;
                    color: #F8FAFC;
                ">
                    {animal_name}
                </div>

                <div style="
                    color: #94A3B8;
                    margin-top: 0.25rem;
                ">
                    Tag ID: <strong style="color: #38BDF8;">{tag_id}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("---")

            info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.markdown("**Species**")
                st.write(species)

            with info_col2:
                st.markdown("**Breed**")
                st.write(breed)

            with info_col3:
                st.markdown("**Health Status**")
                st.write(str(status).upper())

            info_col4, info_col5, info_col6 = st.columns(3)

            with info_col4:
                st.markdown("**Gender**")
                st.write(
                    selected_animal.get("gender", "N/A")
                )

            with info_col5:
                st.markdown("**Date of Birth**")
                st.write(
                    _format_date(
                        selected_animal.get("date_of_birth")
                    )
                )

            with info_col6:
                st.markdown("**Weight**")
                st.write(
                    f"{_safe_float(selected_animal.get('weight_kg')):.1f} kg"
                )

    with identity_col2:
        with st.container(border=True):

            st.markdown("**QR Animal Identity**")

            farm_id = selected_animal.get("farm_id")

            qr_image = None

            if farm_id and selected_animal_id:
                try:
                    qr_image = api_client.get_animal_qr(
                        farm_id,
                        selected_animal_id
                    )
                except Exception:
                    qr_image = None

            if qr_image:
                try:
                    st.image(
                        io.BytesIO(qr_image),
                        caption=tag_id,
                        use_container_width=True,
                    )
                except Exception:
                    st.info("QR identity available.")
            else:
                st.info(
                    "QR identity is not currently available."
                )

    # ============================================================
    # LOAD AI REPORT
    # ============================================================

    with st.spinner("Loading VETRA health intelligence..."):
        ai_report = api_client.get_ai_assessment(
            selected_animal_id
        )

    if ai_report is None:
        ai_report = {}

    # ============================================================
    # TABS
    # ============================================================

    (
        tab_ai,
        tab_visual,
        tab_vitals,
        tab_cases,
        tab_vacc,
        tab_deworm,
        tab_treat,
        tab_visits,
    ) = st.tabs(
        [
            "AI Health Assessment",
            "👁️ Visual Health",
            "Vitals Telemetry",
            "Veterinary Cases",
            "Vaccinations",
            "Deworming",
            "Treatments",
            "Veterinary Visits",
        ]
    )

    # ============================================================
    # TAB 1 — AI HEALTH ASSESSMENT
    # ============================================================

    with tab_ai:

        st.markdown("### AI Health Assessment")

        risk_score = _safe_float(
            ai_report.get("risk_score", 0)
        )

        risk_category = str(
            ai_report.get(
                "risk_category",
                "low"
            )
        ).upper()

        trend_summary = ai_report.get(
            "trend_summary",
            "No trend information available."
        )

        stability_score = _safe_float(
            ai_report.get(
                "vital_stability_score",
                0
            )
        )

        metric_col1, metric_col2, metric_col3, metric_col4 = (
            st.columns(4)
        )

        with metric_col1:
            st.metric(
                "Health Risk Score",
                f"{risk_score:.0f}/100"
            )

        with metric_col2:
            st.metric(
                "Risk Classification",
                risk_category
            )

        with metric_col3:
            st.metric(
                "Vital Stability",
                f"{stability_score:.1f}%"
            )

        with metric_col4:
            st.metric(
                "Physiological Trend",
                str(trend_summary)
            )

        st.markdown("---")

        st.markdown("#### Clinical Decision-Support Summary")

        with st.container(border=True):
            st.write(
                ai_report.get(
                    "clinical_interpretation",
                    ai_report.get(
                        "ai_explanation",
                        "No clinical interpretation available."
                    )
                )
            )

        st.markdown("#### Recommended Action")

        with st.container(border=True):
            st.write(
                ai_report.get(
                    "recommended_action",
                    "Continue routine monitoring and preventive care."
                )
            )

        st.markdown("#### Monitoring Protocol")

        with st.container(border=True):
            st.write(
                ai_report.get(
                    "monitoring_recommendation",
                    "Continue routine telemetry monitoring."
                )
            )

        contributing_factors = ai_report.get(
            "contributing_factors",
            []
        )

        st.markdown("#### Contributing Telemetry Signals")

        if contributing_factors:
            for factor in contributing_factors:
                st.markdown(f"- {factor}")
        else:
            st.success(
                "No significant abnormal telemetry signals detected."
            )

        questions = ai_report.get(
            "questions_for_veterinarian",
            []
        )

        st.markdown("#### Clinical Examination Focus")

        if questions:
            for question in questions:
                st.markdown(f"- {question}")
        else:
            st.info(
                "No additional veterinary examination questions "
                "were generated."
            )

        # ========================================================
        # DISEASE INTELLIGENCE
        # ========================================================

        st.markdown("---")
        st.markdown(
            "#### Disease Intelligence & Early-Warning Screening"
        )

        disease_level = str(
            ai_report.get(
                "disease_risk_level",
                "low"
            )
        ).upper()

        disease_patterns = ai_report.get(
            "risk_patterns",
            []
        )

        disease_indicators = ai_report.get(
            "physiological_indicators",
            []
        )

        disease_recommendations = ai_report.get(
            "disease_recommendations",
            []
        )

        disease_col1, disease_col2 = st.columns(
            [1, 2]
        )

        with disease_col1:

            with st.container(border=True):

                st.markdown(
                    "**DISEASE RISK LEVEL**"
                )

                if disease_level == "HIGH":
                    st.error(disease_level)

                elif disease_level == "MODERATE":
                    st.warning(disease_level)

                else:
                    st.success(disease_level)

        with disease_col2:

            with st.container(border=True):

                st.markdown(
                    "**DETECTED RISK PATTERNS**"
                )

                if disease_patterns:

                    for pattern in disease_patterns:
                        st.markdown(
                            f"- {pattern}"
                        )

                else:

                    st.success(
                        "No significant disease-associated "
                        "physiological pattern detected."
                    )

        st.markdown("##### Physiological Indicators")

        if disease_indicators:

            for indicator in disease_indicators:
                st.info(indicator)

        else:

            st.success(
                "No significant disease-associated "
                "physiological indicators detected."
            )

        st.markdown(
            "##### Disease-Risk Recommendations"
        )

        if disease_recommendations:

            for recommendation in disease_recommendations:
                st.markdown(
                    f"- {recommendation}"
                )

        else:

            st.markdown(
                "- Continue routine telemetry monitoring "
                "and preventive healthcare."
            )

        screening_note = ai_report.get(
            "disease_screening_note",
            "Disease intelligence provides early-warning "
            "patterns for decision support and does not "
            "constitute a definitive diagnosis."
        )

        st.caption(
            f"Screening note: {screening_note}"
        )

        disease_engine = ai_report.get(
            "disease_engine_version",
            "VETRA-DiseaseIntelligence-v1.0"
        )

        st.caption(
            f"Disease Intelligence Engine: {disease_engine}"
        )

        # ========================================================
        # PHASE 8: HERD DISEASE SURVEILLANCE CONTEXT
        # ========================================================
        st.markdown("---")
        st.markdown("#### 🦠 Herd Disease Surveillance Context")
        st.caption("Epidemiological holding risk, active cluster association, and syndromic surveillance posture.")

        surv_col1, surv_col2 = st.columns([1, 1])
        with surv_col1:
            with st.container(border=True):
                st.markdown("**HOLDING SURVEILLANCE STATUS**")
                # Look up holding risk
                animal_farm_id = str(selected_animal.get("farm_id", ""))
                farm_risk_cat = "ROUTINE"
                farm_risk_score = 0.0
                try:
                    surv_farms = api_client.get_surveillance_farms()
                    target_f = next((f for f in surv_farms if f["farm_id"] == animal_farm_id), None)
                    if target_f:
                        farm_risk_cat = target_f.get("risk_category", "LOW")
                        farm_risk_score = target_f.get("risk_score", 0.0)
                except Exception:
                    pass

                st.metric("Holding Risk Category", f"{farm_risk_cat}", f"{farm_risk_score}/100")
                st.markdown(f"**Dominant Syndromic Pattern:** `{disease_patterns[0] if disease_patterns else 'Baseline'}`")

        with surv_col2:
            with st.container(border=True):
                st.markdown("**EPIDEMIOLOGICAL ACTIONS**")
                if disease_level in ["HIGH", "MODERATE"]:
                    st.warning("⚠️ Animal exhibits physiological deviations contributing to elevated surveillance risk.")
                    st.caption("Follow biosecurity isolation protocols if contagious syndrome is suspected.")
                else:
                    st.success("✅ Physiological telemetry aligns with healthy reference range. No syndromic cluster association.")

        # ========================================================
        # EARLY WARNING
        # ========================================================


        st.markdown("---")
        st.markdown(
            "#### AI Early-Warning & Dynamic Risk Detection"
        )

        early_warning_level = str(
            ai_report.get(
                "early_warning_level",
                "LOW"
            )
        ).upper()

        early_warning_score = _safe_float(
            ai_report.get(
                "early_warning_score",
                0
            )
        )

        deterioration_detected = bool(
            ai_report.get(
                "deterioration_detected",
                False
            )
        )

        early_warning_signals = ai_report.get(
            "early_warning_signals",
            []
        )

        early_warning_trend = ai_report.get(
            "early_warning_trend",
            "No significant deterioration pattern detected "
            "in recent telemetry."
        )

        early_warning_action = ai_report.get(
            "early_warning_action",
            "Continue routine telemetry monitoring "
            "and preventive care."
        )

        early_warning_engine = ai_report.get(
            "early_warning_engine_version",
            "VETRA-EarlyWarning-v1.0"
        )

        warning_col1, warning_col2, warning_col3 = (
            st.columns(3)
        )

        with warning_col1:

            with st.container(border=True):

                st.markdown(
                    "**EARLY-WARNING LEVEL**"
                )

                if early_warning_level == "CRITICAL":
                    st.error(early_warning_level)

                elif early_warning_level == "HIGH":
                    st.warning(early_warning_level)

                elif early_warning_level == "MODERATE":
                    st.warning(early_warning_level)

                else:
                    st.success(early_warning_level)

        with warning_col2:

            with st.container(border=True):

                st.markdown(
                    "**EARLY-WARNING SCORE**"
                )

                st.metric(
                    "Score",
                    f"{early_warning_score:.0f}/100"
                )

        with warning_col3:

            with st.container(border=True):

                st.markdown(
                    "**TELEMETRY STATUS**"
                )

                if deterioration_detected:
                    st.error(
                        "DETERIORATION DETECTED"
                    )
                else:
                    st.success(
                        "NO DETERIORATION"
                    )

        if deterioration_detected:

            st.warning(
                "VETRA detected a physiological deterioration "
                "pattern in the recent telemetry window. "
                "Review the signals and recommended action."
            )

        else:

            st.success(
                "No significant physiological deterioration "
                "detected in the recent telemetry window."
            )

        st.markdown(
            "##### Detected Early-Warning Signals"
        )

        if early_warning_signals:

            for signal in early_warning_signals:

                with st.container(border=True):
                    st.markdown(
                        f"⚠️ {signal}"
                    )

        else:

            st.info(
                "No early-warning physiological signals "
                "detected across the recent telemetry readings."
            )

        # ========================================================
        # IMPORTANT: STREAMLIT-NATIVE TREND SECTION
        # No nested HTML is used here.
        # ========================================================

        st.markdown(
            "##### Deterioration Trend"
        )

        with st.container(border=True):

            st.markdown(
                "**TELEMETRY TREND ANALYSIS**"
            )

            st.write(
                early_warning_trend
            )

        # ========================================================
        # IMPORTANT: STREAMLIT-NATIVE ACTION SECTION
        # No nested HTML is used here.
        # ========================================================

        st.markdown(
            "##### Early-Warning Recommended Action"
        )

        with st.container(border=True):

            st.markdown(
                "**VETRA DECISION-SUPPORT RECOMMENDATION**"
            )

            st.write(
                early_warning_action
            )

        metadata_col1, metadata_col2 = st.columns(2)

        with metadata_col1:

            st.caption(
                f"Early-Warning Engine: "
                f"{early_warning_engine}"
            )

        with metadata_col2:

            readings_analyzed = ai_report.get(
                "early_warning_readings_analyzed",
                0
            )

            st.caption(
                f"Recent Telemetry Readings Analyzed: "
                f"{readings_analyzed}"
            )

        st.caption(
            "Early-warning intelligence identifies "
            "physiological deterioration patterns for "
            "decision support and does not constitute "
            "a definitive veterinary diagnosis."
        )

        # ========================================================
        # INTELLIGENCE SOURCE
        # ========================================================

        st.markdown("---")

        st.caption(
            "Intelligence Source: "
            f"{ai_report.get('analysis_engine', 'VETRA-AI-Core')}"
        )

    # ============================================================
    # TAB 1.5 — VISUAL HEALTH (PHASE 9 INTEGRATION)
    # ============================================================

    with tab_visual:
        st.markdown("### 👁️ Visual Health & Multimodal Assessment")
        st.caption("Computer vision screening, physical signs, and multimodal health fusion.")

        # Safety disclaimer
        st.info("🛡️ **Decision Support Only:** Visual observations are AI-assisted indicators and are not a confirmed veterinary diagnosis. Veterinary examination is required for clinical confirmation.")

        vis_analyses = api_client.get_animal_visual_analyses(selected_animal_id, limit=5)
        trend = api_client.get_animal_visual_trend(selected_animal_id)

        v_top_col1, v_top_col2 = st.columns([3, 1])
        with v_top_col2:
            if st.button("📸 Analyze New Image", key="btn_prof_analyze_img", use_container_width=True, type="primary"):
                st.session_state["nav_choice"] = "👁️ Visual Health"
                st.rerun()

        if not vis_analyses:
            st.info("No visual health analyses recorded for this animal yet. Click 'Analyze New Image' to initiate screening.")
        else:
            latest_va = vis_analyses[0]
            v_score = latest_va.get("visual_risk_score", 0.0)
            v_cat = latest_va.get("risk_category", "LOW")

            vm_c1, vm_c2, vm_c3, vm_c4 = st.columns(4)
            with vm_c1:
                st.metric("Latest Visual Risk", f"{v_score:.0f}/100", delta=v_cat, delta_color="inverse")
            with vm_c2:
                st.metric("Detected Species", latest_va.get("animal_detected", "Cattle").title(), f"{latest_va.get('detection_confidence', 0.9)*100:.0f}% conf")
            with vm_c3:
                st.metric("Review Status", latest_va.get("review_status", "pending").title())
            with vm_c4:
                st.metric("Trajectory", trend.get("trajectory", "stable").replace("_", " ").title())

            st.markdown("##### Recent Visible Health Observations")
            observations = latest_va.get("observations", [])
            if not observations:
                st.success("No abnormal visible indicators detected in the latest photographic assessment.")
            else:
                for obs in observations:
                    st.markdown(
                        f"- **{obs.get('indicator', '').replace('_', ' ').title()}**: {obs.get('description')} "
                        f"*(Confidence: {obs.get('confidence', 0)*100:.0f}%, Severity: {obs.get('severity', 'medium').upper()})*"
                    )

            if latest_va.get("explanation"):
                st.info(f"💡 **AI Visual Interpretation:** {latest_va.get('explanation')}")

            # Multimodal Fusion preview
            st.markdown("##### Multimodal Health Fusion")
            mm_gen_col1, mm_gen_col2 = st.columns([2, 1])
            with mm_gen_col1:
                st.caption("Fuses visual observations with IoT vital telemetry and disease surveillance.")
            with mm_gen_col2:
                if st.button("🧬 Generate Multimodal Report", key="btn_prof_gen_mm", use_container_width=True):
                    mm_ok, mm_data = api_client.create_multimodal_assessment(animal_id=selected_animal_id, visual_analysis_id=latest_va.get("analysis_id"))
                    if mm_ok and isinstance(mm_data, dict):
                        st.success(f"Combined Multimodal Risk: {mm_data.get('combined_risk'):.0f}/100 ({mm_data.get('risk_category')})")
                    else:
                        st.error(f"Error: {mm_data}")

            st.caption(f"Visual Model: {latest_va.get('model_name')} ({latest_va.get('model_version')}) | Analyzed: {latest_va.get('created_at', '')[:16].replace('T', ' ')}")

    # ============================================================
    # TAB 2 — VITALS TELEMETRY
    # ============================================================

    with tab_vitals:

        st.markdown("### Vitals Telemetry")

        readings = api_client.get_health_readings(
            selected_animal_id
        )

        if not readings:

            st.info(
                "No physiological telemetry recorded "
                "for this animal yet."
            )

        else:

            latest = readings[0]

            temp = _safe_float(
                latest.get("temperature_c")
            )

            heart_rate = _safe_float(
                latest.get("heart_rate_bpm")
            )

            activity = _safe_float(
                latest.get("activity_level")
            )

            rumination = _safe_float(
                latest.get("rumination_level")
            )

            respiration = _safe_float(
                latest.get("respiratory_rate")
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                st.metric(
                    "Temperature",
                    f"{temp:.2f} °C"
                )

            with c2:
                st.metric(
                    "Heart Rate",
                    f"{heart_rate:.1f} BPM"
                )

            with c3:
                st.metric(
                    "Respiration",
                    f"{respiration:.1f} /min"
                )

            with c4:
                st.metric(
                    "Activity",
                    f"{activity:.1f}%"
                )

            with c5:
                st.metric(
                    "Rumination",
                    f"{rumination:.1f}%"
                )

            st.markdown("---")

            st.markdown(
                "#### Recent Telemetry Readings"
            )

            telemetry_rows = []

            for reading in readings[:50]:

                telemetry_rows.append(
                    {
                        "Recorded At": str(
                            reading.get(
                                "recorded_at",
                                ""
                            )
                        )[:19],
                        "Temperature °C": reading.get(
                            "temperature_c"
                        ),
                        "Heart Rate BPM": reading.get(
                            "heart_rate_bpm"
                        ),
                        "Activity %": reading.get(
                            "activity_level"
                        ),
                        "Rumination %": reading.get(
                            "rumination_level"
                        ),
                        "Respiration /min": reading.get(
                            "respiratory_rate"
                        ),
                        "Source": reading.get(
                            "source",
                            "simulator"
                        ),
                    }
                )

            if telemetry_rows:
                st.dataframe(
                    telemetry_rows,
                    use_container_width=True,
                    hide_index=True,
                )

    # ============================================================
    # TAB 3 — VETERINARY CASES
    # ============================================================

    with tab_cases:
        st.markdown("### Veterinary Cases & Clinical Management")

        cases = api_client.get_cases_for_animal(selected_animal_id)

        open_cases = [c for c in cases if c.get("status") not in ["resolved", "closed"]]
        resolved_cases = [c for c in cases if c.get("status") in ["resolved", "closed"]]

        # Current Treatment and Upcoming Follow-up
        current_tx = next((c for c in open_cases if c.get("treatment_plan") or c.get("status") == "treatment"), None)
        upcoming_fup = next((c for c in open_cases if c.get("follow_up_date")), None)

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Open Cases", len(open_cases))
        with col_m2:
            st.metric("Total Case History", len(cases))
        with col_m3:
            st.metric("Active Treatment", "Yes" if current_tx else "None")
        with col_m4:
            st.metric("Upcoming Follow-up", _format_date(upcoming_fup.get("follow_up_date")) if upcoming_fup else "None")

        st.markdown("---")

        with st.popover("➕ Open New Veterinary Case for this Animal", use_container_width=True):
            st.markdown("##### New Clinical Case")
            with st.form(f"case_from_profile_{selected_animal_id}", clear_on_submit=True):
                n_title = st.text_input("Case Title", placeholder="e.g. Lameness / Respiratory Distress")
                n_type = st.selectbox(
                    "Case Type",
                    options=["health_alert", "preventive_follow_up", "routine_checkup", "suspected_disease", "treatment", "vaccination", "deworming", "other"],
                    format_func=lambda s: s.replace("_", " ").title()
                )
                n_prio = st.selectbox("Priority", options=["critical", "high", "medium", "low"], format_func=lambda s: s.upper())
                n_desc = st.text_area("Symptoms & Clinical History")

                if st.form_submit_button("Submit Veterinary Case", type="primary"):
                    if n_title.strip():
                        ok, res = api_client.create_veterinary_case({
                            "animal_id": selected_animal_id,
                            "title": n_title.strip(),
                            "description": n_desc.strip() if n_desc else None,
                            "case_type": n_type,
                            "priority": n_prio,
                            "source": "manual"
                        })
                        if ok:
                            st.success(f"Case {res.get('case_number')} opened successfully!")
                            st.rerun()
                        else:
                            st.error(str(res))
                    else:
                        st.error("Case title is required.")

        st.markdown("#### Active & Open Cases")
        if open_cases:
            for c in open_cases:
                c_num = c.get("case_number", "CASE")
                c_prio = c.get("priority", "medium").upper()
                c_stat = c.get("status", "open").upper()
                with st.expander(f"🩺 [{c_prio}] {c_num}: {c.get('title')} ({c_stat})", expanded=True):
                    st.markdown(f"**Case Type:** {c.get('case_type', '').replace('_', ' ').title()} &nbsp;•&nbsp; **Source:** {c.get('source', '').replace('_', ' ').title()}")
                    st.markdown(f"**Assigned Veterinarian:** {c.get('assigned_veterinarian_name') or 'Unassigned'}")
                    if c.get("description"):
                        st.caption(f"Description: {c.get('description')}")
                    if c.get("diagnosis"):
                        st.success(f"Diagnosis: {c.get('diagnosis')}")
                    if c.get("treatment_plan"):
                        st.info(f"Treatment Plan: {c.get('treatment_plan')}")
                    if c.get("follow_up_date"):
                        st.markdown(f"**Scheduled Follow-up:** `{_format_date(c.get('follow_up_date'))}`")

                    if st.button("🔍 Open Full Case in Clinical Console", key=f"open_case_from_profile_{c['id']}"):
                        st.session_state["selected_case_id"] = c["id"]
                        st.success(f"Case {c_num} selected. Navigate to '🩺 Clinical Cases' in the sidebar to review.")
        else:
            st.success("🟢 No open clinical cases for this animal.")

        if resolved_cases:
            st.markdown("#### Case History (Resolved & Closed)")
            for rc in resolved_cases:
                with st.expander(f"✅ {rc.get('case_number')}: {rc.get('title')} ({rc.get('status').upper()})"):
                    st.markdown(f"**Diagnosis:** {rc.get('diagnosis') or '-'}")
                    st.markdown(f"**Resolution Summary:** {rc.get('recommendations') or '-'}")
                    st.caption(f"Closed: {_format_date(rc.get('closed_at') or rc.get('updated_at'))}")

    # ============================================================
    # TAB 4 — VACCINATIONS
    # ============================================================

    with tab_vacc:

        st.markdown("### Vaccination Records")

        vaccinations = api_client.get_vaccinations(
            selected_animal_id
        )

        if vaccinations:

            for vaccination in vaccinations:
                _display_record(vaccination)

        else:

            st.info(
                "No vaccination records available."
            )

        st.markdown("---")

        st.markdown(
            "#### Add Vaccination Record"
        )

        with st.form(
            "vaccination_form",
            clear_on_submit=True
        ):

            vaccine_name = st.text_input(
                "Vaccine Name"
            )

            vaccination_date = st.date_input(
                "Vaccination Date",
                value=date.today()
            )

            next_due_date = st.date_input(
                "Next Due Date",
                value=date.today()
            )

            veterinarian = st.text_input(
                "Veterinarian / Provider"
            )

            notes = st.text_area(
                "Notes"
            )

            submit_vaccination = st.form_submit_button(
                "Save Vaccination",
                use_container_width=True
            )

        if submit_vaccination:

            if not vaccine_name.strip():

                st.error(
                    "Please enter the vaccine name."
                )

            else:

                payload = {
                    "animal_id": selected_animal_id,
                    "vaccine_name": vaccine_name.strip(),
                    "vaccination_date": str(
                        vaccination_date
                    ),
                    "next_due_date": str(
                        next_due_date
                    ),
                    "veterinarian": veterinarian.strip(),
                    "notes": notes.strip(),
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

                    st.rerun()

                else:

                    st.error(
                        str(result)
                    )

    # ============================================================
    # TAB 4 — DEWORMING
    # ============================================================

    with tab_deworm:

        st.markdown("### Deworming Records")

        deworming_records = api_client.get_deworming(
            selected_animal_id
        )

        if deworming_records:

            for record in deworming_records:
                _display_record(record)

        else:

            st.info(
                "No deworming records available."
            )

        st.markdown("---")

        st.markdown(
            "#### Add Deworming Record"
        )

        with st.form(
            "deworming_form",
            clear_on_submit=True
        ):

            medicine_name = st.text_input(
                "Medicine / Dewormer"
            )

            deworming_date = st.date_input(
                "Deworming Date",
                value=date.today()
            )

            next_due_date = st.date_input(
                "Next Due Date",
                value=date.today()
            )

            dosage = st.text_input(
                "Dosage"
            )

            notes = st.text_area(
                "Notes"
            )

            submit_deworming = st.form_submit_button(
                "Save Deworming Record",
                use_container_width=True
            )

        if submit_deworming:

            if not medicine_name.strip():

                st.error(
                    "Please enter the medicine/dewormer name."
                )

            else:

                payload = {
                    "animal_id": selected_animal_id,
                    "medicine_name": medicine_name.strip(),
                    "deworming_date": str(
                        deworming_date
                    ),
                    "next_due_date": str(
                        next_due_date
                    ),
                    "dosage": dosage.strip(),
                    "notes": notes.strip(),
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

                    st.rerun()

                else:

                    st.error(
                        str(result)
                    )

    # ============================================================
    # TAB 5 — TREATMENTS
    # ============================================================

    with tab_treat:

        st.markdown("### Treatment Records")

        treatments = api_client.get_treatments(
            selected_animal_id
        )

        if treatments:

            for treatment in treatments:
                _display_record(treatment)

        else:

            st.info(
                "No treatment records available."
            )

        st.markdown("---")

        st.markdown(
            "#### Add Treatment Record"
        )

        with st.form(
            "treatment_form",
            clear_on_submit=True
        ):

            treatment_name = st.text_input(
                "Treatment / Medicine"
            )

            treatment_date = st.date_input(
                "Treatment Date",
                value=date.today()
            )

            diagnosis = st.text_input(
                "Clinical Concern / Diagnosis"
            )

            dosage = st.text_input(
                "Dosage / Instructions"
            )

            veterinarian = st.text_input(
                "Veterinarian"
            )

            notes = st.text_area(
                "Clinical Notes"
            )

            submit_treatment = st.form_submit_button(
                "Save Treatment",
                use_container_width=True
            )

        if submit_treatment:

            if not treatment_name.strip():

                st.error(
                    "Please enter the treatment name."
                )

            else:

                payload = {
                    "animal_id": selected_animal_id,
                    "treatment_name": treatment_name.strip(),
                    "treatment_date": str(
                        treatment_date
                    ),
                    "diagnosis": diagnosis.strip(),
                    "dosage": dosage.strip(),
                    "veterinarian": veterinarian.strip(),
                    "notes": notes.strip(),
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

                    st.rerun()

                else:

                    st.error(
                        str(result)
                    )

    # ============================================================
    # TAB 6 — VETERINARY VISITS
    # ============================================================

    with tab_visits:

        st.markdown("### Veterinary Visit Records")

        vet_visits = api_client.get_vet_visits(
            selected_animal_id
        )

        if vet_visits:

            for visit in vet_visits:
                _display_record(visit)

        else:

            st.info(
                "No veterinary visit records available."
            )

        st.markdown("---")

        st.markdown(
            "#### Add Veterinary Visit"
        )

        with st.form(
            "vet_visit_form",
            clear_on_submit=True
        ):

            visit_date = st.date_input(
                "Visit Date",
                value=date.today()
            )

            veterinarian = st.text_input(
                "Veterinarian"
            )

            reason = st.text_input(
                "Reason for Visit"
            )

            clinical_findings = st.text_area(
                "Clinical Findings"
            )

            treatment_plan = st.text_area(
                "Treatment / Follow-up Plan"
            )

            next_visit_date = st.date_input(
                "Next Follow-up Date",
                value=date.today()
            )

            submit_visit = st.form_submit_button(
                "Save Veterinary Visit",
                use_container_width=True
            )

        if submit_visit:

            payload = {
                "animal_id": selected_animal_id,
                "visit_date": str(
                    visit_date
                ),
                "veterinarian": veterinarian.strip(),
                "reason": reason.strip(),
                "clinical_findings": clinical_findings.strip(),
                "treatment_plan": treatment_plan.strip(),
                "next_visit_date": str(
                    next_visit_date
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

                st.rerun()

            else:

                st.error(
                    str(result)
                )
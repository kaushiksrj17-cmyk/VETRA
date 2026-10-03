from datetime import datetime, timezone
import io
from typing import Any, Optional
import pandas as pd
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api_client
from session import get_user_info


def render_computer_vision_page():
    """
    VETRA Phase 9 — Computer Vision & Multimodal Animal Health Intelligence.
    Provides AI-assisted visual health observation, video frame analysis,
    temporal health comparison, and multimodal health assessment.
    """
    user_info = get_user_info()
    user_role = str(user_info.get("role", "farmer")).lower()

    # -------------------------------------------------------------
    # 1. HEADER & CLINICAL DISCLAIMER
    # -------------------------------------------------------------
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.25rem; border: 1px solid #334155; color: white;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px;">
                        👁️ Visual Health Intelligence
                    </h1>
                    <p style="margin: 0.35rem 0 0 0; font-size: 0.95rem; color: #94a3b8;">
                        AI-assisted visual assessment of livestock health indicators and multimodal intelligence.
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="display: inline-block; padding: 0.35rem 0.85rem; border-radius: 9999px; background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8; font-size: 0.85rem; font-weight: 600;">
                        DECISION SUPPORT PLATFORM
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Prominent Clinical Safety Notice (Step 30)
    st.info(
        "🛡️ **Decision Support Only:** Visual observations are AI-assisted indicators and are not a confirmed veterinary "
        "diagnosis. Veterinary examination is required for clinical confirmation."
    )

    # -------------------------------------------------------------
    # 2. KPI STRIP (Step 20)
    # -------------------------------------------------------------
    summary = api_client.get_visual_health_summary()
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.metric("Images Analyzed", summary.get("total_analyses", 0))
    with k2:
        st.metric("Animals Assessed", summary.get("animals_assessed", 0))
    with k3:
        st.metric("Visual Signals", summary.get("total_observations", 0))
    with k4:
        st.metric("Moderate/High Risk", summary.get("high_risk_analyses", 0))
    with k5:
        st.metric("Pending Vet Reviews", summary.get("pending_reviews", 0))
    with k6:
        st.metric("Multimodal Reports", summary.get("multimodal_assessments_count", 0))

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 3. COMMON ANIMAL / FARM SELECTION DATA
    # -------------------------------------------------------------
    farms = api_client.get_farms()
    farm_dict = {f["name"]: str(f["id"]) for f in farms} if farms else {}

    animals = api_client.get_animals()
    animal_dict = {f"{a.get('tag_id')} — {a.get('name', 'Unnamed')} ({a.get('species', 'Cattle')})": str(a["id"]) for a in animals} if animals else {}

    # -------------------------------------------------------------
    # 4. TABS
    # -------------------------------------------------------------
    t1, t2, t3, t4, t5 = st.tabs([
        "📸 Image Analysis",
        "🎥 Video Analysis",
        "📜 Analysis History",
        "🔄 Animal Comparison",
        "🧬 Multimodal Intelligence"
    ])

    # =============================================================
    # TAB 1: IMAGE ANALYSIS
    # =============================================================
    with t1:
        st.subheader("Livestock Image Health Screening")
        st.caption("Upload a photographic observation of an animal to detect visible posture, condition, or surface health signals.")

        c_left, c_right = st.columns([1, 1], gap="large")

        with c_left:
            st.markdown("##### 1. Select Subject & Media")
            if not animal_dict:
                st.warning("No animal records available. Please register livestock first.")
                selected_animal_id = None
            else:
                chosen_animal_label = st.selectbox("Select Target Animal", options=list(animal_dict.keys()), key="cv_img_animal")
                selected_animal_id = animal_dict.get(chosen_animal_label)

            uploaded_img = st.file_uploader(
                "Upload Image (JPG, PNG, WEBP — Max 10MB)",
                type=["jpg", "jpeg", "png", "webp"],
                key="cv_img_file"
            )

            if uploaded_img:
                img_bytes = uploaded_img.getvalue()
                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    st.image(pil_img, caption=f"Preview: {uploaded_img.name} ({len(img_bytes)/1024:.1f} KB)", use_container_width=True)
                except Exception:
                    st.error("Invalid image preview.")

            run_analysis_btn = st.button("🔍 Run Visual Health Analysis", type="primary", use_container_width=True, disabled=(not uploaded_img or not selected_animal_id))

        with c_right:
            st.markdown("##### 2. Visual Health Assessment Report")

            if run_analysis_btn and uploaded_img and selected_animal_id:
                with st.spinner("Analyzing image features, body posture, and visible health markers..."):
                    success, res = api_client.upload_and_analyze_image(
                        animal_id=selected_animal_id,
                        file_bytes=uploaded_img.getvalue(),
                        filename=uploaded_img.name,
                        content_type=uploaded_img.type or "image/jpeg"
                    )

                if success and isinstance(res, dict):
                    st.session_state["last_cv_result"] = res
                    st.success(f"Analysis Complete: **{res.get('analysis_id')}**")
                else:
                    st.error(f"Analysis failed: {res}")

            current_res = st.session_state.get("last_cv_result")
            if current_res:
                v_score = current_res.get("visual_risk_score", 0.0)
                v_cat = current_res.get("risk_category", "LOW")
                vet_needed = current_res.get("requires_veterinary_review", False)

                # Score Badge
                cat_color = "#10b981" if v_cat == "LOW" else ("#f59e0b" if v_cat == "MODERATE" else ("#ef4444" if v_cat == "HIGH" else "#991b1b"))
                st.markdown(
                    f"""
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;">Visual Health Risk Score</span>
                                <h2 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: {cat_color};">
                                    {v_score:.0f} <span style="font-size: 1rem; color: #94a3b8;">/ 100</span>
                                </h2>
                            </div>
                            <div style="text-align: right;">
                                <span style="display: inline-block; padding: 0.35rem 0.85rem; border-radius: 6px; background: {cat_color}22; border: 1px solid {cat_color}66; color: {cat_color}; font-weight: 700; font-size: 0.95rem;">
                                    {v_cat} RISK
                                </span>
                                <p style="margin: 0.3rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">
                                    Species: <b>{current_res.get('animal_detected', 'Cattle').title()}</b> ({current_res.get('detection_confidence', 0.9)*100:.0f}%)
                                </p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Observed Indicators
                st.markdown("###### Detected Visual Indicators")
                obs_list = current_res.get("observations", [])
                if not obs_list:
                    st.success("No abnormal visual health indicators detected in this image.")
                else:
                    for obs in obs_list:
                        ind_name = obs.get("indicator", "").replace("_", " ").title()
                        conf = obs.get("confidence", 0.0) * 100
                        sev = obs.get("severity", "medium").upper()
                        desc = obs.get("description", "")
                        st.markdown(
                            f"""
                            <div style="border-left: 3px solid #f59e0b; background: rgba(245, 158, 11, 0.08); padding: 0.65rem 0.85rem; margin-bottom: 0.5rem; border-radius: 0 6px 6px 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <b style="color: #f8fafc; font-size: 0.95rem;">{ind_name}</b>
                                    <span style="font-size: 0.8rem; color: #cbd5e1; background: #334155; padding: 0.2rem 0.5rem; border-radius: 4px;">
                                        Confidence: <b>{conf:.0f}%</b> | Severity: <b>{sev}</b>
                                    </span>
                                </div>
                                <p style="margin: 0.3rem 0 0 0; font-size: 0.85rem; color: #94a3b8;">{desc}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # AI Interpretation
                if current_res.get("explanation"):
                    st.info(f"💡 **AI Health Interpretation:** {current_res.get('explanation')}")

                # Veterinary Review Recommendation
                if vet_needed:
                    st.warning("⚠️ **Veterinary Examination Recommended:** Visual signals warrant on-site clinical review.")

                # Action Escalations
                st.markdown("###### Clinical & Surveillance Actions")
                act_col1, act_col2 = st.columns(2)

                with act_col1:
                    with st.expander("🩺 Refer to Veterinarian"):
                        case_notes = st.text_area("Clinical Referral Notes", value=f"Visual health screening flagged score {v_score:.0f}/100. Observations: {', '.join([o['indicator'] for o in obs_list])}", key="img_case_notes")
                        priority = st.selectbox("Triage Priority", ["medium", "high", "critical"], index=1 if v_score >= 45 else 0, key="img_case_pri")
                        if st.button("Confirm Clinical Case Creation", key="btn_create_img_case"):
                            c_success, c_res = api_client.escalate_visual_to_veterinary_case(
                                analysis_id=current_res["analysis_id"],
                                notes=case_notes,
                                priority=priority
                            )
                            if c_success and isinstance(c_res, dict):
                                st.success(f"Case Created: **{c_res.get('case_number')}**")
                            else:
                                st.error(f"Error: {c_res}")

                with act_col2:
                    with st.expander("🧬 Generate Multimodal Assessment"):
                        st.caption("Fuses visual observations with real-time IoT vital telemetry and disease surveillance.")
                        if st.button("Compute Multimodal Score", key="btn_run_mm_img"):
                            mm_ok, mm_res = api_client.create_multimodal_assessment(
                                animal_id=current_res["animal_id"],
                                visual_analysis_id=current_res["analysis_id"]
                            )
                            if mm_ok and isinstance(mm_res, dict):
                                st.session_state["last_mm_result"] = mm_res
                                st.success(f"Multimodal Assessment Ready! (Risk: {mm_res.get('combined_risk'):.0f}/100)")
                            else:
                                st.error(f"Error: {mm_res}")
            else:
                st.info("Upload an image on the left and click 'Run Visual Health Analysis' to generate a report.")

    # =============================================================
    # TAB 2: VIDEO ANALYSIS
    # =============================================================
    with t2:
        st.subheader("Livestock Video Frame Analysis")
        st.caption("Controlled frame sampling over short video clips to evaluate gait irregularity, posture persistence, and temporal motion.")

        v_left, v_right = st.columns([1, 1], gap="large")

        with v_left:
            st.markdown("##### 1. Select Subject & Video File")
            if not animal_dict:
                st.warning("No animal records available.")
                vid_animal_id = None
            else:
                chosen_vid_animal = st.selectbox("Select Target Animal", options=list(animal_dict.keys()), key="cv_vid_animal")
                vid_animal_id = animal_dict.get(chosen_vid_animal)

            uploaded_vid = st.file_uploader(
                "Upload Video File (MP4, AVI, MOV — Max 25MB)",
                type=["mp4", "avi", "mov"],
                key="cv_vid_file"
            )

            st.caption("⏱️ Processing constraint: Videos are sampled at controlled intervals (max 10 frames) to ensure responsive execution.")
            run_vid_btn = st.button("📹 Run Video Frame Analysis", type="primary", use_container_width=True, disabled=(not uploaded_vid or not vid_animal_id))

        with v_right:
            st.markdown("##### 2. Video Analysis Results")

            if run_vid_btn and uploaded_vid and vid_animal_id:
                with st.spinner("Sampling video frames, analyzing temporal consistency and gait markers..."):
                    success, v_res = api_client.upload_and_analyze_video(
                        animal_id=vid_animal_id,
                        file_bytes=uploaded_vid.getvalue(),
                        filename=uploaded_vid.name,
                        content_type=uploaded_vid.type or "video/mp4"
                    )

                if success and isinstance(v_res, dict):
                    st.session_state["last_vid_result"] = v_res
                    st.success(f"Video Analysis Complete: **{v_res.get('analysis_id')}**")
                else:
                    st.error(f"Video analysis failed: {v_res}")

            last_v = st.session_state.get("last_vid_result")
            if last_v:
                # Video KPI strip
                vk1, vk2, vk3 = st.columns(3)
                with vk1:
                    st.metric("Duration", f"{last_v.get('duration_sec', 0.0):.1f}s")
                with vk2:
                    st.metric("Frames Sampled", last_v.get("total_frames_sampled", 0))
                with vk3:
                    st.metric("Consistency", str(last_v.get("temporal_consistency", "nominal")).title())

                st.metric("Video Visual Risk Score", f"{last_v.get('visual_risk_score', 0):.0f}/100", delta=last_v.get("risk_category"))

                st.markdown("###### Observations Detected Across Video Sequence")
                v_obs = last_v.get("observations", [])
                if not v_obs:
                    st.success("No abnormal motion or posture indicators observed across video sequence.")
                else:
                    for vo in v_obs:
                        st.markdown(f"- **{vo.get('indicator', '').replace('_', ' ').title()}**: {vo.get('description')} (Confidence: {vo.get('confidence', 0)*100:.0f}%)")

                if last_v.get("explanation"):
                    st.info(f"💡 **Temporal Assessment:** {last_v.get('explanation')}")
            else:
                st.info("Upload a video on the left to initiate controlled frame sampling analysis.")

    # =============================================================
    # TAB 3: ANALYSIS HISTORY
    # =============================================================
    with t3:
        st.subheader("Historical Visual Analyses Log")
        st.caption("Audit trail of all photographic and video screenings.")

        h_filter_col1, h_filter_col2 = st.columns(2)
        with h_filter_col1:
            h_farm_choice = st.selectbox("Filter Farm", ["All Farms"] + list(farm_dict.keys()), key="hist_farm_filter")
        with h_filter_col2:
            h_limit = st.slider("Result Limit", 10, 100, 30, key="hist_limit")

        sel_fid = farm_dict.get(h_farm_choice) if h_farm_choice != "All Farms" else None
        history_records = api_client.get_visual_analyses(farm_id=sel_fid, limit=h_limit)

        if not history_records:
            st.info("No visual health analyses recorded yet.")
        else:
            table_data = []
            for r in history_records:
                top_obs = r.get("observations", [{}])[0].get("indicator", "None") if r.get("observations") else "Nominal"
                table_data.append({
                    "Analysis ID": r.get("analysis_id"),
                    "Date": r.get("created_at")[:16].replace("T", " ") if r.get("created_at") else "",
                    "Animal": r.get("animal_tag") or r.get("animal_id"),
                    "Holding": r.get("farm_name", "Holding"),
                    "Type": r.get("media_type", "image").title(),
                    "Visual Risk": f"{r.get('visual_risk_score', 0):.0f} ({r.get('risk_category')})",
                    "Top Observation": top_obs.replace("_", " ").title(),
                    "Vet Review": "Required" if r.get("requires_veterinary_review") else "Not Required",
                    "Status": r.get("review_status", "pending")
                })

            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

            # Detail Inspector
            st.markdown("##### Detailed Report Inspector")
            analysis_opts = [r["analysis_id"] for r in history_records]
            chosen_aid = st.selectbox("Select Analysis Record to Inspect", analysis_opts, key="hist_inspect_id")
            chosen_rec = next((r for r in history_records if r["analysis_id"] == chosen_aid), None)

            if chosen_rec:
                with st.expander(f"Analysis Report — {chosen_rec.get('analysis_id')}", expanded=True):
                    r_col1, r_col2 = st.columns(2)
                    with r_col1:
                        st.markdown(f"**Animal:** {chosen_rec.get('animal_tag')} ({chosen_rec.get('animal_name', 'Unnamed')})")
                        st.markdown(f"**Farm:** {chosen_rec.get('farm_name')}")
                        st.markdown(f"**Model:** {chosen_rec.get('model_name')} ({chosen_rec.get('model_version')})")
                        st.markdown(f"**Processing Time:** {chosen_rec.get('processing_time_ms', 0):.1f} ms")
                        st.markdown(f"**Media SHA-256:** `{chosen_rec.get('media_hash', '')[:20]}...`")
                    with r_col2:
                        st.markdown(f"**Visual Risk Score:** **{chosen_rec.get('visual_risk_score', 0):.0f} / 100** ({chosen_rec.get('risk_category')})")
                        st.markdown(f"**Review Status:** `{chosen_rec.get('review_status')}`")
                        st.markdown(f"**Veterinary Case:** {chosen_rec.get('veterinary_case_id') or 'None'}")
                        st.markdown(f"**Notice:** *{chosen_rec.get('clinical_safety_notice')}*")

    # =============================================================
    # TAB 4: ANIMAL COMPARISON (TEMPORAL INTELLIGENCE)
    # =============================================================
    with t4:
        st.subheader("Temporal Visual Trajectory Comparison")
        st.caption("Compares consecutive visual assessments for an individual animal to detect improving, stable, or worsening clinical signs.")

        if not animal_dict:
            st.warning("No animal records available.")
        else:
            comp_animal_label = st.selectbox("Select Animal to Compare Trajectory", options=list(animal_dict.keys()), key="comp_animal_choice")
            comp_animal_id = animal_dict.get(comp_animal_label)

            if comp_animal_id:
                trend_data = api_client.get_animal_visual_trend(comp_animal_id)

                if not trend_data or trend_data.get("trajectory") == "no_data":
                    st.info("No visual health analyses recorded for this animal yet.")
                elif trend_data.get("trajectory") == "baseline":
                    st.info(trend_data.get("explanation", "Single baseline assessment recorded."))
                else:
                    traj = trend_data.get("trajectory", "stable")
                    traj_color = "#10b981" if traj == "improved" else ("#3b82f6" if traj == "stable" else ("#f59e0b" if traj == "new_signal" else "#ef4444"))

                    st.markdown(
                        f"""
                        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 0.85rem; color: #94a3b8;">TEMPORAL HEALTH TRAJECTORY</span>
                                    <h3 style="margin: 0.2rem 0; font-size: 1.6rem; font-weight: 800; color: {traj_color};">
                                        {traj.replace('_', ' ').upper()}
                                    </h3>
                                </div>
                                <div style="text-align: right;">
                                    <span style="font-size: 0.85rem; color: #94a3b8;">RISK SCORE DELTA</span>
                                    <h3 style="margin: 0.2rem 0; font-size: 1.6rem; font-weight: 800; color: {'#ef4444' if trend_data.get('score_delta', 0) > 0 else '#10b981'};">
                                        {'+' if trend_data.get('score_delta', 0) > 0 else ''}{trend_data.get('score_delta', 0):.1f}
                                    </h3>
                                </div>
                            </div>
                            <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #cbd5e1;">{trend_data.get('explanation')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Two-column Earlier vs Latest comparison
                    col_early, col_late = st.columns(2)
                    with col_early:
                        st.markdown(f"###### Baseline / Earlier Assessment (`{trend_data.get('earlier_analysis_id')}`)")
                        st.caption(f"Recorded: {trend_data.get('earlier_date', '')[:16].replace('T', ' ')}")
                    with col_late:
                        st.markdown(f"###### Latest Assessment (`{trend_data.get('latest_analysis_id')}`)")
                        st.caption(f"Recorded: {trend_data.get('latest_date', '')[:16].replace('T', ' ')}")

                    # Breakdown of indicators
                    st.markdown("###### Indicator Shifts")
                    ind_col1, ind_col2, ind_col3 = st.columns(3)
                    with ind_col1:
                        st.markdown("**Persistent Signs:**")
                        pers = trend_data.get("persistent_indicators", [])
                        if pers:
                            for p in pers:
                                st.markdown(f"- ⚠️ {p.replace('_', ' ').title()}")
                        else:
                            st.caption("None")

                    with ind_col2:
                        st.markdown("**New Visible Signs:**")
                        news = trend_data.get("new_indicators", [])
                        if news:
                            for n in news:
                                st.markdown(f"- 🔴 {n.replace('_', ' ').title()}")
                        else:
                            st.caption("None")

                    with ind_col3:
                        st.markdown("**Resolved Visible Signs:**")
                        resd = trend_data.get("resolved_indicators", [])
                        if resd:
                            for r in resd:
                                st.markdown(f"- 🟢 {r.replace('_', ' ').title()}")
                        else:
                            st.caption("None")

    # =============================================================
    # TAB 5: MULTIMODAL INTELLIGENCE
    # =============================================================
    with t5:
        st.subheader("Unified Multimodal Animal Health Assessment")
        st.caption(
            "Fuses photographic observations (30%), IoT vital telemetry (30%), disease intelligence (15%), "
            "surveillance risk (15%), and preventive records (10%) into a transparent decision-support profile."
        )

        if not animal_dict:
            st.warning("No animal records available.")
        else:
            mm_animal_label = st.selectbox("Select Target Animal for Multimodal Fusion", options=list(animal_dict.keys()), key="mm_animal_choice")
            mm_animal_id = animal_dict.get(mm_animal_label)

            mm_col1, mm_col2 = st.columns([1, 2], gap="large")

            with mm_col1:
                st.markdown("##### 1. Assessment Trigger")
                st.caption("Evaluate multi-source health indicators across physical appearance, real-time vitals, and herd context.")
                run_mm_btn = st.button("🧬 Generate Multimodal Assessment", type="primary", use_container_width=True, key="btn_run_mm_tab")

                if run_mm_btn and mm_animal_id:
                    with st.spinner("Synthesizing visual, IoT telemetry, disease screening, and surveillance risk factors..."):
                        success, mm_res = api_client.create_multimodal_assessment(animal_id=mm_animal_id)
                        if success and isinstance(mm_res, dict):
                            st.session_state["last_mm_result"] = mm_res
                            st.success(f"Assessment Generated: **{mm_res.get('assessment_id')}**")
                        else:
                            st.error(f"Assessment generation failed: {mm_res}")

            with mm_col2:
                st.markdown("##### 2. Integrated Decision-Support Intelligence")
                active_mm = st.session_state.get("last_mm_result")

                if active_mm:
                    comb_score = active_mm.get("combined_risk", 0.0)
                    comb_cat = active_mm.get("risk_category", "LOW")
                    consistency = active_mm.get("visual_telemetry_consistency", "nominal")
                    mm_color = "#10b981" if comb_cat == "LOW" else ("#f59e0b" if comb_cat == "MODERATE" else ("#ef4444" if comb_cat == "HIGH" else "#991b1b"))

                    st.markdown(
                        f"""
                        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 0.85rem; color: #94a3b8;">COMBINED MULTIMODAL HEALTH RISK</span>
                                    <h2 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: {mm_color};">
                                        {comb_score:.0f} <span style="font-size: 1rem; color: #94a3b8;">/ 100</span>
                                    </h2>
                                </div>
                                <div style="text-align: right;">
                                    <span style="display: inline-block; padding: 0.35rem 0.85rem; border-radius: 6px; background: {mm_color}22; border: 1px solid {mm_color}66; color: {mm_color}; font-weight: 700;">
                                        {comb_cat} RISK
                                    </span>
                                    <p style="margin: 0.3rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">
                                        Directional Signal: <b>{consistency.replace('_', ' ').title()}</b>
                                    </p>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Radar / Bar breakdown of contributing scores
                    categories = ["Visual (30%)", "IoT Vitals (30%)", "Disease Screening (15%)", "Surveillance (15%)", "Preventive (10%)"]
                    values = [
                        active_mm.get("visual_score", 0.0),
                        active_mm.get("telemetry_score", 0.0),
                        active_mm.get("disease_risk", 0.0),
                        active_mm.get("surveillance_risk", 0.0),
                        active_mm.get("preventive_risk", 0.0)
                    ]

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=categories,
                        y=values,
                        marker_color=["#38bdf8", "#818cf8", "#f43f5e", "#fb923c", "#34d399"],
                        text=[f"{v:.0f}" for v in values],
                        textposition="auto"
                    ))
                    fig.update_layout(
                        title="Multimodal Component Risk Breakdown (0-100 Scale)",
                        yaxis=dict(range=[0, 100]),
                        height=260,
                        margin=dict(l=20, r=20, t=35, b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#cbd5e1")
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Contributing factors
                    factors = active_mm.get("contributing_factors", [])
                    if factors:
                        st.markdown("###### Key Contributing Health Factors")
                        for f in factors:
                            st.markdown(f"- 📌 {f}")

                    # Explanation and action
                    st.info(f"💡 **AI Synthesis:** {active_mm.get('explanation')}")
                    st.markdown(f"**Recommended Action:** {active_mm.get('recommended_action')}")

                    if active_mm.get("veterinary_review_required"):
                        st.warning("⚠️ **Clinical Attention Required:** Multimodal risk profile indicates on-site veterinary review.")
                else:
                    st.info("Select an animal and click 'Generate Multimodal Assessment' to fuse visual and physiological telemetry.")

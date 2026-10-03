from datetime import datetime, timezone
from typing import Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api_client
from session import get_user_info


def render_surveillance_page():
    """
    VETRA Phase 8 — Disease Surveillance & Geospatial Intelligence.
    Monitors emerging disease patterns, farm-level risk, potential statistical clusters,
    and regional surveillance signals.
    """
    user_info = get_user_info()
    user_role = str(user_info.get("role", "farmer")).lower()

    # -------------------------------------------------------------
    # 1. HEADER
    # -------------------------------------------------------------
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid #334155; color: white;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px;">
                        🦠 Disease Surveillance & Geospatial Intelligence
                    </h1>
                    <p style="margin: 0.35rem 0 0 0; font-size: 0.95rem; color: #94a3b8;">
                        Monitor emerging disease patterns, farm-level risk and regional surveillance signals.
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="display: inline-block; padding: 0.35rem 0.85rem; border-radius: 9999px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #93c5fd; font-size: 0.85rem; font-weight: 600;">
                        DECISION SUPPORT PLATFORM
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------
    # 2. CONTROLS BAR & TIME WINDOW
    # -------------------------------------------------------------
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])

    with ctrl_col1:
        window_options = {
            "24 Hours": 1,
            "3 Days": 3,
            "7 Days (Standard)": 7,
            "14 Days": 14,
            "30 Days": 30,
            "90 Days (Quarterly)": 90
        }
        selected_window_label = st.selectbox(
            "Surveillance Time Window",
            options=list(window_options.keys()),
            index=2,
            key="surv_window_select"
        )
        window_days = window_options[selected_window_label]

    with ctrl_col2:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    with ctrl_col3:
        st.write("")
        st.write("")
        if st.button("⚡ Run AI Synthesis", use_container_width=True, type="primary"):
            with st.spinner("Executing AI disease surveillance synthesis..."):
                analysis_res = api_client.trigger_surveillance_analysis()
                if analysis_res:
                    st.session_state["surv_last_analysis"] = analysis_res
                    st.success("AI Surveillance synthesis updated!")
                else:
                    st.warning("Analysis temporarily unavailable.")

    # -------------------------------------------------------------
    # 3. FETCH DATA WITH ERROR HANDLING
    # -------------------------------------------------------------
    with st.spinner("Querying surveillance intelligence..."):
        try:
            overview = api_client.get_surveillance_overview(window_days=window_days)
            watchlist = api_client.get_surveillance_watchlist(window_days=window_days)
            clusters = api_client.get_surveillance_clusters(window_days=window_days)
            hotspots = api_client.get_surveillance_hotspots(window_days=window_days)
            risk_map_items = api_client.get_surveillance_risk_map(window_days=window_days)
            regions = api_client.get_surveillance_regions(window_days=window_days)
            events = api_client.get_surveillance_events(limit=100)
            observations = api_client.get_surveillance_observations(limit=50)
            farm_profiles = api_client.get_surveillance_farms(window_days=window_days)
        except Exception:
            st.error("Surveillance data temporarily unavailable.")
            return

    if not overview:
        st.warning("Surveillance data temporarily unavailable.")
        return

    # -------------------------------------------------------------
    # 4. CLINICAL SAFETY NOTICE
    # -------------------------------------------------------------
    st.info(
        f"🛡️ **Clinical Safety Protocol:** {overview.get('clinical_safety_notice', 'VETRA tracks statistical anomalies. Outbreak declaration requires licensed veterinary confirmation.')}"
    )

    # -------------------------------------------------------------
    # 5. TOP KPI STRIP
    # -------------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    farms_count = overview.get("farms_monitored", 0)
    animals_count = overview.get("animals_monitored", 0)
    high_risk_count = overview.get("high_risk_farms_count", 0)
    active_events_count = overview.get("active_events_count", 0)
    clusters_count = overview.get("potential_clusters_count", 0)
    hotspots_count = overview.get("geographic_hotspots_count", 0)

    kpi1.metric("Farms Monitored", f"{farms_count}")
    kpi2.metric("Animals Monitored", f"{animals_count}")
    kpi3.metric(
        "High-Risk Farms",
        f"{high_risk_count}",
        delta=f"{high_risk_count} Elevated" if high_risk_count > 0 else "0 Nominal",
        delta_color="inverse"
    )
    kpi4.metric("Active Disease Events", f"{active_events_count}")
    kpi5.metric("Potential Clusters", f"{clusters_count}", help="Statistical clustering; not confirmed outbreaks")
    kpi6.metric("Geographic Hotspots", f"{hotspots_count}")

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 6. SURVEILLANCE TABS
    # -------------------------------------------------------------
    tab_map, tab_watch, tab_clusters, tab_events, tab_trends, tab_regional, tab_drill, tab_visual = st.tabs([
        "🗺️ Geospatial Risk Map",
        "📋 Farm Risk Watchlist",
        "🧬 Potential Clusters & Hotspots",
        "🚨 Disease Events",
        "📈 Surveillance Trends",
        "🏛️ Regional Intelligence",
        "🔍 Farm Drill-Down",
        "👁️ Visual Disease Signals"
    ])

    # =============================================================
    # TAB 1: GEOSPATIAL RISK MAP
    # =============================================================
    with tab_map:
        st.subheader("Geospatial Herd Risk & Holding Proximity")
        st.caption("Visualizes geographical distribution of monitored holdings, evaluated risk tiers, and potential proximity associations.")

        farms_with_coords = [f for f in risk_map_items if f.get("has_coordinates") and f.get("latitude") is not None and f.get("longitude") is not None]
        farms_without_coords = [f for f in risk_map_items if not f.get("has_coordinates") or f.get("latitude") is None or f.get("longitude") is None]

        col_map_view, col_map_legend = st.columns([3, 1])

        with col_map_view:
            if farms_with_coords:
                lats = [f["latitude"] for f in farms_with_coords]
                lons = [f["longitude"] for f in farms_with_coords]
                names = [f["farm_name"] for f in farms_with_coords]
                scores = [f["risk_score"] for f in farms_with_coords]
                categories = [f["risk_category"] for f in farms_with_coords]
                colors = [f["status_color"] for f in farms_with_coords]

                hover_texts = [
                    f"<b>{name}</b><br>Risk: {cat} ({score}/100)<br>Affected Animals: {f['affected_animals']}<br>Active Alerts: {f['active_alerts']}"
                    for name, score, cat, f in zip(names, scores, categories, farms_with_coords)
                ]

                avg_lat = sum(lats) / len(lats)
                avg_lon = sum(lons) / len(lons)

                fig = go.Figure(go.Scattermapbox(
                    lat=lats,
                    lon=lons,
                    mode='markers+text',
                    marker=go.scattermapbox.Marker(
                        size=18,
                        color=colors,
                        opacity=0.9
                    ),
                    text=names,
                    textposition="top right",
                    textfont=dict(size=12, color="#0f172a"),
                    hovertext=hover_texts,
                    hoverinfo="text"
                ))

                # Add Hotspot circles if any
                for h in hotspots:
                    fig.add_trace(go.Scattermapbox(
                        lat=[h["center_latitude"]],
                        lon=[h["center_longitude"]],
                        mode='markers',
                        marker=go.scattermapbox.Marker(
                            size=36,
                            color="rgba(239, 68, 68, 0.25)",
                            symbol="circle"
                        ),
                        hovertext=f"<b>Hotspot: {h['hotspot_id']}</b><br>Radius: {h['radius_km']} km<br>Risk: {h['risk_score']}",
                        hoverinfo="text",
                        showlegend=False
                    ))

                fig.update_layout(
                    mapbox_style="open-street-map",
                    mapbox=dict(
                        center=dict(lat=avg_lat, lon=avg_lon),
                        zoom=9
                    ),
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=460
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("🗺️ No farm coordinates currently registered. Showing holding distribution list below.")

        with col_map_legend:
            st.markdown(
                """
                <div style="background: #151F2E; border: 1px solid #273449; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: #F8FAFC; margin-bottom: 0.5rem; letter-spacing: 0.05em;">RISK TIERS</div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                        <span style="width: 12px; height: 12px; border-radius: 50%; background: #22C55E; display: inline-block;"></span>
                        <span style="font-size: 0.85rem; color: #CBD5E1;"><strong>LOW</strong> (0–24)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                        <span style="width: 12px; height: 12px; border-radius: 50%; background: #FBBF24; display: inline-block;"></span>
                        <span style="font-size: 0.85rem; color: #CBD5E1;"><strong>MODERATE</strong> (25–49)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                        <span style="width: 12px; height: 12px; border-radius: 50%; background: #F97316; display: inline-block;"></span>
                        <span style="font-size: 0.85rem; color: #CBD5E1;"><strong>HIGH</strong> (50–74)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="width: 12px; height: 12px; border-radius: 50%; background: #EF4444; display: inline-block;"></span>
                        <span style="font-size: 0.85rem; color: #CBD5E1;"><strong>CRITICAL</strong> (75–100)</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if farms_without_coords:
                st.warning(
                    f"📍 **Location unavailable for {len(farms_without_coords)} holding(s):**\n" +
                    "\n".join([f"- {f['farm_name']} ({f['location']})" for f in farms_without_coords]) +
                    "\n\n*Coordinates can be configured by administrators in Farm Settings.*"
                )

    # =============================================================
    # TAB 2: FARM RISK WATCHLIST & PATTERNS
    # =============================================================
    with tab_watch:
        st.subheader("Holding Surveillance Watchlist")
        st.caption("Deterministic scoring evaluates telemetry anomaly percentage, active alerts, clinical cases, and preventive gaps.")

        if watchlist:
            df_watch = pd.DataFrame(watchlist)
            df_display = df_watch[[
                "farm_name", "location", "risk_category", "risk_score",
                "affected_animals", "active_alerts", "dominant_pattern", "last_signal", "recommended_action"
            ]].copy()
            df_display.columns = [
                "Holding Name", "Location", "Risk Tier", "Score",
                "Affected Animals", "Active Alerts", "Dominant Pattern", "Trend", "Recommended Action"
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No holdings currently registered.")

        st.divider()
        st.subheader("Disease Pattern Distribution")
        p_col1, p_col2 = st.columns([1, 1])

        with p_col1:
            patterns = [p.get("dominant_disease_pattern", "Baseline") for p in farm_profiles]
            pattern_counts = pd.Series(patterns).value_counts().reset_index()
            pattern_counts.columns = ["Disease Pattern", "Holdings Affected"]

            fig_p = px.bar(
                pattern_counts,
                x="Holdings Affected",
                y="Disease Pattern",
                orientation='h',
                title="Dominant Syndromic Patterns Across Holdings",
                color="Holdings Affected",
                color_continuous_scale="Blues"
            )
            fig_p.update_layout(height=280, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

        with p_col2:
            st.markdown(
                """
                <div style="background: #151F2E; padding: 1.25rem; border-radius: 8px; border: 1px solid #273449; border-left: 4px solid #38BDF8;">
                    <div style="font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">Clinical Pattern Insights</div>
                    <ul style="font-size: 0.9rem; color: #CBD5E1; margin: 0; padding-left: 1.2rem; line-height: 1.6;">
                        <li><strong>Thermal Elevation / Fever:</strong> High core temperature (>39.5°C) with synchronous heart rate elevation.</li>
                        <li><strong>Respiratory Stress Pattern:</strong> Tachypnea (>38 bpm) with depressed activity.</li>
                        <li><strong>Rumination / Metabolic Drop:</strong> Rumination under 300 min/day indicating digestive cessation.</li>
                        <li><strong>Multi-system Anomaly:</strong> Simultaneous deviations across multiple organ systems.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True
            )

    # =============================================================
    # TAB 3: POTENTIAL CLUSTERS & HOTSPOTS
    # =============================================================
    with tab_clusters:
        st.subheader("Statistical Disease Clusters & Hotspot Detection")
        st.caption("Clusters represent statistical aggregations of similar anomalies and do NOT constitute confirmed outbreaks without veterinary investigation.")

        if clusters:
            for c in clusters:
                risk_val = c.get("risk_score", 0.0)
                badge_bg = "#fee2e2" if risk_val >= 60 else "#fef3c7"
                badge_fg = "#b91c1c" if risk_val >= 60 else "#b45309"

                with st.expander(f"🧬 {c.get('cluster_id')}: {c.get('title')} — Risk: {risk_val}/100", expanded=True):
                    c_col1, c_col2 = st.columns([2, 1])
                    with c_col1:
                        st.markdown(f"**Disease Pattern:** `{c.get('disease_pattern')}`")
                        st.markdown(f"**Holdings Involved:** {', '.join(c.get('farm_names', []))}")
                        st.markdown(f"**Affected Animals:** {c.get('affected_animal_count')} animal(s)")
                        st.markdown(f"**Geographic Spread:** {c.get('geographic_spread')}")
                        st.markdown(f"**First Detected:** `{c.get('first_detected')}` | **Last Signal:** `{c.get('last_detected')}`")
                        st.markdown(f"**Contributing Factors:**")
                        for f in c.get("contributing_factors", []):
                            st.write(f"- {f}")
                        st.warning(f"💡 **Recommended Action:** {c.get('recommended_action')}")
                        st.caption(f"🛡️ *{c.get('clinical_disclaimer')}*")

                    with c_col2:
                        st.metric("Cluster Risk Score", f"{risk_val}/100")
                        st.metric("Statistical Confidence", f"{c.get('confidence', 0.8) * 100:.0f}%")
                        st.markdown(f"**Lifecycle Status:** `{c.get('status').upper()}`")

                        if user_role in ["veterinarian", "admin"]:
                            if st.button(f"🔍 Investigate Cluster {c.get('cluster_id')}", key=f"inv_btn_{c.get('cluster_id')}"):
                                st.session_state["cluster_to_investigate"] = c
                                st.info("Escalate cluster to clinical case from the Clinical Cases tab.")
        else:
            st.success("✅ No statistical disease clusters detected across monitored holdings.")

        st.divider()
        st.subheader("Geographic Hotspots")
        if hotspots:
            for h in hotspots:
                st.markdown(
                    f"""
                    <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.35); padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem;">
                        <div style="font-weight: 700; color: #FCA5A5; font-size: 1.05rem;">📍 Hotspot: {h['hotspot_id']} (Center: {h['center_latitude']}, {h['center_longitude']})</div>
                        <div style="font-size: 0.9rem; color: #CBD5E1; margin-top: 0.25rem;">
                            Radius: <strong>{h['radius_km']} km</strong> | Holdings: <strong>{', '.join(h['affected_farm_names'])}</strong> | Animals: <strong>{h['affected_animal_count']}</strong>
                        </div>
                        <div style="font-size: 0.9rem; color: #F87171; margin-top: 0.4rem; font-weight: 500;">
                            Recommendation: {h['recommendation']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No geographic hotspots detected with active coordinates.")

    # =============================================================
    # TAB 4: DISEASE EVENTS
    # =============================================================
    with tab_events:
        st.subheader("Disease Events & Field Investigation Registry")
        st.caption("Official register of reported disease events, investigations, and veterinary resolutions.")

        # Reporting form
        with st.expander("➕ Report New Disease Event / Suspected Anomaly", expanded=False):
            with st.form("new_disease_event_form"):
                rf_col1, rf_col2 = st.columns(2)
                with rf_col1:
                    farm_opts = {f["farm_name"]: f["farm_id"] for f in farm_profiles}
                    sel_farm_name = st.selectbox("Holding", options=list(farm_opts.keys()))
                    disease_name_in = st.text_input("Suspected Disease / Syndrome", placeholder="e.g. Bovine Respiratory Disease")
                    category_in = st.selectbox("Syndrome Category", ["respiratory", "enteric", "metabolic", "thermal", "reproductive", "general"])
                with rf_col2:
                    severity_in = st.selectbox("Assessed Severity", ["low", "medium", "high", "critical"], index=1)
                    source_in = st.selectbox("Event Source", ["manual_report", "health_monitoring", "ai_detection", "preventive_screening", "veterinary_case", "laboratory_result"])
                    onset_in = st.date_input("Estimated Onset Date", value=datetime.now())

                symptoms_in = st.text_area("Observed Symptoms (comma separated)", placeholder="Coughing, nasal discharge, pyrexia, lethargy")
                notes_in = st.text_area("Clinical Notes & Observations", placeholder="Enter field observations, pen numbers, feed intake notes...")

                submitted = st.form_submit_button("Submit Disease Event", type="primary")
                if submitted:
                    if not disease_name_in.strip():
                        st.error("Please provide a disease or syndrome name.")
                    else:
                        payload = {
                            "farm_id": farm_opts[sel_farm_name],
                            "disease_name": disease_name_in.strip(),
                            "disease_category": category_in,
                            "symptoms": [s.strip() for s in symptoms_in.split(",") if s.strip()],
                            "observed_signs": [],
                            "severity": severity_in,
                            "confidence": 0.75,
                            "source": source_in,
                            "onset_date": onset_in.strftime("%Y-%m-%d"),
                            "notes": notes_in.strip() or None
                        }
                        success, res = api_client.create_disease_event(payload)
                        if success:
                            st.success(f"Disease event registered successfully! Event Number: {res.get('event_number')}")
                            st.rerun()
                        else:
                            st.error(f"Failed to register disease event: {res}")

        if events:
            df_ev = pd.DataFrame(events)
            st.dataframe(
                df_ev[[
                    "event_number", "farm_name", "disease_name", "disease_category",
                    "severity", "status", "source", "onset_date", "created_at"
                ]],
                use_container_width=True,
                hide_index=True
            )

            if user_role in ["veterinarian", "admin"]:
                st.subheader("Update Event Status / Clinical Outcome")
                u_col1, u_col2, u_col3 = st.columns([2, 1, 1])
                with u_col1:
                    ev_opts = {f"{e['event_number']} — {e['disease_name']} ({e['farm_name']})": e["id"] for e in events}
                    target_ev_str = st.selectbox("Select Event to Update", options=list(ev_opts.keys()))
                    target_ev_id = ev_opts[target_ev_str]
                with u_col2:
                    new_status = st.selectbox("Update Status", ["suspected", "under_investigation", "confirmed", "ruled_out", "resolved"], index=1)
                with u_col3:
                    st.write("")
                    st.write("")
                    if st.button("Save Event Status", use_container_width=True):
                        success, res = api_client.update_disease_event(target_ev_id, {"status": new_status})
                        if success:
                            st.success("Event updated successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to update event: {res}")
        else:
            st.info("No disease events currently recorded.")

    # =============================================================
    # TAB 5: SURVEILLANCE TRENDS
    # =============================================================
    with tab_trends:
        st.subheader("Surveillance Temporal Analytics")
        st.caption(f"Rolling historical trend over the selected window ({window_days} days).")

        trends_data = api_client.get_surveillance_trends(period_days=window_days)
        ts_points = trends_data.get("time_series", [])

        if ts_points:
            df_ts = pd.DataFrame(ts_points)

            tr_col1, tr_col2 = st.columns(2)
            with tr_col1:
                fig_obs = px.line(
                    df_ts,
                    x="date",
                    y=["observation_count", "affected_animals"],
                    title="Daily Disease Observations & Affected Animals",
                    labels={"value": "Count", "date": "Date", "variable": "Metric"},
                    markers=True
                )
                fig_obs.update_layout(
                    template="plotly_dark",
                    height=320,
                    margin=dict(l=0, r=0, t=35, b=0),
                    plot_bgcolor="#111827",
                    paper_bgcolor="#151F2E",
                    font=dict(color="#F8FAFC")
                )
                st.plotly_chart(fig_obs, use_container_width=True)

            with tr_col2:
                fig_risk = px.line(
                    df_ts,
                    x="date",
                    y="average_risk_score",
                    title="Average Population Risk Score Trajectory",
                    labels={"average_risk_score": "Risk (0-100)", "date": "Date"},
                    markers=True,
                    color_discrete_sequence=["#ea580c"]
                )
                fig_risk.update_layout(
                    template="plotly_dark",
                    height=320,
                    margin=dict(l=0, r=0, t=35, b=0),
                    plot_bgcolor="#111827",
                    paper_bgcolor="#151F2E",
                    font=dict(color="#F8FAFC")
                )
                st.plotly_chart(fig_risk, use_container_width=True)
        else:
            st.info("No trend telemetry points recorded for this window.")

    # =============================================================
    # TAB 6: REGIONAL INTELLIGENCE
    # =============================================================
    with tab_regional:
        st.subheader("Regional Surveillance Aggregations")
        st.caption("District-level and state-level surveillance aggregations for institutional and veterinary monitoring.")

        if regions:
            df_reg = pd.DataFrame(regions)
            st.dataframe(
                df_reg[[
                    "region_key", "surveillance_level", "average_risk_score", "farms_count",
                    "animals_count", "high_risk_farms_count", "active_disease_events_count", "active_clusters_count"
                ]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No regional geographic grouping available.")

    # =============================================================
    # TAB 7: FARM DRILL-DOWN
    # =============================================================
    with tab_drill:
        st.subheader("Farm-Specific Surveillance Deep Dive")

        if farm_profiles:
            farm_names = {f["farm_name"]: f["farm_id"] for f in farm_profiles}
            selected_f_name = st.selectbox("Select Holding to Inspect", options=list(farm_names.keys()), key="drill_farm_select")
            selected_f_id = farm_names[selected_f_name]

            f_prof = next((p for p in farm_profiles if p["farm_id"] == selected_f_id), None)
            if f_prof:
                fd_col1, fd_col2, fd_col3 = st.columns([1, 1, 1])
                fd_col1.metric("Holding Risk Score", f"{f_prof['risk_score']}/100", f_prof["risk_category"])
                fd_col2.metric("Affected Animals", f"{f_prof['affected_animals_count']}/{f_prof['total_animals']}", f"{f_prof['abnormal_animals_pct']}% Herd")
                fd_col3.metric("Dominant Pattern", f_prof["dominant_disease_pattern"], f"Trend: {f_prof.get('trend', 'stable').capitalize()}")

                st.markdown("#### Contributing Risk Factors")
                for factor in f_prof.get("contributing_factors", []):
                    st.write(f"- {factor}")

                # AI Narrative section
                st.markdown("#### AI Surveillance Intelligence & Investigation Plan")
                analysis_cache = st.session_state.get("surv_last_analysis")
                if analysis_cache and analysis_cache.get("ai_explanation"):
                    expl = analysis_cache["ai_explanation"]
                    st.markdown(f"**Clinical Interpretation:** {expl.get('pattern_explanation')}")
                    st.markdown(f"**Surveillance Risk:** {expl.get('risk_interpretation')}")
                    st.markdown(f"**Cluster Analysis:** {expl.get('cluster_explanation')}")
                    st.markdown("**Prioritized Field Recommendations:**")
                    for rec in expl.get("surveillance_recommendations", []):
                        st.write(f"- {rec}")
                    st.markdown("**Questions for Investigating Veterinarian:**")
                    for q in expl.get("veterinary_questions", []):
                        st.write(f"- *{q}*")
                else:
                    if st.button("Generate AI Surveillance Explanation for this Holding", key="btn_gen_ai_farm"):
                        with st.spinner("Generating AI clinical narrative..."):
                            res = api_client.trigger_surveillance_analysis(farm_id=selected_f_id)
                            if res:
                                st.session_state["surv_last_analysis"] = res
                                st.rerun()
                            else:
                                st.warning("Analysis temporarily unavailable.")
        else:
            st.info("No farm profiles available.")

    # =============================================================
    # TAB 8: VISUAL DISEASE SIGNALS (PHASE 9 INTEGRATION)
    # =============================================================
    with tab_visual:
        st.subheader("👁️ Syndromic Visual Disease Signals & Cluster Indicators")
        st.caption("Aggregated photographic observations across holdings to detect syndromic patterns and supporting evidence.")

        st.info(
            "🛡️ **Surveillance Note:** Multiple animals showing similar visual observations (e.g. skin abnormalities, "
            "posture irregularities, ocular discharge) serve as supporting evidence for syndromic surveillance. "
            "Visual observations do NOT constitute a confirmed disease diagnosis."
        )

        vh_summary = api_client.get_visual_health_summary()
        dominant_signals = vh_summary.get("dominant_visual_signals", [])

        vk1, vk2, vk3 = st.columns(3)
        with vk1:
            st.metric("Total Visual Observations", vh_summary.get("total_observations", 0))
        with vk2:
            st.metric("Animals Screened", vh_summary.get("animals_assessed", 0))
        with vk3:
            st.metric("Elevated Risk Analyses", vh_summary.get("high_risk_analyses", 0))

        st.markdown("#### Dominant Visual Health Signal Frequency")
        if not dominant_signals:
            st.info("No syndromic visual signals currently aggregated in the surveillance window.")
        else:
            sig_df = pd.DataFrame([
                {"Indicator": s["indicator"].replace("_", " ").title(), "Occurrences": s["count"]}
                for s in dominant_signals
            ])
            fig_sig = px.bar(
                sig_df,
                x="Occurrences",
                y="Indicator",
                orientation="h",
                color="Occurrences",
                color_continuous_scale="Blues"
            )
            fig_sig.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1")
            )
            st.plotly_chart(fig_sig, use_container_width=True)

        st.markdown("#### Recent Syndromic Visual Observations Log")
        vis_obs = api_client.get_visual_observations(limit=25)
        if not vis_obs:
            st.info("No individual visual indicator logs available.")
        else:
            obs_rows = []
            for vo in vis_obs:
                obs_rows.append({
                    "Timestamp": vo.get("timestamp", "")[:16].replace("T", " "),
                    "Animal": vo.get("animal_tag") or vo.get("animal_id"),
                    "Indicator": vo.get("indicator", "").replace("_", " ").title(),
                    "Severity": vo.get("severity", "medium").upper(),
                    "Confidence": f"{vo.get('confidence', 0)*100:.0f}%",
                    "Description": vo.get("description", "")
                })
            st.dataframe(pd.DataFrame(obs_rows), use_container_width=True)


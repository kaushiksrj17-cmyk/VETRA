from datetime import datetime, timezone
import time
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import api_client
from session import get_user_info
from styles import render_dashboard_hero


def _navigate_to(page_name: str, animal_id: Optional[str] = None):
    """
    Safely transition to another VETRA application page.
    """
    if animal_id:
        st.session_state["selected_animal_id"] = animal_id
        st.session_state["open_animal_profile"] = True

    st.session_state["nav_choice"] = page_name
    st.rerun()


def render_dashboard_page():
    """
    VETRA Phase 7.3 — Advanced Real-Time Command Center.
    Brings together farm management, animal telemetry, live health activity,
    alerts triage, AI clinical risk intelligence, early warning signals,
    preventive healthcare, veterinary cases, hardware fleet health,
    and safe real-time synchronization.
    """
    user_info = get_user_info()
    user_role = str(user_info.get("role", "farmer")).lower()

    # ============================================================
    # 1. SYSTEM HEALTH & REAL-TIME CONNECTIVITY PROBE
    # ============================================================
    sys_health = api_client.get_system_health()
    backend_status = sys_health.get("backend", "offline")
    db_status = sys_health.get("database", "disconnected")
    ai_status = sys_health.get("ai_engine", "operational")
    ws_status = api_client.get_websocket_status()

    # Evaluate overall system indicator
    is_online = (backend_status == "online" and db_status == "connected")
    sys_badge_color = "#059669" if is_online else ("#ea580c" if backend_status == "online" else "#dc2626")
    sys_badge_label = "● SYSTEM ONLINE" if is_online else ("● SYSTEM DEGRADED" if backend_status == "online" else "● SYSTEM OFFLINE")

    ws_color_map = {
        "LIVE": "#059669",
        "SYNCING": "#ca8a04",
        "OFFLINE": "#dc2626"
    }
    ws_color = ws_color_map.get(ws_status, "#64748b")
    ws_icon = "🟢" if ws_status == "LIVE" else ("🟡" if ws_status == "SYNCING" else "🔴")

    # ============================================================
    # 2. TOP COMMAND CENTER HERO & HEADER
    # ============================================================
    render_dashboard_hero()

    header_left, header_right = st.columns([3, 1.4])

    with header_left:
        st.markdown(
            f"""
            <div style="margin-bottom: 0.25rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                    <span style="background: {sys_badge_color}18; color: {sys_badge_color}; border: 1px solid {sys_badge_color}50; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.65rem; border-radius: 9999px;">
                        {sys_badge_label}
                    </span>
                    <span style="background: {ws_color}18; color: {ws_color}; border: 1px solid {ws_color}50; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.65rem; border-radius: 9999px;" title="WebSocket Monitoring Channel (/ws/monitoring)">
                        {ws_icon} {ws_status}
                    </span>
                    <span style="font-size: 0.8rem; color: #94A3B8;">Last telemetry sync: <strong style="color: #CBD5E1;">{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</strong></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with header_right:
        ar_col, btn_col = st.columns([1.5, 1])
        with ar_col:
            auto_refresh = st.checkbox(
                "🔄 Auto-refresh (12s)",
                value=st.session_state.get("dash_auto_refresh", True),
                key="dash_auto_refresh_toggle",
                help="Automatically re-queries operational endpoints every 12 seconds"
            )
            st.session_state["dash_auto_refresh"] = auto_refresh
        with btn_col:
            if st.button("⚡ Refresh", use_container_width=True, help="Force sync latest telemetry and analytics"):
                st.rerun()

        st.caption(f"Last data update: **{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}**")

    # Expandable Subsystem Telemetry Details
    with st.expander("🛠️ Subsystem Status & Diagnostics", expanded=False):
        sub_c1, sub_c2, sub_c3, sub_c4, sub_c5 = st.columns(5)
        with sub_c1:
            st.markdown(f"**FastAPI Backend:** `{'ONLINE' if backend_status == 'online' else 'UNREACHABLE'}`")
        with sub_c2:
            st.markdown(f"**MongoDB Atlas:** `{'CONNECTED' if db_status == 'connected' else 'DISCONNECTED'}`")
        with sub_c3:
            st.markdown(f"**AI Engine:** `{'OPERATIONAL' if ai_status == 'operational' else 'DEGRADED'}`")
        with sub_c4:
            st.markdown(f"**Telemetry Bus:** `{ws_status}`")
        with sub_c5:
            st.markdown(f"**Analytics Engine:** `READY`")

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 3. GLOBAL FILTERS RIBBON
    # ============================================================
    farms_list = api_client.get_farms()
    farm_options = {"all": "All Monitored Farms"}
    for f in farms_list:
        farm_options[f["id"]] = f.get("name", "Farm")

    f1, f2, f3, f4 = st.columns([1.4, 1.1, 1.1, 1.2])

    with f1:
        saved_farm = st.session_state.get("dash_farm_filter", "all")
        if saved_farm not in farm_options:
            saved_farm = "all"
        selected_farm_id = st.selectbox(
            "🏢 Farm Scope",
            options=list(farm_options.keys()),
            format_func=lambda fid: farm_options[fid],
            index=list(farm_options.keys()).index(saved_farm),
            key="dash_farm_filter"
        )

    with f2:
        species_options = {
            "all": "All Species",
            "cattle": "Cattle (Bovine)",
            "buffalo": "Buffalo",
            "goat": "Goat (Caprine)",
            "sheep": "Sheep (Ovine)"
        }
        saved_species = st.session_state.get("dash_species_filter", "all")
        if saved_species not in species_options:
            saved_species = "all"
        selected_species = st.selectbox(
            "🐄 Livestock Species",
            options=list(species_options.keys()),
            format_func=lambda s: species_options[s],
            index=list(species_options.keys()).index(saved_species),
            key="dash_species_filter"
        )

    with f3:
        timeframe_options = {
            1: "24 Hours (Hourly)",
            7: "7 Days (Daily)",
            30: "30 Days (Daily)",
            90: "90 Days (Daily)"
        }
        saved_days = st.session_state.get("dash_days_filter", 7)
        if saved_days not in timeframe_options:
            saved_days = 7
        selected_days = st.selectbox(
            "📅 Analysis Window",
            options=list(timeframe_options.keys()),
            format_func=lambda d: timeframe_options[d],
            index=list(timeframe_options.keys()).index(saved_days),
            key="dash_days_filter"
        )

    with f4:
        scope_label = "Global (All Farms)" if selected_farm_id == "all" else f"Scoped: {farm_options.get(selected_farm_id, 'Farm')}"
        st.markdown(
            f"""
            <div style="background: #151F2E; border: 1px solid #273449; border-radius: 8px; padding: 0.55rem 0.75rem; margin-top: 1.6rem; text-align: center;">
                <span style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.05em;">ACTIVE SCOPE</span>
                <div style="font-size: 0.85rem; font-weight: 700; color: #F8FAFC; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 0.15rem;">
                    {scope_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 4. FETCH OPERATIONAL ANALYTICS DATA
    # ============================================================
    with st.spinner("Compiling real-time herd operations & intelligence..."):
        try:
            overview_data = api_client.get_analytics_overview(
                farm_id=selected_farm_id,
                species=selected_species,
                days=selected_days
            )
        except Exception:
            overview_data = {}

        try:
            trends_data = api_client.get_analytics_health_trends(
                farm_id=selected_farm_id,
                species=selected_species,
                days=selected_days
            )
        except Exception:
            trends_data = {}

        try:
            alerts_data = api_client.get_analytics_alerts(
                farm_id=selected_farm_id,
                days=selected_days
            )
        except Exception:
            alerts_data = {}

        try:
            prevention_data = api_client.get_analytics_prevention(
                farm_id=selected_farm_id
            )
        except Exception:
            prevention_data = {}

        try:
            veterinary_data = api_client.get_analytics_veterinary(
                farm_id=selected_farm_id
            )
        except Exception:
            veterinary_data = {}

        try:
            devices_data = api_client.get_analytics_devices(
                farm_id=selected_farm_id
            )
        except Exception:
            devices_data = {}

        try:
            watchlist_data = api_client.get_analytics_watchlist(
                farm_id=selected_farm_id
            )
        except Exception:
            watchlist_data = {}

        try:
            animals_list = api_client.get_animals()
        except Exception:
            animals_list = []

        try:
            recent_readings = api_client.get_health_readings(
                limit=15,
                farm_id=selected_farm_id
            )
        except Exception:
            recent_readings = []

    kpis = overview_data.get("kpis", {})
    risk_dist = overview_data.get("risk_distribution", {})
    hhi = overview_data.get("herd_health_index", {})

    # ============================================================
    # 5. LIVE KPI STRIP (8 PRIMARY OPERATIONAL METRICS)
    # ============================================================
    total_animals = kpis.get("total_animals", len(animals_list))
    healthy_animals = kpis.get("healthy_animals", 0)
    monitoring_animals = kpis.get("animals_under_monitoring", 0)
    at_risk_animals = kpis.get("high_risk_animals", 0)
    critical_animals = kpis.get("critical_animals", 0)
    attention_required = monitoring_animals + at_risk_animals + critical_animals

    active_alerts = kpis.get("active_alerts", 0)
    crit_alerts = kpis.get("critical_alerts", 0)
    open_cases = kpis.get("open_veterinary_cases", 0)
    prev_due = kpis.get("preventive_actions_due", 0)
    prev_comp = kpis.get("preventive_compliance", 100.0)
    dev_online = kpis.get("devices_online", 0)
    dev_total = kpis.get("total_devices", 0)

    st.markdown(
        """
        <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">
            📊 Live Fleet KPIs & Operational Status
        </div>
        """,
        unsafe_allow_html=True
    )

    kpi_cols = st.columns(8)

    with kpi_cols[0]:
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Total Herd</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: #F8FAFC;">{total_animals}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Registered</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Herd →", key="kpi_nav_animals", use_container_width=True):
            _navigate_to("🐄 Animals")

    with kpi_cols[1]:
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Healthy / Low</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: #22C55E;">{healthy_animals}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Baseline normal</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.caption("Optimal state")

    with kpi_cols[2]:
        attn_color = "#DC2626" if critical_animals > 0 else ("#F97316" if at_risk_animals > 0 else ("#F59E0B" if monitoring_animals > 0 else "#22C55E"))
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Need Attention</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: {attn_color};">{attention_required}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Variance / Risk</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.caption(f"{critical_animals} crit • {at_risk_animals} risk")

    with kpi_cols[3]:
        al_color = "#DC2626" if active_alerts > 0 else "#22C55E"
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Active Alerts</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: {al_color};">{active_alerts}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Open warnings</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Alerts →", key="kpi_nav_alerts", use_container_width=True):
            _navigate_to("🚨 Alerts")

    with kpi_cols[4]:
        crit_color = "#DC2626" if crit_alerts > 0 else "#94A3B8"
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Critical Alerts</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: {crit_color};">{crit_alerts}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Urgent priority</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.caption("Action required" if crit_alerts > 0 else "None pending")

    with kpi_cols[5]:
        vc_color = "#F97316" if open_cases > 0 else "#22C55E"
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Clinical Cases</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: {vc_color};">{open_cases}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">Active caseload</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Cases →", key="kpi_nav_cases", use_container_width=True):
            _navigate_to("🩺 Clinical Cases")

    with kpi_cols[6]:
        prev_color = "#DC2626" if prev_due > 0 else "#38BDF8"
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Preventive Due</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: {prev_color};">{prev_due}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">{prev_comp:.0f}% compliant</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Vaccine →", key="kpi_nav_prev", use_container_width=True):
            _navigate_to("💉 Preventive Health")

    with kpi_cols[7]:
        st.markdown(
            f"""
            <div class="kpi-card" style="padding: 0.75rem 0.65rem; text-align: center;">
                <div class="kpi-label" style="font-size: 0.68rem;">Nodes Online</div>
                <div class="kpi-value" style="font-size: 1.55rem; color: #38BDF8;">{dev_online}/{dev_total}</div>
                <div class="kpi-sub" style="font-size: 0.68rem;">ESP32 telemetry</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("IoT →", key="kpi_nav_devices", use_container_width=True):
            _navigate_to("📡 Live Monitoring")

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 6. HERD HEALTH OVERVIEW & POPULATION RISK DISTRIBUTION
    # ============================================================
    hhi_col, risk_col = st.columns([1.6, 1.4])

    with hhi_col:
        score = hhi.get("score", 100.0)
        band = hhi.get("band", "Optimal")
        trend = hhi.get("trend", "stable")
        summary_text = hhi.get("summary", "Herd physiological metrics align with healthy baselines.")
        pos_factors = hhi.get("contributing_positive", [])
        neg_factors = hhi.get("contributing_negative", [])

        band_colors = {
            "Excellent": "#059669",
            "Optimal": "#059669",
            "Good": "#10b981",
            "Attention Required": "#ca8a04",
            "High Risk": "#ea580c",
            "Critical": "#dc2626"
        }
        band_color = band_colors.get(band, "#059669")

        trend_icons = {
            "positive": "📈 Improving",
            "stable": "➡️ Stable",
            "warning": "⚠️ Caution",
            "negative": "📉 Deteriorating",
            "critical": "🚨 Critical Alert"
        }
        trend_label = trend_icons.get(trend, "➡️ Stable")

        st.markdown(
            f"""
            <div class="vetra-panel" style="padding: 1.25rem; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">
                            VETRA Herd Health Index (HHI)
                        </div>
                        <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 0.2rem;">
                            Multi-factor physiological, alert & preventive composite score
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; background: {band_color}25; color: {band_color}; border: 1px solid {band_color}50;">
                            {band.upper()}
                        </span>
                        <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 0.25rem;">{trend_label}</div>
                    </div>
                </div>
                <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-top: 0.75rem;">
                    <div style="font-size: 2.85rem; font-weight: 800; color: {band_color}; line-height: 1;">
                        {score:.1f}
                    </div>
                    <div style="font-size: 1.1rem; color: #94A3B8; font-weight: 600;">/ 100</div>
                </div>
                <div style="width: 100%; background: #273449; height: 8px; border-radius: 4px; overflow: hidden; margin: 0.6rem 0;">
                    <div style="width: {min(100.0, max(0.0, score))}%; background: {band_color}; height: 100%;"></div>
                </div>
                <div style="font-size: 0.85rem; color: #CBD5E1; margin-bottom: 0.75rem;">
                    {summary_text}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
            """,
            unsafe_allow_html=True
        )

        tag_html = ""
        for pf in pos_factors:
            tag_html += f"<span style='font-size: 0.73rem; background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.35); border-radius: 6px; padding: 0.15rem 0.5rem;'>✓ {pf}</span> "
        for nf in neg_factors:
            tag_html += f"<span style='font-size: 0.73rem; background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 6px; padding: 0.15rem 0.5rem;'>⚠ {nf}</span> "

        st.markdown(tag_html + "</div></div>", unsafe_allow_html=True)

    with risk_col:
        st.markdown(
            """
            <div class="vetra-panel" style="padding: 1.25rem; height: 100%;">
                <div style="font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">
                    Population Health Risk Distribution
                </div>
                <div style="font-size: 0.82rem; color: #CBD5E1; margin-bottom: 0.75rem;">
                    Livestock categorized by clinical telemetry risk severity
                </div>
            """,
            unsafe_allow_html=True
        )

        low_cnt = risk_dist.get("low", {}).get("count", healthy_animals)
        med_cnt = risk_dist.get("medium", {}).get("count", monitoring_animals)
        high_cnt = risk_dist.get("high", {}).get("count", at_risk_animals)
        crit_cnt = risk_dist.get("critical", {}).get("count", critical_animals)

        labels = ["Low Risk", "Moderate Risk", "High Risk", "Critical Risk"]
        values = [low_cnt, med_cnt, high_cnt, crit_cnt]
        colors = ["#059669", "#ca8a04", "#ea580c", "#dc2626"]

        if sum(values) == 0:
            st.info("No livestock categorized in the active scope.")
        else:
            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.55,
                        marker=dict(colors=colors),
                        textinfo="value+percent",
                        hoverinfo="label+value+percent",
                        textfont=dict(size=12, family="Inter, sans-serif")
                    )
                ]
            )
            fig_pie.update_layout(
                height=180,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=10, color="#CBD5E1")),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 7. LIVE HEALTH ACTIVITY (MOST RECENT TELEMETRY FEED)
    # ============================================================
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">
                    📡 Live Health Activity & Telemetry Feed
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8;">
                    Chronological stream of sensor readings, physiological variance, and clinical risk flags
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not recent_readings:
        st.info("No recent health telemetry logged. Start the IoT simulator or connect ESP32 hardware to stream live readings.")
    else:
        # Build clean tabular view
        act_rows = []
        for r in recent_readings[:8]:
            t_val = r.get("temperature_c", 0.0)
            hr_val = r.get("heart_rate_bpm", 0.0)
            rr_val = r.get("respiratory_rate", 0.0)
            act_val = r.get("activity_level", 0.0)
            rum_val = r.get("rumination_level", 0.0)
            r_status = r.get("risk_status", "normal")

            # Timestamp format
            raw_ts = str(r.get("recorded_at") or r.get("created_at") or "")
            ts_display = raw_ts[11:19] if "T" in raw_ts else raw_ts[:19]

            # Highlight abnormal signs
            t_warn = " ⚠️" if (t_val > 39.5 or t_val < 37.0) else ""
            hr_warn = " ⚠️" if (hr_val > 85 or hr_val < 55) else ""
            rr_warn = " ⚠️" if (rr_val > 35 or rr_val < 12) else ""

            act_rows.append({
                "Animal": r.get("animal_name") or r.get("tag_id") or r.get("animal_id")[:8],
                "Tag": r.get("tag_id") or "N/A",
                "Temp (°C)": f"{t_val:.2f}{t_warn}",
                "HR (BPM)": f"{hr_val:.1f}{hr_warn}",
                "Resp (/min)": f"{rr_val:.1f}{rr_warn}",
                "Activity (%)": f"{act_val:.1f}%",
                "Rumination (%)": f"{rum_val:.1f}%",
                "Risk Evaluation": r_status.upper(),
                "Time (UTC)": ts_display,
                "_raw": r
            })

        df_act = pd.DataFrame(act_rows)
        st.dataframe(
            df_act[["Time (UTC)", "Animal", "Tag", "Temp (°C)", "HR (BPM)", "Resp (/min)", "Activity (%)", "Rumination (%)", "Risk Evaluation"]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 8. PHYSIOLOGICAL TELEMETRY TRENDS (PLOTLY)
    # ============================================================
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.35rem;">
            📈 Physiological Telemetry Trends & Clinical Safe Zones
        </div>
        """,
        unsafe_allow_html=True
    )

    t_mode_col, t_anim_col = st.columns([1.2, 1.8])
    with t_mode_col:
        view_mode = st.radio(
            "Telemetry Perspective",
            options=["Herd Baseline Aggregate", "Individual Livestock Drill-Down"],
            horizontal=True,
            key="telemetry_view_mode",
            label_visibility="collapsed"
        )

    selected_animal_for_trend = None
    if view_mode == "Individual Livestock Drill-Down":
        with t_anim_col:
            if animals_list:
                animal_choices = {
                    a["id"]: f"{a.get('name', 'Unnamed')} ({a.get('tag_id')}) - {a.get('species')}"
                    for a in animals_list
                }
                selected_animal_for_trend = st.selectbox(
                    "Select Animal",
                    options=list(animal_choices.keys()),
                    format_func=lambda aid: animal_choices[aid],
                    key="trend_animal_select",
                    label_visibility="collapsed"
                )
            else:
                st.caption("No registered animals found.")

    if selected_animal_for_trend:
        trends_data = api_client.get_analytics_health_trends(
            farm_id=selected_farm_id,
            animal_id=selected_animal_for_trend,
            days=selected_days
        )

    time_series = trends_data.get("time_series", [])

    if not time_series:
        st.info(f"No physiological readings logged within the selected {timeframe_options.get(selected_days, 'timeframe')}. Telemetry simulator will record new data on heartbeat.")
    else:
        df_trends = pd.DataFrame(time_series)

        if "time" not in df_trends.columns:
            if "timestamp" in df_trends.columns:
                df_trends["time"] = df_trends["timestamp"]
            elif "recorded_at" in df_trends.columns:
                df_trends["time"] = df_trends["recorded_at"].astype(str).str[11:19]
            elif "created_at" in df_trends.columns:
                df_trends["time"] = df_trends["created_at"].astype(str).str[11:19]
            else:
                df_trends["time"] = range(len(df_trends))

        for col in ["temperature_c", "heart_rate_bpm", "activity_level", "rumination_level", "respiratory_rate"]:
            if col not in df_trends.columns:
                df_trends[col] = None

        fig_vitals = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "🌡️ Body Temperature (°C) — Safe Zone [38.0 - 39.5]",
                "💓 Heart Rate (BPM) — Safe Zone [60 - 80]",
                "🏃 Activity & 🌿 Rumination Level (%)",
                "🫁 Respiration Rate (/min) — Safe Zone [15 - 30]"
            ),
            vertical_spacing=0.18,
            horizontal_spacing=0.08
        )

        fig_vitals.add_trace(
            go.Scatter(
                x=df_trends["time"],
                y=df_trends["temperature_c"],
                mode="lines+markers",
                name="Temperature (°C)",
                line=dict(color="#ef4444", width=2.5),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        fig_vitals.add_hline(y=39.5, line_dash="dash", line_color="#ea580c", annotation_text="Upper Normal", row=1, col=1)
        fig_vitals.add_hline(y=38.0, line_dash="dash", line_color="#059669", annotation_text="Lower Normal", row=1, col=1)

        fig_vitals.add_trace(
            go.Scatter(
                x=df_trends["time"],
                y=df_trends["heart_rate_bpm"],
                mode="lines+markers",
                name="Heart Rate (BPM)",
                line=dict(color="#3b82f6", width=2.5),
                marker=dict(size=4)
            ),
            row=1, col=2
        )
        fig_vitals.add_hline(y=80, line_dash="dash", line_color="#ea580c", row=1, col=2)
        fig_vitals.add_hline(y=60, line_dash="dash", line_color="#059669", row=1, col=2)

        fig_vitals.add_trace(
            go.Scatter(
                x=df_trends["time"],
                y=df_trends["activity_level"],
                mode="lines",
                name="Activity (%)",
                line=dict(color="#8b5cf6", width=2)
            ),
            row=2, col=1
        )
        fig_vitals.add_trace(
            go.Scatter(
                x=df_trends["time"],
                y=df_trends["rumination_level"],
                mode="lines",
                name="Rumination (%)",
                line=dict(color="#10b981", width=2)
            ),
            row=2, col=1
        )

        fig_vitals.add_trace(
            go.Scatter(
                x=df_trends["time"],
                y=df_trends["respiratory_rate"],
                mode="lines+markers",
                name="Respiration (/min)",
                line=dict(color="#06b6d4", width=2.5),
                marker=dict(size=4)
            ),
            row=2, col=2
        )
        fig_vitals.add_hline(y=30, line_dash="dash", line_color="#ea580c", row=2, col=2)
        fig_vitals.add_hline(y=15, line_dash="dash", line_color="#059669", row=2, col=2)

        fig_vitals.update_layout(
            template="plotly_dark",
            height=460,
            margin=dict(l=20, r=20, t=35, b=20),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(color="#CBD5E1")),
            plot_bgcolor="#151F2E",
            paper_bgcolor="#151F2E"
        )
        fig_vitals.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#273449", tickfont=dict(color="#94A3B8"))
        fig_vitals.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#273449", tickfont=dict(color="#94A3B8"))

        st.plotly_chart(fig_vitals, use_container_width=True)

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 9. OPERATIONAL INTELLIGENCE TABS
    # ============================================================
    tab_alerts, tab_watch, tab_ai, tab_prev, tab_vet, tab_dev = st.tabs([
        "🚨 Alert Intelligence",
        "⚠️ Priority Attention Watchlist",
        "🤖 AI Health Intelligence",
        "💉 Preventive Care",
        "🩺 Veterinary Operations",
        "📡 IoT Fleet & Hardware Health"
    ])

    # ------------------------------------------------------------
    # TAB 1: ALERTS INTELLIGENCE
    # ------------------------------------------------------------
    with tab_alerts:
        a_left, a_right = st.columns([1.2, 1.8])

        with a_left:
            tot_a = alerts_data.get("total_alerts", 0)
            act_a = alerts_data.get("active_alerts", 0)
            ack_a = alerts_data.get("acknowledged_alerts", 0)
            res_a = alerts_data.get("resolved_alerts", 0)
            mtta_str = alerts_data.get("mtta_display", "Insufficient data")
            mttr_str = alerts_data.get("mttr_display", "Insufficient data")

            st.markdown(
                f"""
                <div class="vetra-panel" style="padding: 1rem;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: #F8FAFC; margin-bottom: 0.75rem;">
                        Operational Alert Response Times
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem;">
                        <div style="background: #1B2638; border: 1px solid #273449; border-radius: 8px; padding: 0.75rem; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; font-weight: 600;">MTTA (Acknowledge)</div>
                            <div style="font-size: 1.15rem; font-weight: 800; color: #38BDF8; margin-top: 0.2rem;">{mtta_str}</div>
                        </div>
                        <div style="background: #1B2638; border: 1px solid #273449; border-radius: 8px; padding: 0.75rem; text-align: center;">
                            <div style="font-size: 0.7rem; color: #94A3B8; font-weight: 600;">MTTR (Resolution)</div>
                            <div style="font-size: 1.15rem; font-weight: 800; color: #22C55E; margin-top: 0.2rem;">{mttr_str}</div>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #CBD5E1; line-height: 1.6;">
                        • Total Logged ({selected_days}d): <strong>{tot_a}</strong><br>
                        • Active Warnings: <strong style="color: #DC2626;">{act_a}</strong><br>
                        • Acknowledged / In Review: <strong style="color: #F59E0B;">{ack_a}</strong><br>
                        • Resolved Turnaround: <strong style="color: #22C55E;">{res_a}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🚨 Open Full Alert Center →", key="btn_goto_alerts", use_container_width=True):
                _navigate_to("🚨 Alerts")

        with a_right:
            st.markdown(
                "<div style='font-weight: 700; font-size: 0.9rem; color: #F8FAFC; margin-bottom: 0.5rem;'>Active Health Triage Queue</div>",
                unsafe_allow_html=True
            )
            raw_active_alerts = api_client.get_active_alerts()

            if not raw_active_alerts:
                st.success("🟢 No active alerts. All physiological readings and preventive milestones are within normal bounds.")
            else:
                for idx, al in enumerate(raw_active_alerts[:5]):
                    alid = al.get("id") or str(al.get("_id", f"alert_{idx}"))
                    sev = al.get("severity", "medium").lower()
                    title = al.get("title", "Alert")
                    msg = al.get("message", "")
                    created = str(al.get("created_at", ""))[:19].replace("T", " ")

                    st.markdown(
                        f"""
                        <div class="alert-card alert-card-{sev}" style="padding: 0.65rem 0.85rem; margin-bottom: 0.4rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span class="badge badge-{sev}">{sev.upper()}</span>
                                <span style="font-size: 0.75rem; color: #94A3B8;">🕒 {created}</span>
                            </div>
                            <div style="font-weight: 700; font-size: 0.88rem; color: #F8FAFC; margin-top: 0.25rem;">{title}</div>
                            <div style="font-size: 0.8rem; color: #CBD5E1;">{msg}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    b1, b2, b3 = st.columns([1, 1, 1.4])
                    with b1:
                        if st.button("👁️ Ack", key=f"dash_a_ack_{alid}_{idx}", use_container_width=True):
                            api_client.acknowledge_alert(alid)
                            st.rerun()
                    with b2:
                        if st.button("✅ Resolve", key=f"dash_a_res_{alid}_{idx}", use_container_width=True):
                            api_client.resolve_alert(alid)
                            st.rerun()
                    with b3:
                        if st.button("🩺 Case Escalation", key=f"dash_a_case_{alid}_{idx}", use_container_width=True):
                            is_prev = str(al.get("alert_type", "")).startswith("preventive")
                            case_payload = {
                                "animal_id": al.get("animal_id"),
                                "title": f"Alert Escalation: {title}",
                                "description": msg,
                                "case_type": "preventive_follow_up" if is_prev else "health_alert",
                                "priority": sev,
                                "source": "alert",
                                "alert_id": alid,
                            }
                            suc, res = api_client.create_veterinary_case(case_payload)
                            if suc:
                                st.success("Veterinary case created.")
                                _navigate_to("🩺 Clinical Cases")
                            else:
                                st.error(str(res))

    # ------------------------------------------------------------
    # TAB 2: PRIORITY ATTENTION WATCHLIST
    # ------------------------------------------------------------
    with tab_watch:
        crit_watch = watchlist_data.get("critical_attention", [])
        high_watch = watchlist_data.get("high_risk", [])
        mon_watch = watchlist_data.get("monitoring", [])
        prev_watch = watchlist_data.get("preventive_due", [])

        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #F8FAFC; margin-bottom: 0.3rem;">
                🎯 Operational Priority Attention Watchlist
            </div>
            <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.75rem;">
                Cross-system triage combining physiological risk, active alerts, disease screening, and due preventive care.
            </div>
            """,
            unsafe_allow_html=True
        )

        watch_records = []
        for a in crit_watch:
            watch_records.append({**a, "Priority": "CRITICAL", "Color": "#DC2626"})
        for a in high_watch:
            watch_records.append({**a, "Priority": "HIGH RISK", "Color": "#F97316"})
        for a in mon_watch:
            watch_records.append({**a, "Priority": "MONITORING", "Color": "#F59E0B"})
        for a in prev_watch:
            watch_records.append({**a, "Priority": "PREVENTIVE DUE", "Color": "#38BDF8"})

        if not watch_records:
            st.success("🟢 No livestock currently require urgent priority attention. All animal records are stable.")
        else:
            for idx, item in enumerate(watch_records):
                aid = item.get("animal_id") or item.get("id") or item.get("_id") or f"unknown_{idx}"
                name = item.get("name", "Animal")
                tag = item.get("tag_id", "No Tag")
                species = item.get("species", "Cattle")
                pri = item.get("Priority", "MONITORING")
                col_hex = item.get("Color", "#F59E0B")
                reason = item.get("reason") or item.get("preventive_status") or item.get("top_alert") or "Physiological variance detected"

                w1, w2, w3 = st.columns([3.5, 1.2, 1.2])
                with w1:
                    st.markdown(
                        f"""
                        <div style="background: #151F2E; border: 1px solid #273449; border-left: 4px solid {col_hex}; border-radius: 6px; padding: 0.75rem 0.95rem; margin-bottom: 0.4rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong style="font-size: 0.95rem; color: #F8FAFC;">{name} ({tag})</strong>
                                <span style="font-size: 0.75rem; font-weight: 700; color: {col_hex}; background: {col_hex}18; border: 1px solid {col_hex}40; padding: 0.15rem 0.5rem; border-radius: 4px;">
                                    {pri}
                                </span>
                            </div>
                            <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 0.2rem;">
                                Species: <strong>{species.capitalize()}</strong> &nbsp;•&nbsp; Reason: {reason}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with w2:
                    pri_slug = pri.replace(" ", "_").lower()
                    if st.button("📋 Profile", key=f"watch_prof_{aid}_{pri_slug}_{idx}", use_container_width=True):
                        _navigate_to("🐄 Animals", animal_id=aid)
                with w3:
                    if st.button("🤖 AI Risk", key=f"watch_ai_{aid}_{pri_slug}_{idx}", use_container_width=True):
                        st.session_state["dash_spotlight_animal_id"] = aid
                        st.rerun()

    # ------------------------------------------------------------
    # TAB 3: AI HEALTH INTELLIGENCE PANEL
    # ------------------------------------------------------------
    with tab_ai:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #F8FAFC; margin-bottom: 0.3rem;">
                🤖 VETRA AI Clinical Risk Intelligence & Early Warning
            </div>
            <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.75rem;">
                Multi-layer physiological risk modeling, early-warning detection, and clinical decision support.
            </div>
            """,
            unsafe_allow_html=True
        )

        if not animals_list:
            st.info("No animals registered in system.")
        else:
            # Default to first at-risk or first animal
            ai_anim_options = {a["id"]: f"{a.get('name', 'Animal')} ({a.get('tag_id')}) - {a.get('species')}" for a in animals_list}
            default_aid = st.session_state.get("dash_spotlight_animal_id")
            if not default_aid or default_aid not in ai_anim_options:
                default_aid = animals_list[0]["id"]

            sel_ai_animal = st.selectbox(
                "Select Animal for AI Clinical Assessment",
                options=list(ai_anim_options.keys()),
                format_func=lambda aid: ai_anim_options[aid],
                index=list(ai_anim_options.keys()).index(default_aid),
                key="dash_ai_animal_select"
            )

            with st.spinner("Executing VETRA AI clinical intelligence pipeline..."):
                ai_report = api_client.get_ai_assessment(sel_ai_animal)

            if not ai_report:
                st.warning("AI health assessment temporarily unavailable for this animal.")
            else:
                ai_c1, ai_c2, ai_c3, ai_c4 = st.columns(4)

                r_score = ai_report.get("risk_score", 0.0)
                r_cat = str(ai_report.get("risk_category", "low")).upper()
                d_level = str(ai_report.get("disease_risk_level", "low")).upper()
                ew_status = str(ai_report.get("early_warning_status", "NORMAL")).upper()
                v_stab = ai_report.get("vital_stability_score", 100.0)

                cat_color = "#dc2626" if r_cat in ["CRITICAL", "HIGH"] else ("#ea580c" if r_cat == "MEDIUM" else "#059669")
                dis_color = "#dc2626" if d_level in ["CRITICAL", "HIGH"] else ("#ea580c" if d_level == "MODERATE" else "#059669")

                with ai_c1:
                    st.metric("Health Risk Score", f"{r_score:.1f} / 100", delta=r_cat, delta_color="inverse")
                with ai_c2:
                    st.metric("Disease Risk Level", d_level)
                with ai_c3:
                    st.metric("Early Warning Status", ew_status)
                with ai_c4:
                    st.metric("Vital Stability", f"{v_stab:.1f}%")

                st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)

                ai_left, ai_right = st.columns(2)

                with ai_left:
                    st.markdown("##### 🔬 Physiological Features & Contributing Factors")
                    contribs = ai_report.get("contributing_factors", [])
                    if contribs:
                        for c in contribs:
                            st.markdown(f"• <span style='color: #ea580c; font-weight: 600;'>{c}</span>", unsafe_allow_html=True)
                    else:
                        st.success("All vital signs align with physiological baselines.")

                    st.markdown("##### ⚠️ Early-Warning Signals")
                    ew_signals = ai_report.get("early_warning_signals", [])
                    if ew_signals:
                        for s in ew_signals:
                            st.markdown(f"• {s}")
                    else:
                        st.write("No pre-clinical anomaly patterns detected in current lookback window.")

                with ai_right:
                    st.markdown("##### 🩺 Clinical Interpretation & Actions")
                    interp = ai_report.get("clinical_interpretation") or ai_report.get("ai_explanation") or "Vital signs remain within normal physiological safe zones."
                    st.info(f"**Assessment:** {interp}")

                    rec_act = ai_report.get("recommended_action") or "Maintain standard preventive management and scheduled monitoring."
                    st.success(f"**Recommended Action:** {rec_act}")

                    engine_source = ai_report.get("analysis_engine", "VETRA-AI-Core")
                    st.caption(f"Analysis Engine: **{engine_source}** (Deterministic fallback fully active if cloud quota exhausted)")

    # ------------------------------------------------------------
    # TAB 4: PREVENTIVE CARE
    # ------------------------------------------------------------
    with tab_prev:
        p_comp = prevention_data.get("compliance_rate", 100.0)
        p_completed = prevention_data.get("completed_count", 0)
        p_today = prevention_data.get("due_today_count", 0)
        p_soon = prevention_data.get("due_soon_count", 0)
        p_overdue = prevention_data.get("overdue_count", 0)
        due_actions = prevention_data.get("due_actions", [])

        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        with pc1:
            st.metric("Compliance Rate", f"{p_comp:.1f}%")
        with pc2:
            st.metric("Completed", p_completed)
        with pc3:
            st.metric("Due Today", p_today)
        with pc4:
            st.metric("Due Soon (30d)", p_soon)
        with pc5:
            st.metric("Overdue", p_overdue, delta=f"-{p_overdue}" if p_overdue > 0 else "0", delta_color="inverse")

        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
        st.markdown("##### 💉 Imminent Preventive Healthcare Milestones")

        if not due_actions:
            st.success("All preventive vaccination, deworming, and health examination milestones are up to date.")
        else:
            for act in due_actions[:6]:
                status_tag = act.get("status", "UPCOMING")
                color = "#dc2626" if status_tag == "OVERDUE" else ("#ea580c" if status_tag == "DUE TODAY" else "#2563eb")

                st.markdown(
                    f"""
                    <div style="background: #151F2E; border: 1px solid #273449; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 0.35rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.75rem; font-weight: 700; color: {color}; border: 1px solid {color}40; background: {color}15; border-radius: 4px; padding: 0.1rem 0.4rem; margin-right: 0.5rem;">
                                {status_tag}
                            </span>
                            <strong style="font-size: 0.85rem; color: #F8FAFC;">{act.get('title')}</strong>
                            <span style="font-size: 0.8rem; color: #94A3B8;">({act.get('type')})</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #CBD5E1;">
                            Due: <strong style="color: #F8FAFC;">{act.get('due_date', '-')}</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        if st.button("💉 Go to Preventive Health Management →", key="btn_goto_prevention"):
            _navigate_to("💉 Preventive Health")

    # ------------------------------------------------------------
    # TAB 5: VETERINARY CLINICAL OPERATIONS
    # ------------------------------------------------------------
    with tab_vet:
        v_total = veterinary_data.get("total_cases", 0)
        v_open = veterinary_data.get("open_cases", 0)
        v_resolved = veterinary_data.get("resolved_cases", 0)
        v_avg_turnaround = veterinary_data.get("avg_resolution_display", "Insufficient data")
        status_counts = veterinary_data.get("status_distribution", {})
        priority_counts = veterinary_data.get("priority_distribution", {})

        vc1, vc2, vc3, vc4 = st.columns(4)
        with vc1:
            st.metric("Total Cases Logged", v_total)
        with vc2:
            st.metric("Active Caseload", v_open)
        with vc3:
            st.metric("Resolved Cases", v_resolved)
        with vc4:
            st.metric("Avg Case Turnaround", v_avg_turnaround)

        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
        st.markdown("##### 🩺 Clinical Caseload Distribution")
        stat_col, pri_col = st.columns(2)

        with stat_col:
            st.markdown("<strong>By Lifecycle Stage:</strong>", unsafe_allow_html=True)
            for st_name, count in status_counts.items():
                st.write(f"• **{st_name.capitalize().replace('_', ' ')}**: {count}")

        with pri_col:
            st.markdown("<strong>By Clinical Priority:</strong>", unsafe_allow_html=True)
            for pr_name, count in priority_counts.items():
                color = "#dc2626" if pr_name == "critical" else ("#ea580c" if pr_name == "high" else "#059669")
                st.markdown(f"• <span style='color: {color}; font-weight: 700;'>{pr_name.upper()}</span>: {count}", unsafe_allow_html=True)

        if st.button("🩺 Go to Clinical Case Management →", key="btn_goto_vet"):
            _navigate_to("🩺 Clinical Cases")

    # ------------------------------------------------------------
    # TAB 6: IOT FLEET & HARDWARE HEALTH
    # ------------------------------------------------------------
    with tab_dev:
        d_tot = devices_data.get("total_devices", 0)
        d_on = devices_data.get("online_devices", 0)
        d_bat = devices_data.get("avg_battery", 0.0)
        d_low_bat = devices_data.get("low_battery_count", 0)
        d_freshness = devices_data.get("freshness_display", "No telemetry stream")

        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.metric("Nodes Online", f"{d_on} / {d_tot}")
        with dc2:
            st.metric("Avg Battery", f"{d_bat:.1f}%")
        with dc3:
            st.metric("Low Battery (<20%)", d_low_bat, delta=f"-{d_low_bat}" if d_low_bat > 0 else "0", delta_color="inverse")
        with dc4:
            st.metric("Telemetry Freshness", d_freshness)

        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
        st.markdown("##### 📡 Monitored Sensor Nodes")
        dev_list = devices_data.get("devices", [])
        if not dev_list:
            st.info("No sensor devices registered.")
        else:
            dev_df = pd.DataFrame([
                {
                    "Device ID": d.get("device_id"),
                    "Type": d.get("device_type", "vital_tracker"),
                    "Paired Animal": d.get("animal_tag", "Unpaired"),
                    "Status": d.get("status", "offline").upper(),
                    "Battery": f"{d.get('battery_level', 0):.1f}%",
                    "Last Heartbeat": str(d.get("last_heartbeat", ""))[:19].replace("T", " ")
                }
                for d in dev_list
            ])
            st.dataframe(dev_df, use_container_width=True, hide_index=True)

        if st.button("📡 Go to Live Monitoring & IoT →", key="btn_goto_dev"):
            _navigate_to("📡 Live Monitoring")

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 9.5 DISEASE SURVEILLANCE & REGIONAL SIGNALS
    # ============================================================
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.35rem;">
            🦠 Herd Disease Surveillance & Regional Signals
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.75rem;">
            Population-level epidemiological anomaly detection, statistical clusters, and spatial risk monitoring
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        surv_data = api_client.get_surveillance_overview(window_days=7)
    except Exception:
        surv_data = {}

    if surv_data:
        s_high_risk = surv_data.get("high_risk_farms_count", 0)
        s_clusters = surv_data.get("potential_clusters_count", 0)
        s_events = surv_data.get("active_events_count", 0)
        s_hotspots = surv_data.get("geographic_hotspots_count", 0)

        if s_high_risk > 0 or s_clusters > 0 or s_events > 0:
            st.markdown(
                f"""
                <div class="vetra-panel" style="border-left: 4px solid #ea580c; background: rgba(234, 88, 12, 0.12); border: 1px solid rgba(234, 88, 12, 0.35); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <div style="font-weight: 700; color: #FDBA74; font-size: 0.95rem;">
                                ⚠️ Elevated Surveillance Risk Detected
                            </div>
                            <div style="font-size: 0.85rem; color: #FED7AA; margin-top: 0.2rem;">
                                {surv_data.get('advisory', 'Potential disease signals flagged. Veterinary investigation recommended.')}
                            </div>
                        </div>
                        <div style="display: flex; gap: 1rem; font-size: 0.85rem; font-weight: 700; color: #FDBA74; margin-top: 0.4rem;">
                            <span>High-Risk Farms: {s_high_risk}</span>
                            <span>Potential Clusters: {s_clusters}</span>
                            <span>Active Events: {s_events}</span>
                            <span>Hotspots: {s_hotspots}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="vetra-panel" style="border-left: 4px solid #22c55e; background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); padding: 0.85rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.9rem; color: #4ADE80; font-weight: 600;">
                            ✅ No significant surveillance escalation detected across monitored holdings.
                        </span>
                        <span style="font-size: 0.78rem; background: rgba(34, 197, 94, 0.2); color: #86EFAC; border: 1px solid rgba(34, 197, 94, 0.4); padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700;">
                            ROUTINE MONITORING
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        sc_col1, sc_col2 = st.columns([3, 1])
        with sc_col1:
            st.caption(f"🛡️ *{surv_data.get('clinical_safety_notice', 'VETRA tracks statistical anomalies. Outbreak declaration requires licensed veterinary confirmation.')}*")
        with sc_col2:
            if st.button("🦠 Open Surveillance Dashboard →", key="btn_goto_surv", use_container_width=True):
                _navigate_to("🦠 Disease Surveillance")
    else:
        st.info("Surveillance data temporarily unavailable.")

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


    # ============================================================
    # 9.75. VISUAL HEALTH INTELLIGENCE (PHASE 9 INTEGRATION)
    # ============================================================
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.35rem;">
            👁️ Visual Health Intelligence
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.75rem;">
            AI-assisted visual screening summary, high visual-risk livestock, and multimodal health signals
        </div>
        """,
        unsafe_allow_html=True
    )

    vh_summary = api_client.get_visual_health_summary()
    tot_analyses = vh_summary.get("total_analyses", 0)
    assessed_animals = vh_summary.get("animals_assessed", 0)
    high_risk_vis = vh_summary.get("high_risk_analyses", 0)
    pending_vis_rev = vh_summary.get("pending_reviews", 0)
    mm_count = vh_summary.get("multimodal_assessments_count", 0)

    vh_col1, vh_col2, vh_col3, vh_col4 = st.columns(4)
    with vh_col1:
        st.metric("Assessed Animals", assessed_animals, help="Distinct animals evaluated via computer vision")
    with vh_col2:
        st.metric("Elevated Visual Risk", high_risk_vis, delta="Concern" if high_risk_vis > 0 else None, delta_color="inverse")
    with vh_col3:
        st.metric("Pending Vet Reviews", pending_vis_rev, help="Visual analyses awaiting clinical examination")
    with vh_col4:
        st.metric("Multimodal Fusions", mm_count, help="Assessments combining visual and physiological vitals")

    if high_risk_vis > 0:
        st.warning(f"⚠️ **Visual Health Escalation:** {high_risk_vis} visual assessment(s) indicate elevated risk. Review recommended.")
    elif assessed_animals > 0:
        st.success(f"✅ {assessed_animals} animal(s) recently assessed. No significant visual health escalation detected.")
    else:
        st.info("No significant visual health escalation detected. Screening queue clear.")

    v_btn_col1, v_btn_col2 = st.columns([3, 1])
    with v_btn_col1:
        st.caption("🛡️ *Decision Support Only: Visual observations are AI-assisted indicators and are not a confirmed veterinary diagnosis.*")
    with v_btn_col2:
        if st.button("👁️ Open Visual Health →", key="btn_goto_vis_health", use_container_width=True):
            _navigate_to("👁️ Visual Health")

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


    # ============================================================
    # 10. ANIMAL SPOTLIGHT (OPERATIONAL DRILL-DOWN)
    # ============================================================
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.35rem;">
            🔍 Animal Operational Spotlight
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.75rem;">
            Instant operational drill-down for individual animal telemetry, risk classification, and profile actions
        </div>
        """,
        unsafe_allow_html=True
    )

    if animals_list:
        spot_choices = {a["id"]: f"{a.get('name', 'Animal')} ({a.get('tag_id')}) - {a.get('species')} [{a.get('health_status', 'healthy').upper()}]" for a in animals_list}
        spot_aid = st.session_state.get("dash_spotlight_animal_id")
        if not spot_aid or spot_aid not in spot_choices:
            spot_aid = animals_list[0]["id"]

        sel_spot_animal = st.selectbox(
            "Select Spotlight Animal",
            options=list(spot_choices.keys()),
            format_func=lambda aid: spot_choices[aid],
            index=list(spot_choices.keys()).index(spot_aid),
            key="dash_spotlight_animal_select"
        )
        st.session_state["dash_spotlight_animal_id"] = sel_spot_animal

        target_animal = next((a for a in animals_list if a["id"] == sel_spot_animal), animals_list[0])

        sp_left, sp_right = st.columns([1.5, 2.5])
        with sp_left:
            h_stat = str(target_animal.get("health_status", "healthy")).lower()
            st.markdown(
                f"""
                <div class="vetra-panel" style="padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #F8FAFC;">{target_animal.get('name', 'Animal')}</h4>
                        <span class="badge badge-{h_stat}">{h_stat.upper()}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 0.5rem; line-height: 1.6;">
                        • <strong>Tag ID:</strong> <code>{target_animal.get('tag_id', 'N/A')}</code><br>
                        • <strong>Species:</strong> {target_animal.get('species', 'Cattle').capitalize()}<br>
                        • <strong>Breed:</strong> {target_animal.get('breed', 'Indigenous')}<br>
                        • <strong>Gender:</strong> {target_animal.get('gender', 'Female').capitalize()}<br>
                        • <strong>Weight:</strong> {target_animal.get('weight_kg', 0):.1f} kg
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("📋 Open Full Animal Profile", key="btn_open_full_profile", use_container_width=True, type="primary"):
                _navigate_to("🐄 Animals", animal_id=sel_spot_animal)

        with sp_right:
            # Latest reading for this animal
            anim_readings = api_client.get_health_readings(animal_id=sel_spot_animal, limit=1)
            if anim_readings:
                latest_r = anim_readings[0]
                vm1, vm2, vm3, vm4, vm5 = st.columns(5)
                vm1.metric("🌡️ Temp", f"{latest_r.get('temperature_c', 0):.2f} °C")
                vm2.metric("💓 HR", f"{latest_r.get('heart_rate_bpm', 0):.1f} BPM")
                vm3.metric("🫁 Resp", f"{latest_r.get('respiratory_rate', 0):.1f} /m")
                vm4.metric("🏃 Act", f"{latest_r.get('activity_level', 0):.1f}%")
                vm5.metric("🌿 Rum", f"{latest_r.get('rumination_level', 0):.1f}%")
                st.caption(f"Last vital telemetry logged: {str(latest_r.get('recorded_at') or '')[:19].replace('T', ' ')}")
            else:
                st.info("No recorded readings for this animal yet.")

    # ============================================================
    # 11. EDGE & CAMERA INTELLIGENCE (Phase 10)
    # ============================================================
    st.divider()
    st.markdown("### 📹 Edge & Camera Intelligence")

    cam_sum = api_client.get_camera_summary()
    edge_sum = api_client.get_edge_device_summary()
    recent_cam_events = api_client.get_recent_edge_events(limit=8)
    cam_list = api_client.get_cameras()

    tot_c = cam_sum.get("total_cameras", len(cam_list))
    on_c = cam_sum.get("online_cameras", sum(1 for c in cam_list if c.get("status") == "online"))
    deg_c = cam_sum.get("degraded_cameras", sum(1 for c in cam_list if c.get("status") == "degraded"))
    off_c = cam_sum.get("offline_cameras", sum(1 for c in cam_list if c.get("status") == "offline"))
    tot_e = edge_sum.get("total_devices", 0)
    on_e = edge_sum.get("online_devices", 0)
    coverage_pct = f"{round((on_c / tot_c * 100.0) if tot_c > 0 else 0.0)}%"

    ci1, ci2, ci3, ci4, ci5, ci6, ci7 = st.columns(7)
    ci1.metric("📹 Total Cameras", tot_c)
    ci2.metric("🟢 Online", on_c)
    ci3.metric("🟡 Degraded", deg_c)
    ci4.metric("🔴 Offline", off_c)
    ci5.metric("⚡ Edge Nodes", tot_e)
    ci6.metric("✅ Healthy Nodes", on_e)
    ci7.metric("📡 Coverage", coverage_pct)

    c_left, c_right = st.columns([1.5, 1.5])

    with c_left:
        st.markdown("##### 🩺 Camera Fleet Health Overview")
        if not cam_list:
            st.info("No camera streams registered in inventory. Click below to add cameras.")
        else:
            cam_data = []
            for c in cam_list[:5]:
                cam_data.append({
                    "Camera ID": c.get("camera_id"),
                    "Name": c.get("camera_name"),
                    "Pen / Shed": c.get("pen_id") or "General",
                    "Type": c.get("camera_type"),
                    "Status": c.get("status", "unknown").upper(),
                    "Last Seen": str(c.get("last_seen") or "Never")[:19]
                })
            st.dataframe(pd.DataFrame(cam_data), use_container_width=True, hide_index=True)

        if st.button("📹 Open Full Live Camera & Edge Console", key="btn_open_camera_console", use_container_width=True, type="secondary"):
            _navigate_to("📹 Live Cameras")

    with c_right:
        st.markdown("##### 🧠 Recent Edge Visual Inference Events")
        if not recent_cam_events:
            st.info("No visual inference events logged yet.")
        else:
            event_records = []
            for ev in recent_cam_events[:5]:
                event_records.append({
                    "Event ID": ev.get("event_id"),
                    "Camera": ev.get("camera_name") or ev.get("camera_id"),
                    "Risk Score": f"{ev.get('visual_risk_score', 0.0):.2f}",
                    "Confidence": f"{ev.get('confidence', 0.85)*100:.0f}%",
                    "Captured": str(ev.get("captured_at") or "")[:19]
                })
            st.dataframe(pd.DataFrame(event_records), use_container_width=True, hide_index=True)

    # ============================================================
    # 12. PREDICTIVE HEALTH INTELLIGENCE & FORECASTS (Phase 11)
    # ============================================================
    st.divider()
    st.markdown("### 🧠 Predictive Health Intelligence & Livestock Forecasting")

    pred_summary = api_client.get_predictive_summary()
    pred_watchlist = api_client.get_predictive_watchlist(limit=10)
    pred_trends = api_client.get_predictive_trends(timeframe="7d")

    tot_eval = pred_summary.get("animals_under_prediction", 0)
    p_high = pred_summary.get("high_risk_count", 0)
    p_crit = pred_summary.get("critical_risk_count", 0)
    p_cov = f"{pred_summary.get('prediction_coverage_pct', 0.0):.1f}%"
    p_det = sum(1 for w in pred_watchlist if w.get("trend") in ("deteriorating", "rapid_deterioration"))
    # Average forecast confidence from watchlist
    p_conf_avg = f"{int(sum(float(w.get('confidence', 0.5)) for w in pred_watchlist) / max(1, len(pred_watchlist)) * 100)}%" if pred_watchlist else "80%"

    p_col1, p_col2, p_col3, p_col4, p_col5, p_col6 = st.columns(6)
    p_col1.metric("🐄 Animals Under Prediction", tot_eval)
    p_col2.metric("⚠️ High Predicted Risk", p_high, delta="Review" if p_high > 0 else "0", delta_color="inverse")
    p_col3.metric("🚨 Critical Predicted Risk", p_crit, delta="Immediate" if p_crit > 0 else "0", delta_color="inverse")
    p_col4.metric("📉 Deteriorating Animals", p_det, help="Animals with accelerating negative trajectory")
    p_col5.metric("📡 Prediction Coverage", p_cov)
    p_col6.metric("🎯 Avg Forecast Confidence", p_conf_avg)

    p_left, p_right = st.columns([1.6, 1.4])

    with p_left:
        st.markdown("##### 📈 Health Forecast Trajectory Trend")
        p_pts = pred_trends.get("points", [])
        if p_pts:
            fig_p_trend = go.Figure()
            fig_p_trend.add_trace(go.Scatter(
                x=[p.get("timestamp", "")[:16].replace("T", " ") for p in p_pts],
                y=[p.get("average_predicted_risk", 0.0) for p in p_pts],
                mode="lines+markers",
                name="Average Predicted Risk",
                line=dict(color="#3b82f6", width=2.5),
                marker=dict(size=6, color="#1d4ed8")
            ))
            fig_p_trend.add_hline(y=70, line_dash="dash", line_color="#ef4444", annotation_text="Critical (70)")
            fig_p_trend.add_hline(y=45, line_dash="dash", line_color="#f59e0b", annotation_text="High Risk (45)")
            fig_p_trend.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=20, b=10),
                height=220,
                yaxis=dict(range=[0, 100], title="Risk (0-100)", gridcolor="#273449", tickfont=dict(color="#94A3B8")),
                xaxis=dict(gridcolor="#273449", tickfont=dict(color="#94A3B8")),
                plot_bgcolor="#151F2E",
                paper_bgcolor="#151F2E",
                font=dict(color="#CBD5E1")
            )
            st.plotly_chart(fig_p_trend, use_container_width=True)
        else:
            st.info("Continuous telemetry required to populate longitudinal forecast trendline.")

        if st.button("🧠 Open Full Predictive Health Intelligence Console", key="btn_open_pred_ai_dash", use_container_width=True, type="primary"):
            _navigate_to("🧠 Predictive AI")

    with p_right:
        st.markdown("##### 🚨 Top Deterioration Watchlist")
        if not pred_watchlist:
            st.info("No animals currently meet clinical deterioration criteria.")
        else:
            w_dash_data = []
            for w in pred_watchlist[:4]:
                w_dash_data.append({
                    "Urgency": w.get("operational_urgency"),
                    "Tag ID": w.get("animal_tag"),
                    "Current": f"{w.get('current_health_risk', 0.0):.1f}",
                    "Predicted": f"{w.get('predicted_health_risk', 0.0):.1f}",
                    "Trajectory": w.get("trend", "stable").upper().replace("_", " "),
                    "Primary Driver": w.get("primary_driver", "Stable")[:35]
                })
            st.dataframe(pd.DataFrame(w_dash_data), use_container_width=True, hide_index=True)

    # Top Risk Drivers & Forecast Timeline
    d_col1, d_col2 = st.columns([1, 1])
    with d_col1:
        st.markdown("##### 🔬 Top Predictive Risk Drivers")
        drivers_list = [w.get("primary_driver") for w in pred_watchlist if w.get("primary_driver")]
        if drivers_list:
            for idx, drv in enumerate(drivers_list[:3], 1):
                st.markdown(f"**{idx}.** {drv}")
        else:
            st.markdown("""
            • **Thermal Elevation Trajectory**: Core body temperature rate of change over baseline.<br>
            • **Rumination & Activity Depression**: Digestive cessation and lethargic movement decline.<br>
            • **Tachypneic Divergence**: Accelerated respiratory slope under physical strain.
            """, unsafe_allow_html=True)

    with d_col2:
        st.markdown("##### ⏱️ Prospective Forecast Timeline")
        st.markdown("""
        • 🟢 **24h Window**: Early metabolic & autonomic vitals divergence triage.<br>
        • 🟡 **48h Window**: Multimodal physiological & visual symptom convergence horizon.<br>
        • 🔴 **72h Window**: Veterinary clinical action window for prophylactic intervention.
        """, unsafe_allow_html=True)

    # ============================================================
    # 13. VETERINARY & INSTITUTIONAL INTELLIGENCE (PHASE 12)
    # ============================================================
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">
                    🏛️ Veterinary & Institutional Intelligence
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8;">
                    Cross-farm telemedicine triage, follow-up scheduling, and disease surveillance reporting integration
                </div>
            </div>
            <div>
                <span style="background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #273449; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 9999px;">
                    🛡️ ADAPTER: READY (NOT_CONFIGURED)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    vet_cases = api_client.get_cases() or []
    tele_consultations = api_client.get_telemedicine_consultations() or []
    inst_reports = api_client.get_institutional_reports() or []

    open_vet_cases = sum(1 for c in vet_cases if c.get("status") not in ["resolved", "closed"])
    active_consultations = sum(1 for c in tele_consultations if c.get("status") == "in_progress")
    follow_ups_due = sum(1 for c in tele_consultations if c.get("follow_up_required") or c.get("status") == "follow_up_required")
    reports_under_review = sum(1 for r in inst_reports if r.get("status") == "under_review")
    reports_submitted = sum(1 for r in inst_reports if r.get("status") in ["submitted", "acknowledged"])
    surveillance_reviews = sum(1 for r in inst_reports if r.get("report_type") in ["surveillance_summary", "outbreak_candidate_review"])
    integration_status_label = "READY"

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    with k1:
        st.metric("Open Cases", open_vet_cases)
    with k2:
        st.metric("Active Consults", active_consultations)
    with k3:
        st.metric("Follow-Ups Due", follow_ups_due)
    with k4:
        st.metric("Under Review", reports_under_review)
    with k5:
        st.metric("Reports Submitted", reports_submitted)
    with k6:
        st.metric("Surv. Reviews", surveillance_reviews)
    with k7:
        st.metric("Gov. Adapter", integration_status_label, help="Government integration adapter is ready in NOT_CONFIGURED state.")

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🩺 Open Telemedicine Console", key="dash_btn_telemed", use_container_width=True):
            _navigate_to("🩺 Telemedicine")
    with c_btn2:
        if st.button("🏛️ Open Institutional Health & Surveillance", key="dash_btn_inst", use_container_width=True):
            _navigate_to("🏛️ Institutional Health")

    # ============================================================
    # 14. ADVANCED INSTITUTIONAL SURVEILLANCE (PHASE 13)
    # ============================================================
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">
                    🛡️ Advanced Institutional Surveillance
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8;">
                    Cross-farm early warning, explainable syndromic clusters, and government-ready data packaging
                </div>
            </div>
            <div>
                <span style="background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #273449; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 9999px;">
                    GATE: SECURE LOCAL (NOT_CONFIGURED)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    epi_events = api_client.list_epidemiological_events() or []
    early_warnings = api_client.list_institutional_warnings() or []
    cross_signals = api_client.get_cross_farm_signals() or []
    geo_clusters = api_client.get_institutional_clusters() or []
    gov_packages = api_client.list_government_packages() or []
    adapter_status = api_client.get_government_adapter_status() or {}

    open_events = sum(1 for e in epi_events if e.get("status") in ["OPEN", "SIGNAL", "SUSPECT"])
    active_warnings = sum(1 for w in early_warnings if w.get("status") == "OPEN")
    total_signals = len(cross_signals)
    total_clusters = len(geo_clusters)
    events_under_review = sum(1 for e in epi_events if e.get("review_state") in ["UNDER_REVIEW", "REVIEW_REQUIRED"] or e.get("status") == "UNDER_REVIEW")
    approved_packages = sum(1 for p in gov_packages if p.get("approval_status") == "APPROVED")
    readiness_label = adapter_status.get("government_adapter_status", "NOT_CONFIGURED")

    kp1, kp2, kp3, kp4, kp5, kp6, kp7 = st.columns(7)
    with kp1:
        st.metric("Open Events", open_events)
    with kp2:
        st.metric("Early Warnings", active_warnings)
    with kp3:
        st.metric("Cross-Farm Signals", total_signals)
    with kp4:
        st.metric("Geo Clusters", total_clusters)
    with kp5:
        st.metric("Under Review", events_under_review)
    with kp6:
        st.metric("Approved Packages", approved_packages)
    with kp7:
        st.metric("Readiness", readiness_label, help="Safety gate status: External adapters are NOT_CONFIGURED by default.")

    # Navigation Shortcuts
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        if st.button("🏛️ Institutional Health", key="dash_sc_inst", use_container_width=True):
            _navigate_to("🏛️ Institutional Health")
    with sc2:
        if st.button("🦠 Disease Surveillance", key="dash_sc_surv", use_container_width=True):
            _navigate_to("🦠 Disease Surveillance")
    with sc3:
        if st.button("🩺 Veterinary Network", key="dash_sc_vet", use_container_width=True):
            _navigate_to("🩺 Clinical Cases")
    with sc4:
        if st.button("📦 Government Data Packages", key="dash_sc_pkg", use_container_width=True):
            _navigate_to("🏛️ Institutional Health")

    # ============================================================
    # 15. SAFE AUTOMATIC REFRESH LOOP
    # ============================================================
    if auto_refresh:
        time.sleep(12)
        st.rerun()


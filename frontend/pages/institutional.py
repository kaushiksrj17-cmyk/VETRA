"""
frontend/pages/institutional.py
===============================
VETRA Phase 12 & Phase 13 — Government & Institutional Advanced Surveillance Integration.

Combines:
Phase 13: Advanced Epidemiological Surveillance (12 specialized sections)
- Epidemiological Event Monitor
- Cross-Farm Signals
- Geographic Clusters
- Early Warning Center
- Species Surveillance
- Temporal Trends
- Risk Heatmap
- Event Review Queue
- Institutional Evidence Matrix
- Government Data Package
- Integration Readiness
- Audit Trail

Phase 12: Institutional Health, Case Reporting & Telemedicine (12 legacy tabs)
"""

from datetime import datetime, timezone
import io
import json
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api_client
from session import get_user_info


def render_institutional_page():
    """Renders the comprehensive Institutional Health & Surveillance page."""
    user_info = get_user_info()
    user_role = str(user_info.get("role", "farmer")).lower()
    user_farm_id = user_info.get("farm_id")

    # ============================================================
    # HEADER & GOVERNMENT INTEGRATION DISCLAIMER
    # ============================================================
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 1rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.1rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
                    🏛️ Institutional Health & Surveillance
                </h1>
                <div style="color: #94A3B8; font-size: 0.95rem; font-weight: 500; margin-top: 0.2rem;">
                    Epidemiological Surveillance, Cross-Farm Early Warning & Government Data Packaging
                </div>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(148, 163, 184, 0.12); color: #CBD5E1; border: 1px solid #273449; font-size: 0.8rem; font-weight: 700; padding: 0.35rem 0.85rem; border-radius: 9999px;">
                    🛡️ ADAPTER: NOT_CONFIGURED (SAFE LOCAL)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(
        "ℹ️ **Government Integration Status Notice:** "
        "VETRA includes pre-built Institutional and Government Reporting Adapters. "
        "In this development environment, external government systems are **NOT CONFIGURED** and live submissions are disabled. "
        "No live government API connection is claimed until authorized endpoints are configured and verified."
    )

    # Master View Selection (Phase 13 Advanced Surveillance vs Phase 12 Clinical Reporting)
    surv_layer = st.radio(
        "Surveillance Architecture View",
        [
            "🛡️ Advanced Epidemiological Surveillance (Phase 13)",
            "📋 Institutional Reporting & Telemedicine (Phase 12)"
        ],
        horizontal=True
    )

    if surv_layer == "🛡️ Advanced Epidemiological Surveillance (Phase 13)":
        render_phase13_surveillance(user_info, user_role, user_farm_id)
    else:
        render_phase12_reporting(user_info, user_role, user_farm_id)


# =====================================================================
# PHASE 13: ADVANCED EPIDEMIOLOGICAL SURVEILLANCE
# =====================================================================
def render_phase13_surveillance(user_info: dict, user_role: str, user_farm_id: Optional[str]):
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12 = st.tabs([
        "🧬 1. Event Monitor",
        "📡 2. Cross-Farm Signals",
        "📍 3. Geo Clusters",
        "⚠️ 4. Early Warning Center",
        "🐑 5. Species Surveillance",
        "📈 6. Temporal Trends",
        "🔥 7. Risk Heatmap",
        "⚖️ 8. Event Review Queue",
        "🧩 9. Evidence Matrix",
        "📦 10. Government Package",
        "🔌 11. Integration Readiness",
        "📜 12. Audit Trail"
    ])

    # 1. Epidemiological Event Monitor
    with t1:
        st.subheader("1. Epidemiological Event Monitor")
        st.caption("Active syndromic health anomalies, mortality spikes, and disease signals.")
        events = api_client.list_epidemiological_events() or []
        if not events:
            st.info("INSUFFICIENT DATA: No active epidemiological events logged.")
        else:
            ev_data = []
            for ev in events:
                ev_data.append({
                    "Event ID": ev.get("event_id"),
                    "Type": ev.get("event_type"),
                    "Farm": ev.get("farm_id", "N/A"),
                    "Species": ev.get("species", "all"),
                    "Severity": str(ev.get("severity")).upper(),
                    "Risk Score": f"{ev.get('risk_score', 0.0):.1f}",
                    "Status": ev.get("status"),
                    "Review State": ev.get("review_state"),
                    "Confidence": f"{ev.get('confidence', 0.0):.2f}"
                })
            st.dataframe(pd.DataFrame(ev_data), use_container_width=True, hide_index=True)

    # 2. Cross-Farm Signals
    with t2:
        st.subheader("2. Cross-Farm Surveillance Signals")
        st.caption("Epidemiological proximity correlation between neighboring livestock holdings.")
        if user_role == "farmer":
            st.warning("Cross-farm surveillance signals are restricted to institutional officers and veterinarians.")
        else:
            signals = api_client.get_cross_farm_signals() or []
            if not signals:
                st.info("INSUFFICIENT DATA: Insufficient multi-holding proximity telemetry to detect cross-farm signals.")
            else:
                for sig in signals:
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #273449; background: #151F2E; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
                            <div style="display: flex; justify-content: space-between;">
                                <h4 style="margin: 0; color: #F8FAFC;">📡 Signal: {sig.get('signal_id')}</h4>
                                <span style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem;">
                                    PROXIMITY: {sig.get('distance_km', 0.0)} km
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 0.3rem;">
                                Source Farm: <code>{sig.get('source_farm_id')}</code> ➔ Target Farm: <code>{sig.get('target_farm_id')}</code>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #CBD5E1;">
                                <b>Risk Correlation:</b> {sig.get('risk_correlation', 0.0) * 100:.1f}% | <b>Recommendation:</b> {sig.get('recommendation')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # 3. Geographic Clusters
    with t3:
        st.subheader("3. Explainable Disease Clusters")
        st.caption("Multi-holding syndromic clustering using geospatial and vital convergence.")
        if user_role == "farmer":
            st.warning("Regional cluster analytics are restricted to institutional and veterinary users.")
        else:
            clusters = api_client.get_institutional_clusters() or []
            if not clusters:
                st.info("INSUFFICIENT DATA: No syndromic clusters detected in observation radius.")
            else:
                for cl in clusters:
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #273449; background: #151F2E; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
                            <div style="display: flex; justify-content: space-between;">
                                <h4 style="margin: 0; color: #F8FAFC;">📍 Cluster: {cl.get('cluster_id')} ({cl.get('cluster_type', 'syndromic')})</h4>
                                <span style="background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.35); font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem;">
                                    {cl.get('review_status', 'OPEN')}
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 0.3rem;">
                                Radius: <b>{cl.get('geographic_radius_km', 5.0)} km</b> | Holdings Involved: <b>{len(cl.get('affected_farms', []))}</b> | Confidence: <b>{cl.get('confidence', 0.0):.2f}</b>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #CBD5E1;">
                                <b>Evidence:</b> {cl.get('evidence_summary', 'Multi-holding proximity')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # 4. Early Warning Center
    with t4:
        st.subheader("4. Institutional Early Warning Center")
        st.caption("Early risk indicators requiring institutional or district review.")
        warnings = api_client.list_institutional_warnings() or []
        if not warnings:
            st.info("INSUFFICIENT DATA: No institutional early warnings currently open.")
        else:
            for w in warnings:
                st.markdown(
                    f"""
                    <div style="border: 1px solid #273449; background: #151F2E; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <h4 style="margin: 0; color: #F8FAFC;">⚠️ {w.get('title')} ({w.get('warning_id')})</h4>
                            <span style="background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.35); font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem;">
                                {str(w.get('severity')).upper()} | {w.get('status')}
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 0.3rem;">
                            Region: <b>{w.get('region')}</b> | Risk Index: <b>{w.get('risk_score', 0.0):.1f}</b> | Generated: <b>{w.get('generated_at', '')[:10]}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Warning Lifecycle Transition
            if user_role in ["institutional_officer", "admin", "veterinarian"]:
                st.markdown("##### 📝 Update Warning Lifecycle Status")
                w_opts = [w.get("warning_id") for w in warnings]
                sel_w_id = st.selectbox("Select Early Warning", options=w_opts, key="sb_warn_id")
                col_st1, col_st2 = st.columns(2)
                with col_st1:
                    new_w_status = st.selectbox("New Lifecycle State", ["UNDER_REVIEW", "ACKNOWLEDGED", "DISMISSED", "ESCALATED", "CLOSED"])
                with col_st2:
                    w_notes = st.text_input("Institutional Review Notes", "Routine review completed.", key="warn_notes_input")

                if st.button("Update Warning Status", key="btn_update_warn"):
                    ok, res = api_client.update_institutional_warning_status(sel_w_id, new_w_status, w_notes)
                    if ok:
                        st.success(f"Warning {sel_w_id} transitioned to {new_w_status}.")
                        st.rerun()
                    else:
                        st.error(f"Failed to update warning: {res}")

    # 5. Species Surveillance
    with t5:
        st.subheader("5. Species-Aggregated Surveillance")
        st.caption("Livestock population breakdown and risk tier by species.")
        sp_data = api_client.get_species_surveillance() or []
        if not sp_data:
            st.info("INSUFFICIENT DATA: No livestock registered for species aggregation.")
        else:
            st.dataframe(pd.DataFrame(sp_data), use_container_width=True, hide_index=True)

    # 6. Temporal Trends
    with t6:
        st.subheader("6. Temporal Surveillance Trends")
        st.caption("Temporal syndromic anomaly trajectories over the monitoring window.")
        trends = api_client.get_institutional_trends(window_days=14) or {}
        if not trends.get("trend_points"):
            st.info("INSUFFICIENT DATA: Insufficient trend telemetry in active monitoring window.")
        else:
            c_tr1, c_tr2, c_tr3 = st.columns(3)
            with c_tr1:
                st.metric("Observation Window", trends.get("timeframe", "14d"))
            with c_tr2:
                st.metric("Trajectory", trends.get("trajectory", "STABLE"))
            with c_tr3:
                st.metric("Confidence", f"{trends.get('confidence', 0.88) * 100:.1f}%")
            st.dataframe(pd.DataFrame(trends.get("trend_points", [])), use_container_width=True, hide_index=True)

    # 7. Risk Heatmap
    with t7:
        st.subheader("7. Geospatial Risk Heatmap & Proximity Map")
        st.caption("Privacy-preserved generalized coordinates for monitored livestock holdings.")
        if user_role == "farmer":
            st.warning("Regional geospatial surveillance is restricted to institutional and veterinary users.")
        else:
            geo = api_client.get_institutional_geospatial_surveillance() or {}
            farms_pts = geo.get("farms", [])
            if not farms_pts:
                st.info("INSUFFICIENT DATA: No geospatial holdings available for mapping.")
            else:
                df_geo = pd.DataFrame(farms_pts)
                st.dataframe(df_geo[["farm_id", "district", "state", "risk_level", "cluster_membership"]], use_container_width=True, hide_index=True)

    # 8. Event Review Queue
    with t8:
        st.subheader("8. Epidemiological Event Review Queue")
        st.caption("Formal human review and authorized confirmation workflow.")
        st.warning("⚠️ **SAFETY MANDATE:** VETRA never automatically confirms an event. Only authorized institutional review may transition an event to CONFIRMED.")
        open_events = [e for e in (api_client.list_epidemiological_events() or []) if e.get("status") != "CONFIRMED"]

        if not open_events:
            st.info("INSUFFICIENT DATA: No epidemiological events currently awaiting review.")
        else:
            sel_ev_id = st.selectbox("Select Event to Review", options=[e.get("event_id") for e in open_events], key="sb_rev_ev_id")
            col_rev1, col_rev2 = st.columns(2)
            with col_rev1:
                st.markdown("##### 🔍 Human Review")
                r_state = st.selectbox("Review Action", ["UNDER_REVIEW", "REVIEWED", "DISMISSED"], key="sb_rev_state")
                r_notes = st.text_area("Review Rationale", "Epidemiological telemetry reviewed by officer.", key="ta_rev_notes")
                if st.button("Submit Review", key="btn_sub_rev"):
                    ok, res = api_client.review_epidemiological_event(sel_ev_id, r_state, r_notes)
                    if ok:
                        st.success(f"Event {sel_ev_id} review state updated to {r_state}.")
                        st.rerun()
                    else:
                        st.error(f"Error: {res}")

            with col_rev2:
                st.markdown("##### 🏛️ Official Confirmation (Authorized Institutional Action)")
                if user_role not in ["institutional_officer", "admin"]:
                    st.info("Only Institutional Officers and Administrators possess confirmation authority.")
                else:
                    c_auth = st.text_input("Confirmation Authority", f"{user_info.get('full_name', 'Officer')} ({user_role.upper()})")
                    c_notes = st.text_area("Confirmation Findings", "Official verification completed per syndromic findings.", key="ta_conf_notes")
                    if st.button("Confirm Event", key="btn_confirm_ev"):
                        ok, res = api_client.confirm_epidemiological_event(sel_ev_id, c_auth, c_notes)
                        if ok:
                            st.success(f"Event {sel_ev_id} officially CONFIRMED.")
                            st.rerun()
                        else:
                            st.error(f"Error: {res}")

    # 9. Institutional Evidence Matrix
    with t9:
        st.subheader("9. Multi-Source Surveillance Evidence Matrix")
        st.caption("Synthesizes IoT, Computer Vision, Predictive AI, Veterinary, Laboratory, and Preventive signals.")
        matrix = api_client.get_surveillance_evidence_matrix() or {}
        st.markdown(f"**Surveillance Index:** `{matrix.get('surveillance_index', 'NOMINAL')}` | **Synthesized At:** `{matrix.get('synthesized_at', '')}`")

        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.markdown("##### 📡 Telemetry & Clinical Evidence Sources")
            ev_sources = matrix.get("evidence_sources", {})
            for k, v in ev_sources.items():
                st.markdown(f"• **{k.replace('_', ' ').title()}:** {v}")

        with c_m2:
            st.markdown("##### 🔬 Explainability & Provenance")
            for expl in matrix.get("explainability", []):
                st.markdown(f"• {expl}")

    # 10. Government Data Package
    with t10:
        st.subheader("10. Government Data Packaging & Surveillance Export")
        st.caption("Standardized data packaging layer (schema v1.0.0).")
        st.warning("⚠️ **NOTICE:** Government-ready export package — not an official submission.")

        if user_role in ["institutional_officer", "admin"]:
            with st.expander("➕ Generate New Government Data Package", expanded=False):
                with st.form("form_gen_pkg"):
                    p_title = st.text_input("Package Title", "District Livestock Surveillance Summary Package")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        p_start = st.date_input("Start Date", value=datetime.now(timezone.utc).date())
                    with col_p2:
                        p_end = st.date_input("End Date", value=datetime.now(timezone.utc).date())
                    p_entity = st.selectbox("Reporting Entity Type", ["district_surveillance_unit", "state_veterinary_authority", "institutional_monitor"])
                    p_mask = st.checkbox("Apply Privacy & PII Masking", value=True)
                    submitted_pkg = st.form_submit_button("Compile Government Package")

                    if submitted_pkg:
                        payload = {
                            "title": p_title,
                            "reporting_period": {
                                "start_date": p_start.isoformat(),
                                "end_date": p_end.isoformat(),
                                "period_type": "custom"
                            },
                            "reporting_entity_type": p_entity,
                            "mask_pii": p_mask
                        }
                        ok, res = api_client.generate_government_package(payload)
                        if ok:
                            st.success(f"Package generated: ID `{res.get('package_id')}`")
                            st.rerun()
                        else:
                            st.error(f"Error: {res}")

        packages = api_client.list_government_packages() or []
        if not packages:
            st.info("INSUFFICIENT DATA: No government data packages compiled yet.")
        else:
            sel_pkg_id = st.selectbox("Select Government Package", options=[p.get("package_id") for p in packages], key="sb_pkg_view")
            pkg_doc = api_client.get_government_package(sel_pkg_id)

            if pkg_doc:
                st.markdown(f"#### 📄 {pkg_doc.get('title')} (`{pkg_doc.get('package_id')}`)")
                col_pk1, col_pk2, col_pk3, col_pk4 = st.columns(4)
                with col_pk1:
                    st.metric("Approval Status", pkg_doc.get("approval_status"))
                with col_pk2:
                    st.metric("Submission Status", pkg_doc.get("submission_status"))
                with col_pk3:
                    st.metric("Holdings", pkg_doc.get("affected_farm_count"))
                with col_pk4:
                    st.metric("Livestock", pkg_doc.get("affected_animal_count"))

                # Package Actions: Validate, Approve, Export, Submit
                col_act1, col_act2, col_act3 = st.columns(3)
                with col_act1:
                    if st.button("🛡️ Validate Safety Gates", key="btn_val_pkg"):
                        val_res = api_client.validate_government_package(sel_pkg_id)
                        if val_res.get("validation_passed"):
                            st.success("All 8 Safety Gates Passed.")
                        else:
                            st.error(f"Validation Blocked: {val_res.get('errors')}")

                with col_act2:
                    if pkg_doc.get("approval_status") != "APPROVED" and user_role in ["institutional_officer", "admin"]:
                        if st.button("✍️ Approve Package", key="btn_appr_pkg"):
                            ok, res = api_client.approve_government_package(sel_pkg_id, "Approved by institutional officer.")
                            if ok:
                                st.success("Package APPROVED.")
                                st.rerun()
                            else:
                                st.error(f"Failed to approve: {res}")

                with col_act3:
                    if st.button("🚀 Submit to Regulatory Adapter", key="btn_sub_pkg"):
                        ok, res = api_client.submit_government_package(sel_pkg_id)
                        if ok:
                            st.success("Submitted successfully.")
                        else:
                            st.error(f"Submission Blocked: {res}")

                # Export downloads
                st.markdown("##### 📥 Export Data Package")
                exp_col1, exp_col2, exp_col3 = st.columns(3)
                with exp_col1:
                    json_data = api_client.export_government_package_json(sel_pkg_id)
                    st.download_button("Download JSON", data=json.dumps(json_data, indent=2), file_name=f"{sel_pkg_id}.json", mime="application/json")
                with exp_col2:
                    ok, csv_str = api_client.export_government_package_csv(sel_pkg_id)
                    if ok:
                        st.download_button("Download CSV", data=str(csv_str), file_name=f"{sel_pkg_id}.csv", mime="text/csv")
                with exp_col3:
                    ok, pdf_bytes = api_client.export_government_package_pdf(sel_pkg_id)
                    if ok and isinstance(pdf_bytes, bytes):
                        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{sel_pkg_id}.pdf", mime="application/pdf")

    # 11. Integration Readiness
    with t11:
        st.subheader("11. Integration Readiness & Adapter Health")
        st.caption("Verification of external surveillance gateways and safety gate readiness.")
        status_info = api_client.get_government_adapter_status() or {}
        st.markdown(f"**Gateway State:** `{status_info.get('government_adapter_status', 'NOT_CONFIGURED')}`")
        st.info("Default development state is strictly: **NOT_CONFIGURED**. Live transmissions are blocked by safety gates.")

        st.markdown("##### 🛡️ The 8 Mandatory Submission Safety Gates")
        gates = [
            ("Gate 1", "Data Validation", "Package conformant with schema_version 1.0.0"),
            ("Gate 2", "Required Fields", "Mandatory identifiers, reporting periods, and aggregations present"),
            ("Gate 3", "Human Review", "Human officer review completed (review_status == REVIEWED)"),
            ("Gate 4", "Authorized Approval", "Official authorization recorded (approval_status == APPROVED)"),
            ("Gate 5", "Adapter Configured", "External gateway adapter active (State != NOT_CONFIGURED)"),
            ("Gate 6", "Adapter Health", "Adapter health check confirmed without errors"),
            ("Gate 7", "Authorized Initiator", "Submission explicitly triggered by Institutional Officer or Admin"),
            ("Gate 8", "Audit Logging", "Tamper-resistant audit record inserted in audit trail")
        ]
        st.dataframe(pd.DataFrame(gates, columns=["Gate", "Requirement", "Verification Standard"]), use_container_width=True, hide_index=True)

    # 12. Audit Trail
    with t12:
        st.subheader("12. Surveillance Audit Trail")
        st.caption("Immutable record of epidemiological event reviews, early warnings, and package workflows.")
        audits = api_client.get_audit_logs() if hasattr(api_client, "get_audit_logs") else []
        if not audits:
            st.info("INSUFFICIENT DATA: No surveillance audit records logged yet.")
        else:
            st.dataframe(pd.DataFrame(audits).tail(30), use_container_width=True)


# =====================================================================
# PHASE 12: INSTITUTIONAL REPORTING & TELEMEDICINE (PRESERVED)
# =====================================================================
def render_phase12_reporting(user_info: dict, user_role: str, user_farm_id: Optional[str]):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
        "📊 1. Surveillance",
        "🔍 2. Event Reviews",
        "👨‍⚕️ 3. Vet Network",
        "⏳ 4. Pending Reports",
        "📤 5. Submitted Reports",
        "🚨 6. Institutional Alerts",
        "🌾 7. Farm Risk",
        "🗺️ 8. Regional",
        "🧪 9. Lab Results",
        "📁 10. Reporting & Export",
        "🔌 11. Integration Status",
        "📜 12. Audit Activity"
    ])

    reports = api_client.get_institutional_reports() or []
    adapters = api_client.get_institutional_integrations() or []
    vet_profiles = api_client.get_veterinary_profiles() or []
    lab_results = api_client.get_laboratory_results() or []
    surv_summary = api_client.get_surveillance_summary() or {}

    with tab1:
        st.subheader("1. Institutional Surveillance Overview")
        st.caption("Aggregated multi-farm health observations and syndromic signal tracking.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Monitored Farms", surv_summary.get("monitored_farms", 0))
        with c2:
            st.metric("Total Animals", surv_summary.get("monitored_animals", 0))
        with c3:
            st.metric("Active Signals", surv_summary.get("active_events", 0))
        with c4:
            st.metric("Surveillance Level", surv_summary.get("surveillance_status", "NORMAL"))

    with tab2:
        st.subheader("2. Disease Event Reviews")
        st.caption("Clinical syndromic clusters identified for institutional validation.")
        evs = api_client.get_surveillance_events() or []
        if not evs:
            st.info("No disease events flagged for review.")
        else:
            st.dataframe(pd.DataFrame(evs), use_container_width=True)

    with tab3:
        st.subheader("3. Registered Veterinary Network")
        st.caption("Certified veterinary professionals within the institutional registry.")
        if not vet_profiles:
            st.info("No veterinary profiles found.")
        else:
            st.dataframe(pd.DataFrame(vet_profiles), use_container_width=True)

    with tab4:
        st.subheader("4. Pending Institutional Reports")
        st.caption("Reports currently in DRAFT or UNDER_REVIEW state.")
        pending = [r for r in reports if r.get("status") in ("draft", "under_review")]
        if not pending:
            st.info("No pending institutional reports.")
        else:
            st.dataframe(pd.DataFrame(pending), use_container_width=True)

    with tab5:
        st.subheader("5. Submitted & Acknowledged Reports")
        st.caption("Reports submitted to institutional buffers or simulated regulatory exchanges.")
        submitted = [r for r in reports if r.get("status") in ("submitted", "acknowledged")]
        if not submitted:
            st.info("No submitted reports.")
        else:
            st.dataframe(pd.DataFrame(submitted), use_container_width=True)

    with tab6:
        st.subheader("6. Institutional Alerts")
        st.caption("System-wide syndromic and biosecurity alerts.")
        alerts = api_client.get_alerts() or []
        if not alerts:
            st.info("No institutional alerts active.")
        else:
            st.dataframe(pd.DataFrame(alerts), use_container_width=True)

    with tab7:
        st.subheader("7. Farm Risk Distribution")
        st.caption("Evaluated biosecurity and syndromic risk tiers across participating holdings.")
        farms = api_client.get_farms() or []
        if not farms:
            st.info("No farm records found.")
        else:
            st.dataframe(pd.DataFrame(farms), use_container_width=True)

    with tab8:
        st.subheader("8. Regional Surveillance Map")
        st.caption("District-level disease mapping.")
        pts = api_client.get_surveillance_risk_map() or []
        if not pts:
            st.info("No regional map points found.")
        else:
            st.dataframe(pd.DataFrame(pts), use_container_width=True)

    with tab9:
        st.subheader("9. Diagnostic Laboratory Results")
        st.caption("Registered laboratory diagnostic records and confirmatory reports.")
        if not lab_results:
            st.info("No laboratory records registered.")
        else:
            st.dataframe(pd.DataFrame(lab_results), use_container_width=True)

    with tab10:
        st.subheader("10. Reporting & Export")
        st.caption("Draft new institutional report or export data packages.")
        if reports:
            sel_exp_id = st.selectbox("Select Report to Export", options=[r.get("report_id") for r in reports])
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                redact = st.checkbox("Redact Farm and Owner PII for Research", value=False)
            with col_ex2:
                export_fmt = st.selectbox("Format", ["json", "csv"])

            if st.button("📥 Download Export Package"):
                ok, content = api_client.export_institutional_report(sel_exp_id, format=export_fmt, redact_pii=redact)
                if ok:
                    st.download_button(
                        label=f"💾 Save {sel_exp_id}.{export_fmt}",
                        data=content,
                        file_name=f"{sel_exp_id}.{export_fmt}",
                        mime="application/json" if export_fmt == "json" else "text/csv"
                    )
                else:
                    st.error("Failed to generate export.")

    with tab11:
        st.subheader("11. Institutional Integration Adapters")
        st.caption("Pre-configured interface adapters for external veterinary departments and state platforms.")
        if not adapters:
            st.info("No integration adapters registered.")
        else:
            for ad in adapters:
                st.markdown(
                    f"""
                    <div style="border: 1px solid #273449; background: #151F2E; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <h4 style="margin: 0; color: #F8FAFC;">{ad.get('adapter_name')}</h4>
                            <span style="background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid #273449; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem;">
                                {ad.get('status')}
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 0.2rem;">
                            Adapter ID: <code>{ad.get('adapter_id')}</code> | System Type: <b>{ad.get('system_type')}</b>
                        </div>
                        <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #CBD5E1;">
                            <b>Disclaimer:</b> {ad.get('disclaimer')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with tab12:
        st.subheader("12. Institutional Audit Activity")
        st.caption("Immutable trail of report creation, reviews, approvals, and adapter dispatches.")
        recent_audits = []
        for r in reports:
            for entry in r.get("audit_trail") or []:
                entry_copy = dict(entry)
                entry_copy["report_id"] = r.get("report_id")
                recent_audits.append(entry_copy)

        if not recent_audits:
            st.info("No institutional audit entries logged yet.")
        else:
            st.dataframe(pd.DataFrame(recent_audits).tail(30), use_container_width=True)

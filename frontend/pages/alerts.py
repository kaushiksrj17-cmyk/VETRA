import streamlit as st

import api_client
from styles import page_header, empty_state


def render_alerts_page():
    """
    Render health alert inbox with status filtering, acknowledge, and resolve workflows.
    """
    page_header("🚨 Health Alert Center", "Early disease warnings, physiological anomalies, and triage actions")

    col1, col2 = st.columns([1, 1])
    with col1:
        status_choice = st.selectbox(
            "Filter by Status",
            options=["All", "Active", "Acknowledged", "Resolved"],
            index=0
        )
    with col2:
        severity_choice = st.selectbox(
            "Filter by Severity",
            options=["All", "Critical", "High", "Medium", "Low"],
            index=0
        )

    status_filter = None if status_choice == "All" else status_choice.lower()
    severity_filter = None if severity_choice == "All" else severity_choice.lower()

    with st.spinner("Fetching alerts..."):
        alerts = api_client.get_alerts(status=status_filter, severity=severity_filter)

    if not alerts:
        empty_state("No Alerts Found", "No health alerts match the selected status and severity criteria.", "✅")
        return

    st.caption(f"Showing {len(alerts)} alert(s)")

    existing_cases = api_client.get_veterinary_cases(limit=100)
    cases_by_alert = {c.get("alert_id"): c for c in existing_cases if c.get("alert_id")}

    for alert in alerts:
        alert_id = alert["id"]
        status = alert.get("status", "active")
        severity = alert.get("severity", "medium").lower()

        sev_class = f"badge-{severity}"
        status_class = f"badge-{status}"
        linked_case = cases_by_alert.get(alert_id)

        extra_meta = ""
        if alert.get("visual_analysis_id"):
            extra_meta += f" &nbsp;•&nbsp; <strong>Visual Analysis:</strong> <code>{alert.get('visual_analysis_id')}</code>"
        if alert.get("multimodal_assessment_id"):
            extra_meta += f" &nbsp;•&nbsp; <strong>Multimodal ID:</strong> <code>{alert.get('multimodal_assessment_id')}</code>"

        card_html = (
            f'<div class="alert-card alert-card-{severity}">'
            f'<div style="display: flex; justify-content: space-between; align-items: center;">'
            f'<div><span class="badge {sev_class}">{severity.upper()}</span>&nbsp;<span class="badge {status_class}">{status.upper()}</span></div>'
            f'<span style="font-size: 0.8rem; color: #94A3B8;">🕒 {alert.get("created_at", "")[:19]}</span>'
            f'</div>'
            f'<div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-top: 0.5rem;">{alert.get("title")}</div>'
            f'<div style="font-size: 0.9rem; color: #CBD5E1; margin-top: 0.25rem; line-height: 1.4;">{alert.get("message")}</div>'
            f'<div style="margin-top: 0.6rem; font-size: 0.8rem; color: #94A3B8;">'
            f'<strong>Animal ID:</strong> <code>{alert.get("animal_id")}</code> &nbsp;•&nbsp; <strong>Source:</strong> <code>{alert.get("device_id")}</code>{extra_meta}'
            f'</div>'
            f'</div>'
        )

        with st.container():
            st.markdown(card_html, unsafe_allow_html=True)

            if linked_case:
                st.caption(
                    f"🩺 **Linked Veterinary Case:** `{linked_case.get('case_number')}` "
                    f"&nbsp;•&nbsp; Status: **{linked_case.get('status', '').upper()}** "
                    f"&nbsp;•&nbsp; Assigned: **{linked_case.get('assigned_veterinarian_name') or 'Unassigned'}**"
                )

            # Action buttons for active / acknowledged alerts
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.6])

            if status == "active":
                with btn_col1:
                    if st.button("👁️ Acknowledge", key=f"ack_{alert_id}", use_container_width=True):
                        success, err = api_client.acknowledge_alert(alert_id)
                        if success:
                            st.success("Alert acknowledged.")
                            st.rerun()
                        else:
                            st.error(err)

                with btn_col2:
                    if st.button("✅ Resolve", key=f"res_{alert_id}", use_container_width=True):
                        success, err = api_client.resolve_alert(alert_id)
                        if success:
                            st.success("Alert resolved.")
                            st.rerun()
                        else:
                            st.error(err)

                with btn_col3:
                    if linked_case:
                        st.button(
                            f"📋 Case Exists ({linked_case.get('case_number')})",
                            key=f"has_case_{alert_id}",
                            disabled=True,
                            use_container_width=True
                        )
                    else:
                        if st.button("🩺 Create Veterinary Case", key=f"create_case_{alert_id}", use_container_width=True):
                            is_prev = alert.get("alert_type", "").startswith("preventive")
                            is_vis = alert.get("alert_type", "").startswith("visual") or alert.get("alert_type", "").startswith("multimodal")
                            case_payload = {
                                "animal_id": alert.get("animal_id"),
                                "title": f"Alert Escalation: {alert.get('title')}",
                                "description": alert.get("message"),
                                "case_type": "suspected_disease" if is_vis else ("preventive_follow_up" if is_prev else "health_alert"),
                                "priority": alert.get("severity", "medium").lower(),
                                "source": "visual_health_alert" if is_vis else "alert",
                                "alert_id": alert_id,
                            }
                            success, result = api_client.create_veterinary_case(case_payload)
                            if success:
                                st.success(f"Veterinary case {result.get('case_number')} created!")
                                st.rerun()
                            else:
                                st.error(str(result))

            elif status == "acknowledged":
                with btn_col1:
                    if st.button("✅ Resolve", key=f"res_{alert_id}", use_container_width=True):
                        success, err = api_client.resolve_alert(alert_id)
                        if success:
                            st.success("Alert resolved.")
                            st.rerun()
                        else:
                            st.error(err)

                with btn_col2:
                    if linked_case:
                        st.button(
                            f"📋 Case Exists ({linked_case.get('case_number')})",
                            key=f"has_case_{alert_id}",
                            disabled=True,
                            use_container_width=True
                        )
                    else:
                        if st.button("🩺 Create Veterinary Case", key=f"create_case_{alert_id}", use_container_width=True):
                            is_prev = alert.get("alert_type", "").startswith("preventive")
                            is_vis = alert.get("alert_type", "").startswith("visual") or alert.get("alert_type", "").startswith("multimodal")
                            case_payload = {
                                "animal_id": alert.get("animal_id"),
                                "title": f"Alert Escalation: {alert.get('title')}",
                                "description": alert.get("message"),
                                "case_type": "suspected_disease" if is_vis else ("preventive_follow_up" if is_prev else "health_alert"),
                                "priority": alert.get("severity", "medium").lower(),
                                "source": "visual_health_alert" if is_vis else "alert",
                                "alert_id": alert_id,
                            }
                            success, result = api_client.create_veterinary_case(case_payload)
                            if success:
                                st.success(f"Veterinary case {result.get('case_number')} created!")
                                st.rerun()
                            else:
                                st.error(str(result))

            st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)

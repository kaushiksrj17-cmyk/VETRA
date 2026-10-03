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


def render_camera_monitoring_page():
    """
    VETRA Phase 10 — Edge Computer Vision & Automated Livestock Monitoring.
    Continuous camera stream ingestion, edge device health, controlled frame sampling,
    live snapshot inspection, temporal visual intelligence, and automated triage.
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
                        📹 Live Camera & Edge Intelligence
                    </h1>
                    <p style="margin: 0.35rem 0 0 0; font-size: 0.95rem; color: #94a3b8;">
                        Automated continuous visual livestock monitoring, edge computing runtime, and real-time clinical triage.
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="display: inline-block; padding: 0.35rem 0.85rem; border-radius: 9999px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 0.85rem; font-weight: 600;">
                        EDGE INFERENCE ACTIVE
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Clinical Safety Notice
    st.info(
        "🛡️ **Clinical Decision Support Mandate:** Camera-based visual inference provides continuous behavioral and "
        "morphological screening. It does NOT autonomously diagnose livestock diseases. Veterinary examination is "
        "required for clinical confirmation."
    )

    # -------------------------------------------------------------
    # 2. FLEET KPI SUMMARY STRIP (Section 1: Camera Overview)
    # -------------------------------------------------------------
    cam_summary = api_client.get_camera_summary()
    edge_summary = api_client.get_edge_device_summary()

    tot_cams = cam_summary.get("total_cameras", 0)
    online_cams = cam_summary.get("online_cameras", 0)
    deg_cams = cam_summary.get("degraded_cameras", 0)
    off_cams = cam_summary.get("offline_cameras", 0)
    tot_edge = edge_summary.get("total_devices", 0)
    online_edge = edge_summary.get("online_devices", 0)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📹 Total Cameras", tot_cams)
    k2.metric("🟢 Online Cameras", online_cams)
    k3.metric("🟡 Degraded Streams", deg_cams)
    k4.metric("🔴 Offline Streams", off_cams)
    k5.metric("⚡ Edge Devices", tot_edge)
    k6.metric("✅ Healthy Edge Nodes", online_edge)

    st.divider()

    # -------------------------------------------------------------
    # 3. FILTERS (Section 26)
    # -------------------------------------------------------------
    st.markdown("#### 🔍 Filter & Triage Stream Feeds")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    farms_list = api_client.get_farms()
    farm_options = {"All Farms": None}
    for f in farms_list:
        farm_options[f.get("name") or f.get("farm_name") or f["id"]] = f["id"]

    with f_col1:
        sel_farm_name = st.selectbox("Holding / Farm", list(farm_options.keys()), index=0)
        sel_farm_id = farm_options[sel_farm_name]

    with f_col2:
        sel_status = st.selectbox(
            "Stream Status",
            ["All", "online", "degraded", "offline", "disabled"],
            index=0
        )
        status_filter = None if sel_status == "All" else sel_status

    with f_col3:
        sel_type = st.selectbox(
            "Camera Enclosure",
            ["All", "stationary_pen", "cattle_shed", "feeding_area", "milking_area", "quarantine_area"],
            index=0
        )
        type_filter = None if sel_type == "All" else sel_type

    with f_col4:
        conn_filter = st.selectbox("Connection Protocol", ["All", "mock", "rtsp", "http", "webhook"], index=0)

    # Fetch filtered camera list
    cameras = api_client.get_cameras(
        farm_id=sel_farm_id,
        status=status_filter,
        camera_type=type_filter
    )
    if conn_filter != "All":
        cameras = [c for c in cameras if c.get("connection_type") == conn_filter]

    # Quick Add Camera Form Modal / Expander
    with st.expander("➕ Register New Camera Feed"):
        with st.form("register_cam_form"):
            rc_name = st.text_input("Camera Name Designation", "Pen 4 North Overhead Cam")
            rc_farm_options = [f["id"] for f in farms_list] if farms_list else ["farm-default"]
            rc_farm = st.selectbox("Holding Farm ID", rc_farm_options)
            rc_pen = st.text_input("Pen / Shed ID", "PEN-04")
            rc_type = st.selectbox(
                "Enclosure Placement",
                ["stationary_pen", "cattle_shed", "feeding_area", "milking_area", "quarantine_area"]
            )
            rc_conn = st.selectbox("Stream Type", ["mock", "rtsp", "http", "webhook"])
            rc_stream_url = st.text_input(
                "Stream URL / Reference (Credentials will be safely redacted)",
                "mock://feed-pen-04" if rc_conn == "mock" else "rtsp://admin:pass@192.168.1.120:554/live"
            )
            rc_fps = st.slider("Target Stream FPS", 5.0, 60.0, 25.0)
            rc_interval = st.slider("Frame Inference Sampling Interval (seconds)", 1.0, 60.0, 5.0)
            submitted = st.form_submit_button("Register Camera", type="primary")
            if submitted:
                payload = {
                    "camera_name": rc_name,
                    "farm_id": rc_farm,
                    "pen_id": rc_pen,
                    "camera_type": rc_type,
                    "connection_type": rc_conn,
                    "stream_url_reference": rc_stream_url,
                    "fps_target": rc_fps,
                    "sampling_interval_seconds": rc_interval,
                }
                ok, res = api_client.register_camera(payload)
                if ok:
                    st.success(f"Camera '{rc_name}' registered successfully! ID: {res.get('camera_id')}")
                    st.rerun()
                else:
                    st.error(f"Registration failed: {res}")

    st.divider()

    # -------------------------------------------------------------
    # 4. LIVE SNAPSHOT & REAL-TIME ANALYSIS (Sections 3, 27)
    # -------------------------------------------------------------
    st.markdown("### 📸 Live Camera Snapshots & On-Demand Inference")

    if not cameras:
        st.warning(
            "⚠️ **NO ACTIVE CAMERA CONNECTION**\n\n"
            "No camera streams match the selected filter criteria. "
            "Register a new camera above or select a mock adapter for simulation testing."
        )
    else:
        cam_choices = {f"{c['camera_name']} ({c['camera_id']})": c for c in cameras}
        sel_cam_label = st.selectbox("Select Target Stream Feed", list(cam_choices.keys()), index=0)
        sel_cam = cam_choices[sel_cam_label]
        target_cam_id = sel_cam["camera_id"]

        snap_col_left, snap_col_right = st.columns([1.6, 1.4])

        with snap_col_left:
            st.markdown(f"##### 🖥️ Live Stream Feed: `{target_cam_id}`")
            # Snapshot acquisition
            ok_snap, snap_data = api_client.get_camera_snapshot(target_cam_id)
            if ok_snap and isinstance(snap_data, bytes):
                try:
                    img = Image.open(io.BytesIO(snap_data))
                    st.image(img, caption=f"Snapshot from {sel_cam['camera_name']} (Sampled {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')})", use_container_width=True)
                except Exception:
                    st.error("Error decoding camera frame.")
            else:
                st.error(f"Camera Stream Unavailable: {snap_data}")
                st.info(f"Last frame timestamp: {sel_cam.get('last_frame_at') or 'No frames recorded yet'}")

            btn_c1, btn_c2, btn_c3 = st.columns(3)
            with btn_c1:
                if st.button("🔄 Refresh Snapshot", use_container_width=True):
                    st.rerun()
            with btn_c2:
                test_clicked = st.button("📡 Test Stream", use_container_width=True)
                if test_clicked:
                    tok, tres = api_client.test_camera_connection(target_cam_id)
                    if tok and isinstance(tres, dict) and tres.get("connected"):
                        st.success(f"Stream responsive! Latency: {tres.get('latency_ms')}ms")
                    else:
                        st.error(f"Stream unreachable: {tres}")
            with btn_c3:
                run_analysis_clicked = st.button("🧠 Run Live Inference", type="primary", use_container_width=True)

        with snap_col_right:
            st.markdown("##### 📊 Stream Telemetry & Placement")
            st.markdown(
                f"""
                <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155; font-size: 0.9rem; line-height: 1.8; color: #e2e8f0;">
                    • <strong>Camera ID:</strong> <code>{target_cam_id}</code><br>
                    • <strong>Holding Farm:</strong> {sel_cam.get('farm_name') or sel_cam.get('farm_id')}<br>
                    • <strong>Enclosure / Pen:</strong> {sel_cam.get('pen_id', 'General Enclosure')}<br>
                    • <strong>Placement Type:</strong> {sel_cam.get('camera_type')}<br>
                    • <strong>Protocol:</strong> <code>{sel_cam.get('connection_type')}</code><br>
                    • <strong>Stream URI (Redacted):</strong> <code>{sel_cam.get('stream_url_reference')}</code><br>
                    • <strong>Sampling Rate:</strong> 1 frame every {sel_cam.get('sampling_interval_seconds', 5.0)}s<br>
                    • <strong>Status:</strong> <span style="font-weight:700; color:{'#10b981' if sel_cam.get('status')=='online' else '#ef4444'};">{sel_cam.get('status', 'unknown').upper()}</span><br>
                    • <strong>Last Seen:</strong> {sel_cam.get('last_seen') or 'Never'}<br>
                    • <strong>Last Inference:</strong> {sel_cam.get('last_inference_at') or 'No inferences yet'}
                </div>
                """,
                unsafe_allow_html=True
            )

            # Live Analysis Result Display
            if run_analysis_clicked:
                with st.spinner("Executing Edge Model Inference & Multimodal Health Assessment..."):
                    a_ok, a_res = api_client.analyze_camera_frame(target_cam_id)
                    if a_ok and isinstance(a_res, dict):
                        inf = a_res.get("inference", {})
                        v_score = inf.get("visual_risk_score", 0.0)
                        risk_color = "#10b981" if v_score < 0.3 else ("#f59e0b" if v_score < 0.7 else "#ef4444")

                        st.success("Edge Analysis Complete!")
                        st.markdown(
                            f"""
                            <div style="background: #0f172a; padding: 1rem; border-radius: 8px; border: 1px solid {risk_color}; margin-top: 0.75rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight:700; color:#f8fafc;">Visual Health Score:</span>
                                    <span style="font-size: 1.25rem; font-weight:800; color:{risk_color};">{v_score*100:.1f} / 100</span>
                                </div>
                                <div style="font-size: 0.85rem; color:#94a3b8; margin-top: 0.5rem;">
                                    • Model: <code>{inf.get('model_name')} {inf.get('model_version')}</code><br>
                                    • Latency: {inf.get('processing_latency_ms')} ms<br>
                                    • Frame Hash: <code>{a_res.get('frame_hash', '')[:16]}...</code><br>
                                    • Event Status: {'🚨 Alert Triggered' if a_res.get('event_response', {}).get('alert_triggered') else 'Normal'}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.error(f"Inference failed: {a_res}")

    st.divider()

    # -------------------------------------------------------------
    # 5. CAMERA HEALTH METRICS (Section 2: Camera Health)
    # -------------------------------------------------------------
    st.markdown("### 🩺 Camera Fleet Health & Reliability")
    if cameras:
        health_data = []
        for c in cameras:
            h = api_client.get_camera_health(c["camera_id"])
            if h:
                health_data.append({
                    "Camera ID": h["camera_id"],
                    "Name": h["camera_name"],
                    "Status": h["status"].upper(),
                    "Health Tier": h["health_tier"],
                    "Uptime Est.": f"{h['uptime_estimate_pct']}%",
                    "Frames Recv": h["frames_received"],
                    "Frames Drop": h["frames_dropped"],
                    "Inferences": h["inference_count"],
                    "Latency (ms)": h["average_inference_latency_ms"],
                    "Diagnostics": h["connection_message"]
                })
        if health_data:
            df_health = pd.DataFrame(health_data)
            st.dataframe(df_health, use_container_width=True, hide_index=True)

    st.divider()

    # -------------------------------------------------------------
    # 6. EDGE DEVICE HARDWARE HEALTH (Sections 5, 28)
    # -------------------------------------------------------------
    st.markdown("### ⚡ Edge Device Hardware Nodes")
    edge_devices = api_client.get_edge_devices(farm_id=sel_farm_id)
    if not edge_devices:
        st.info("No dedicated edge hardware nodes registered for this holding. Visual inference running via local fallback.")
    else:
        e_cols = st.columns(min(len(edge_devices), 3))
        for idx, dev in enumerate(edge_devices):
            with e_cols[idx % 3]:
                d_id = dev["edge_device_id"]
                d_stat = dev.get("status", "offline")
                stat_badge = "🟢 ONLINE" if d_stat == "online" else "🔴 OFFLINE"

                st.markdown(
                    f"""
                    <div style="background: #1e293b; border-radius: 8px; padding: 1.25rem; border: 1px solid #334155; margin-bottom: 1rem; color: #f8fafc;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h5 style="margin:0; font-size:1.05rem;">{dev.get('device_name', 'Node')}</h5>
                            <span style="font-size:0.75rem; font-weight:700;">{stat_badge}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.6rem; line-height:1.7;">
                            • <strong>Device ID:</strong> <code>{d_id}</code><br>
                            • <strong>Hardware Type:</strong> {dev.get('device_type')}<br>
                            • <strong>Model Runtime:</strong> {dev.get('model_version')}<br>
                            • <strong>CPU Load:</strong> {dev.get('cpu_usage_pct') or 12.0}%<br>
                            • <strong>Memory:</strong> {dev.get('memory_usage_pct') or 25.0}%<br>
                            • <strong>Thermal:</strong> {dev.get('temperature_celsius') or 42.0} °C<br>
                            • <strong>Linked Cameras:</strong> {len(dev.get('camera_ids', []))}<br>
                            • <strong>Last Heartbeat:</strong> {str(dev.get('last_heartbeat') or 'N/A')[:19]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.divider()

    # -------------------------------------------------------------
    # 7. RECENT EDGE INFERENCE OBSERVATIONS (Sections 4, 13)
    # -------------------------------------------------------------
    st.markdown("### 🧠 Recent Edge Visual Inference Events")
    recent_events = api_client.get_recent_edge_events(limit=15)
    if not recent_events:
        st.info("No edge inference events recorded yet.")
    else:
        evt_records = []
        for ev in recent_events:
            evt_records.append({
                "Event ID": ev.get("event_id"),
                "Camera": ev.get("camera_name") or ev.get("camera_id"),
                "Captured At": str(ev.get("captured_at") or "")[:19],
                "Risk Score": f"{ev.get('visual_risk_score', 0.0):.2f}",
                "Confidence": f"{ev.get('confidence', 0.85)*100:.0f}%",
                "Latency": f"{ev.get('processing_latency_ms', 0):.1f} ms",
                "Frame Hash": ev.get("frame_hash", "")[:12] + "...",
            })
        st.dataframe(pd.DataFrame(evt_records), use_container_width=True, hide_index=True)

    st.divider()

    # -------------------------------------------------------------
    # 8. PERSISTENT CONCERNS & CAMERA ALERTS (Sections 7, 9, 20)
    # -------------------------------------------------------------
    st.markdown("### 🚨 Recent Camera & Edge Alerts (With 30-min Cooldown)")
    alerts = api_client.get_alerts()
    cam_alerts = [a for a in alerts if a.get("camera_id") or "visual" in str(a.get("alert_type", "")).lower()]

    if not cam_alerts:
        st.success("✅ No active camera or visual anomaly alerts. All streams operating within normal parameters.")
    else:
        for al in cam_alerts[:5]:
            sev = al.get("severity", "medium").lower()
            sev_color = "#ef4444" if sev == "critical" else ("#f97316" if sev == "high" else "#eab308")
            st.markdown(
                f"""
                <div style="background: #1e293b; border-left: 4px solid {sev_color}; padding: 0.85rem 1.25rem; border-radius: 4px; margin-bottom: 0.6rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color: #f8fafc; font-size: 0.95rem;">{al.get('title')}</strong>
                        <span style="background:{sev_color}25; color:{sev_color}; padding:0.2rem 0.6rem; border-radius:9999px; font-size:0.75rem; font-weight:700;">
                            {sev.upper()}
                        </span>
                    </div>
                    <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.35rem;">
                        {al.get('message')}<br>
                        <small>Camera: <code>{al.get('camera_id', 'N/A')}</code> | Logged: {str(al.get('created_at'))[:19]}</small>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

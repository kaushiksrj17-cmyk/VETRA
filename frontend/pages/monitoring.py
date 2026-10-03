import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api_client


def render_monitoring_page():
    """
    Render live IoT hardware nodes and real-time telemetry streaming graphs.
    """
    header_col, refresh_col = st.columns([3, 1])
    with header_col:
        st.markdown(
            """
            <div class="vetra-header">
                <div class="vetra-brand">📡 Live IoT Telemetry & Sensor Nodes</div>
                <div class="vetra-tagline">Continuous physiological telemetry, ESP32 gateway health, and node signals</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with refresh_col:
        live_stream = st.checkbox("🟢 Stream Live Telemetry (5s)", value=False)
        st.caption(f"Sync time: {time.strftime('%H:%M:%S UTC')}")

    devices = api_client.get_devices()
    animals = api_client.get_animals()

    col_dev, col_telemetry = st.columns([1, 1.8])

    with col_dev:
        st.subheader("Hardware Nodes & Gateway")
        if not devices:
            st.info("No monitoring devices registered yet.")
        else:
            for dev in devices:
                status = dev.get("status", "offline")
                badge_class = f"badge-{status}"
                battery = dev.get("battery_level", 0.0)

                st.markdown(
                    f"""
                    <div class="vetra-panel" style="margin-bottom: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-weight: 700; color: #F8FAFC; font-size: 1rem;">
                                {dev.get('device_name')}
                            </div>
                            <span class="badge {badge_class}">{status.upper()}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: #94A3B8; margin-top: 0.25rem;">
                            ID: <code>{dev.get('device_id')}</code> &nbsp;•&nbsp; Type: {dev.get('device_type')}
                        </div>
                        <div style="margin-top: 0.75rem; font-size: 0.85rem; color: #CBD5E1;">
                            🔋 <strong>Battery:</strong> {battery:.1f}% &nbsp;•&nbsp; 
                            🕒 <strong>Last Seen:</strong> {str(dev.get('last_seen_at') or 'Never')[:19]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with col_telemetry:
        st.subheader("Real-Time Telemetry Stream")
        if not animals:
            st.info("Enroll livestock to see telemetry data.")
        else:
            animal_map = {a["id"]: f"{a.get('name', 'Unnamed')} ({a.get('tag_id')})" for a in animals}
            selected_animal_id = st.selectbox(
                "Select Monitored Animal",
                options=list(animal_map.keys()),
                format_func=lambda aid: animal_map[aid],
                key="mon_animal_sel"
            )

            readings = api_client.get_health_readings(selected_animal_id)

            if not readings:
                st.info("No recorded readings for this animal yet. Start the IoT simulator to stream vitals.")
            else:
                latest = readings[0]

                # Real-time metrics
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("🌡️ Temp", f"{latest.get('temperature_c', 0):.2f} °C")
                m2.metric("💓 HR", f"{latest.get('heart_rate_bpm', 0):.1f} BPM")
                m3.metric("🫁 Resp", f"{latest.get('respiratory_rate', 0):.1f} /min")
                m4.metric("🏃 Act", f"{latest.get('activity_level', 0):.1f}%")
                m5.metric("🌿 Rum", f"{latest.get('rumination_level', 0):.1f}%")

                # Plotly live sensor trend chart
                df = pd.DataFrame(readings[:30][::-1])
                if not df.empty and "recorded_at" in df.columns:
                    df["time"] = pd.to_datetime(df["recorded_at"]).dt.strftime("%H:%M:%S")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df["time"], y=df["temperature_c"], mode="lines+markers", name="Temp (°C)", line=dict(color="#ef4444", width=2)))
                    fig.add_trace(go.Scatter(x=df["time"], y=df["heart_rate_bpm"], mode="lines", name="HR (BPM)", line=dict(color="#3b82f6", width=2)))
                    fig.add_trace(go.Scatter(x=df["time"], y=df["activity_level"], mode="lines", name="Activity (%)", line=dict(color="#8b5cf6", width=1.5)))
                    fig.add_trace(go.Scatter(x=df["time"], y=df["rumination_level"], mode="lines", name="Rumination (%)", line=dict(color="#10b981", width=1.5)))

                    fig.update_layout(
                        template="plotly_dark",
                        title=dict(text="Continuous Multi-Sensor Telemetry (Last 30 Readings)", font=dict(color="#F8FAFC", size=14)),
                        height=380,
                        margin=dict(l=20, r=20, t=40, b=20),
                        plot_bgcolor="#151F2E",
                        paper_bgcolor="#151F2E",
                        font=dict(color="#CBD5E1"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(color="#CBD5E1"))
                    )
                    fig.update_xaxes(showgrid=True, gridcolor="#273449", tickfont=dict(color="#94A3B8"))
                    fig.update_yaxes(showgrid=True, gridcolor="#273449", tickfont=dict(color="#94A3B8"))

                    st.plotly_chart(fig, use_container_width=True)

    if live_stream:
        time.sleep(5)
        st.rerun()

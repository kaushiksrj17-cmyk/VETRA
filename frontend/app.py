import sys
from pathlib import Path

import streamlit as st


# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------

frontend_dir = Path(__file__).resolve().parent

if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))


# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

from session import (
    init_session,
    is_authenticated,
    get_user_info,
    clear_session,
)

from styles import apply_custom_styles, render_top_bar
from auth import render_auth_page

from pages.dashboard import render_dashboard_page
from pages.farms import render_farms_page
from pages.animals import render_animals_page
from pages.monitoring import render_monitoring_page
from pages.alerts import render_alerts_page
from pages.profile import render_profile_page
from pages.animal_profile import render_animal_profile_page
from pages.prevention import render_prevention_page
from pages.veterinarian import render_veterinarian_page
from pages.surveillance import render_surveillance_page
from pages.computer_vision import render_computer_vision_page
from pages.camera_monitoring import render_camera_monitoring_page
from pages.predictive_ai import render_predictive_ai_page
from pages.telemedicine import render_telemedicine_page
from pages.institutional import render_institutional_page


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="VETRA — Intelligent Livestock Health Command Center",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# SESSION INITIALIZATION & STYLING
# ---------------------------------------------------------

init_session()
apply_custom_styles()


# ---------------------------------------------------------
# AUTHENTICATION CHECK
# ---------------------------------------------------------

if not is_authenticated():
    render_auth_page()
    st.stop()


# ---------------------------------------------------------
# CATEGORIZED NAVIGATION STRUCTURE
# ---------------------------------------------------------

NAV_CATEGORIES = {
    "OPERATIONS": [
        ("🏠 Command Center", "Executive Overview & Telemetry"),
        ("🌾 Farms", "Facility Management"),
        ("🐄 Animals", "Livestock Registry"),
        ("📡 Live Monitoring", "Real-Time Telemetry"),
        ("🚨 Alerts", "Health Triage Queue"),
    ],
    "AI INTELLIGENCE": [
        ("👁️ Visual Health", "Computer Vision & Biometrics"),
        ("📹 Live Cameras", "Edge Video Streams"),
        ("🧠 Predictive AI", "Longitudinal Risk Forecasting"),
        ("🦠 Disease Surveillance", "Epidemiological Map & Clusters"),
    ],
    "VETERINARY": [
        ("🩺 Clinical Cases", "Diagnosis & Clinical Records"),
        ("💉 Preventive Health", "Schedules & Compliance"),
        ("🩺 Telemedicine", "Remote Consultations"),
    ],
    "INSTITUTIONAL": [
        ("🏛️ Institutional Health", "Regulatory Surveillance"),
    ],
    "ACCOUNT": [
        ("👤 Profile", "Account & Security"),
    ],
}

ALL_NAV_KEYS = [key for cat in NAV_CATEGORIES.values() for key, _ in cat]

current_nav = st.session_state.get("nav_choice", "🏠 Command Center")
if current_nav not in ALL_NAV_KEYS:
    current_nav = "🏠 Command Center"
    st.session_state["nav_choice"] = current_nav

# Find current section name for breadcrumb
current_section = "OPERATIONS"
for cat_name, items in NAV_CATEGORIES.items():
    if any(k == current_nav for k, _ in items):
        current_section = cat_name
        break

user = get_user_info()
user_name = user.get("full_name", "User")
user_role = str(user.get("role", "Farmer")).upper()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    # VETRA Brand Header
    st.markdown(
        """
        <div class="sidebar-brand-box">
            <div class="sidebar-brand-title">🐄 VETRA</div>
            <div class="sidebar-brand-tagline">AI HEALTH INTELLIGENCE</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Render Categorized Navigation
    for cat_name, items in NAV_CATEGORIES.items():
        st.markdown(f'<div class="sidebar-category-header">{cat_name}</div>', unsafe_allow_html=True)
        for nav_key, desc in items:
            is_active = (nav_key == current_nav)
            btn_type = "primary" if is_active else "secondary"
            if st.button(nav_key, key=f"nav_btn_{nav_key}", use_container_width=True, type=btn_type):
                if current_nav != nav_key:
                    st.session_state["nav_choice"] = nav_key
                    st.rerun()

    # User Info Card
    st.markdown(
        f"""
        <div class="sidebar-user-box">
            <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">SIGNED IN AS</div>
            <div class="sidebar-user-name">{user_name}</div>
            <div class="sidebar-user-role">● {user_role}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Logout
    if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
        clear_session()
        st.rerun()


# ---------------------------------------------------------
# MISSION-CONTROL TOP BAR & PAGE ROUTING
# ---------------------------------------------------------

# Render the compact mission-control breadcrumb & status top bar
render_top_bar(
    current_page=current_nav,
    current_section=current_section,
    role=user_role
)

# Route to the selected page module
if current_nav == "🏠 Command Center":
    render_dashboard_page()

elif current_nav == "🌾 Farms":
    render_farms_page()

elif current_nav == "🐄 Animals":
    render_animals_page()

elif current_nav == "📡 Live Monitoring":
    render_monitoring_page()

elif current_nav == "👁️ Visual Health":
    render_computer_vision_page()

elif current_nav == "📹 Live Cameras":
    render_camera_monitoring_page()

elif current_nav == "🧠 Predictive AI":
    render_predictive_ai_page()

elif current_nav == "🚨 Alerts":
    render_alerts_page()

elif current_nav == "🦠 Disease Surveillance":
    render_surveillance_page()

elif current_nav == "🩺 Clinical Cases":
    render_veterinarian_page()

elif current_nav == "🩺 Telemedicine":
    render_telemedicine_page()

elif current_nav == "🏛️ Institutional Health":
    render_institutional_page()

elif current_nav == "💉 Preventive Health":
    render_prevention_page()

elif current_nav == "👤 Profile":
    render_profile_page()
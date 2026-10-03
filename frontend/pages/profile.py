import streamlit as st

from session import get_user_info
from styles import page_header


def render_profile_page():
    """
    Render user account details and permissions overview.
    """
    user_info = get_user_info()

    page_header("👤 Operator Profile", "Account credentials, system permissions, and session status")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown(
            f"""
            <div class="vetra-panel">
                <h3 style="color: #F8FAFC; margin-top: 0; font-size: 1.15rem; font-weight: 700;">Account Information</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 1rem;">
                    <tr style="border-bottom: 1px solid #273449;">
                        <td style="padding: 0.75rem 0; color: #94A3B8; font-weight: 600;">Full Name</td>
                        <td style="padding: 0.75rem 0; color: #F8FAFC; font-weight: 700;">{user_info.get('full_name')}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #273449;">
                        <td style="padding: 0.75rem 0; color: #94A3B8; font-weight: 600;">Email Address</td>
                        <td style="padding: 0.75rem 0; color: #CBD5E1;">{user_info.get('email')}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #273449;">
                        <td style="padding: 0.75rem 0; color: #94A3B8; font-weight: 600;">System Role</td>
                        <td style="padding: 0.75rem 0;">
                            <span class="badge badge-healthy">{str(user_info.get('role')).upper()}</span>
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #273449;">
                        <td style="padding: 0.75rem 0; color: #94A3B8; font-weight: 600;">Account Status</td>
                        <td style="padding: 0.75rem 0;">
                            <span class="badge badge-online">ACTIVE</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 0.75rem 0; color: #94A3B8; font-weight: 600;">User ID</td>
                        <td style="padding: 0.75rem 0; font-family: monospace; color: #38BDF8;">{user_info.get('user_id')}</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="vetra-panel">
                <h3 style="color: #F8FAFC; margin-top: 0; font-size: 1.15rem; font-weight: 700;">Role Permissions</h3>
                <p style="color: #CBD5E1; font-size: 0.88rem;">
                    Your account has authorized access to:
                </p>
                <ul style="color: #94A3B8; font-size: 0.88rem; line-height: 1.8;">
                    <li>Register and manage private farm facilities</li>
                    <li>Enroll livestock and generate unique QR identities</li>
                    <li>Pair and observe IoT telemetry devices</li>
                    <li>Receive real-time early disease alerts</li>
                    <li>Acknowledge and resolve physiological anomalies</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

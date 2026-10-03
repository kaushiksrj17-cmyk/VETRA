import streamlit as st

import api_client
from session import set_user_session


def render_auth_page():
    """
    Render login and farmer registration forms in a clean, professional, high-contrast dark card.
    """
    col1, col2, col3 = st.columns([1, 1.8, 1])

    with col2:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 2rem; margin-bottom: 1.5rem;">
                <div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 16px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); font-size: 2.2rem; margin-bottom: 0.75rem;">
                    🐄
                </div>
                <h1 style="font-size: 2.2rem; font-weight: 800; color: #F8FAFC; margin: 0; letter-spacing: -0.03em;">
                    VETRA
                </h1>
                <p style="color: #94A3B8; font-size: 0.95rem; font-weight: 500; margin-top: 0.35rem;">
                    AI Livestock Health & Early Disease Prevention Command Center
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_login, tab_register = st.tabs(["🔐 Sign In", "📝 Create Account"])

        # ====================================================
        # LOGIN TAB
        # ====================================================
        with tab_login:
            st.markdown(
                """
                <div style="margin-top: 0.5rem; margin-bottom: 0.75rem;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">Welcome Back</div>
                    <div style="font-size: 0.85rem; color: #94A3B8;">Sign in to access your livestock health telemetry and AI analytics.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email Address", placeholder="e.g. farmer@vetra.demo")
                password = st.text_input("Password", type="password", placeholder="Enter your password")

                submitted = st.form_submit_button("Sign In to Command Center", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            success, result = api_client.login(email=email, password=password)

                        if success:
                            set_user_session(result)
                            st.success("Authentication successful! Loading Command Center...")
                            st.rerun()
                        else:
                            st.error(result)

            # Quick credentials helper for live SIH demonstration
            with st.expander("🔑 SIH Demo Quick Credentials", expanded=False):
                st.markdown(
                    """
                    <div style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.6;">
                        • <strong>Farmer:</strong> <code>farmer@vetra.demo</code> / <code>Vetra@12345</code><br>
                        • <strong>Veterinarian:</strong> <code>vet@vetra.demo</code> / <code>VetraVet@2026</code><br>
                        • <strong>Institutional:</strong> <code>officer@vetra.demo</code> / <code>VetraGov@2026</code><br>
                        • <strong>Administrator:</strong> <code>admin@vetra.demo</code> / <code>VetraAdmin@2026</code>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ====================================================
        # REGISTER TAB
        # ====================================================
        with tab_register:
            st.markdown(
                """
                <div style="margin-top: 0.5rem; margin-bottom: 0.75rem;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">Farmer Registration</div>
                    <div style="font-size: 0.85rem; color: #94A3B8;">Create a new producer account to register your livestock and IoT devices.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            with st.form("register_form", clear_on_submit=False):
                full_name = st.text_input("Full Name", placeholder="e.g. Ramesh Kumar")
                reg_email = st.text_input("Email Address", placeholder="e.g. ramesh@farm.demo")
                reg_password = st.text_input("Password", type="password", placeholder="Minimum 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")

                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if reg_submitted:
                    if not full_name or not reg_email or not reg_password:
                        st.error("All fields are required.")
                    elif "@" not in reg_email or "." not in reg_email:
                        st.error("Please enter a valid email address.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif reg_password != confirm_password:
                        st.error("Passwords do not match. Please verify.")
                    else:
                        with st.spinner("Creating account..."):
                            success, result = api_client.register(
                                full_name=full_name,
                                email=reg_email,
                                password=reg_password
                            )

                        if success:
                            st.success("Account created successfully! Signing in...")
                            login_success, login_result = api_client.login(reg_email, reg_password)
                            if login_success:
                                set_user_session(login_result)
                                st.rerun()
                            else:
                                st.info("Please sign in using your new credentials.")
                        else:
                            st.error(result)

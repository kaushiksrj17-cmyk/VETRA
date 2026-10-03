import streamlit as st

import api_client


def render_farms_page():
    """
    Render farm management page for viewing, registering, and inspecting farms,
    including Phase 8 Disease Surveillance & Geospatial intelligence.
    """
    st.markdown(
        """
        <div class="vetra-header">
            <div class="vetra-brand">🌾 Farm Management & Surveillance</div>
            <div class="vetra-tagline">Manage your registered agricultural holdings, coordinates, and disease risk profiles</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_list, tab_create = st.tabs(["📋 My Farms", "➕ Register New Farm"])

    # ====================================================
    # LIST FARMS
    # ====================================================
    with tab_list:
        with st.spinner("Fetching farms..."):
            farms = api_client.get_farms()
            surv_profiles = {p["farm_id"]: p for p in api_client.get_surveillance_farms()}

        if not farms:
            st.info("No farms registered yet. Click 'Register New Farm' to create your first farm.")
        else:
            st.caption(f"Total registered farms: {len(farms)}")
            for farm in farms:
                fid = str(farm.get("id"))
                prof = surv_profiles.get(fid, {})
                risk_score = prof.get("risk_score", 0.0)
                risk_cat = prof.get("risk_category", "LOW")

                risk_color = "#10B981"
                if risk_cat == "CRITICAL":
                    risk_color = "#EF4444"
                elif risk_cat == "HIGH":
                    risk_color = "#F97316"
                elif risk_cat == "MODERATE":
                    risk_color = "#FBBF24"

                with st.container():
                    st.markdown(
                        f"""
                        <div class="vetra-panel">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                                <div>
                                    <h3 style="margin: 0; color: #F8FAFC;">{farm.get('name')}</h3>
                                    <p style="margin: 0.25rem 0 0.5rem 0; color: #94A3B8; font-size: 0.9rem;">
                                        📍 {farm.get('location')} &nbsp;•&nbsp; 🐄 {farm.get('livestock_type')}
                                    </p>
                                </div>
                                <div style="display: flex; gap: 0.5rem; align-items: center;">
                                    <span style="background: {risk_color}22; color: {risk_color}; border: 1px solid {risk_color}; font-size: 0.85rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 9999px;">
                                        SURVEILLANCE: {risk_cat} ({risk_score:.0f}/100)
                                    </span>
                                    <span class="badge badge-healthy">{farm.get('total_animals', 0)} Animals</span>
                                </div>
                            </div>
                            <p style="color: #CBD5E1; font-size: 0.88rem; margin-top: 0.5rem;">
                                {farm.get('description') or 'No description provided.'}
                            </p>
                            <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 0.5rem;">
                                Farm ID: <code>{fid}</code> &nbsp;•&nbsp; 
                                Coordinates: <code>{farm.get('latitude') if farm.get('latitude') is not None else 'Unavailable'}, {farm.get('longitude') if farm.get('longitude') is not None else ''}</code>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    with st.expander(f"🦠 Disease Surveillance Profile for {farm.get('name')}", expanded=False):
                        if prof:
                            s1, s2, s3, s4 = st.columns(4)
                            s1.metric("Risk Score", f"{risk_score}/100", risk_cat)
                            s2.metric("Affected Animals", f"{prof.get('affected_animals_count', 0)}/{prof.get('total_animals', 0)}")
                            s3.metric("Active Alerts", f"{prof.get('active_alerts_count', 0)}")
                            s4.metric("Dominant Pattern", prof.get("dominant_disease_pattern", "Baseline"))

                            st.markdown("**Contributing Factors:**")
                            for fact in prof.get("contributing_factors", []):
                                st.write(f"- {fact}")

                            if farm.get("latitude") is None:
                                st.caption("📍 *Geographic coordinates unavailable for this farm. Can be registered by updating farm records.*")
                        else:
                            st.info("Surveillance profile being computed.")

                    with st.expander(f"👁️ Visual Health Overview for {farm.get('name')}", expanded=False):
                        farm_analyses = api_client.get_farm_visual_analyses(fid, limit=20)
                        if not farm_analyses:
                            st.info("No visual health analyses conducted for animals in this farm yet.")
                        else:
                            f_distinct_animals = len(set(a.get("animal_id") for a in farm_analyses if a.get("animal_id")))
                            f_high_risk = sum(1 for a in farm_analyses if a.get("risk_category") in ["HIGH", "CRITICAL"])
                            f_pending_rev = sum(1 for a in farm_analyses if a.get("requires_veterinary_review") and a.get("review_status") == "pending")
                            f_total_obs = sum(len(a.get("observations", [])) for a in farm_analyses)

                            vc1, vc2, vc3, vc4 = st.columns(4)
                            vc1.metric("Visually Assessed", f"{f_distinct_animals} Animals")
                            vc2.metric("Visual Signals", f"{f_total_obs} Total")
                            vc3.metric("High Visual Risk", f"{f_high_risk}", delta="Action Required" if f_high_risk > 0 else None, delta_color="inverse")
                            vc4.metric("Pending Vet Reviews", f"{f_pending_rev}")

                            if f_high_risk > 0:
                                st.warning(f"⚠️ {f_high_risk} animal(s) exhibit elevated visual health risk on this farm.")

    # ====================================================
    # CREATE FARM
    # ====================================================
    with tab_create:
        st.markdown("#### Register New Farm")
        st.caption("Provide details about your agricultural holding, including optional coordinates for geospatial disease surveillance.")

        with st.form("create_farm_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                name = st.text_input("Farm Name", placeholder="e.g. Green Pastures Dairy Farm")
                location = st.text_input("Location / City", placeholder="e.g. Anand, Gujarat")
                livestock_type = st.selectbox(
                    "Primary Livestock Type",
                    ["Cattle", "Buffalo", "Sheep", "Goat", "Mixed Dairy", "Poultry", "Swine"]
                )
            with f_col2:
                district = st.text_input("District (Optional)", placeholder="e.g. Anand")
                state = st.text_input("State (Optional)", placeholder="e.g. Gujarat")
                pincode = st.text_input("Pincode (Optional)", placeholder="e.g. 388001")

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                lat_str = st.text_input("Latitude (Optional decimal degrees)", placeholder="e.g. 22.5645")
            with c_col2:
                lon_str = st.text_input("Longitude (Optional decimal degrees)", placeholder="e.g. 72.9289")

            description = st.text_area("Description (Optional)", placeholder="Brief details about facility and infrastructure")

            submitted = st.form_submit_button("Register Farm", type="primary")

            if submitted:
                if not name or not location:
                    st.error("Farm name and location are required.")
                else:
                    payload = {
                        "name": name.strip(),
                        "location": location.strip(),
                        "livestock_type": livestock_type,
                        "total_animals": 0,
                        "description": description.strip() if description else None
                    }
                    if district.strip():
                        payload["district"] = district.strip()
                    if state.strip():
                        payload["state"] = state.strip()
                    if pincode.strip():
                        payload["pincode"] = pincode.strip()

                    try:
                        if lat_str.strip():
                            payload["latitude"] = float(lat_str.strip())
                        if lon_str.strip():
                            payload["longitude"] = float(lon_str.strip())
                    except ValueError:
                        st.warning("Invalid latitude/longitude coordinates entered. Registering without coordinates.")

                    with st.spinner("Registering farm..."):
                        success, result = api_client.create_farm(payload)

                    if success:
                        st.success(f"Farm '{name}' registered successfully!")
                        st.rerun()
                    else:
                        st.error(result)

from datetime import date

import streamlit as st

import api_client
from pages.animal_profile import render_animal_profile_page


def render_animals_page():
    """
    Render livestock registry and animal management.
    """

    # ====================================================
    # PAGE HEADER
    # ====================================================
    st.title("Livestock Registry")
    st.caption(
        "Track individual livestock identities, vitals status, and profiles"
    )

    tab_list, tab_create = st.tabs(
        ["Monitored Herd", "Register Animal"]
    )

    # ====================================================
    # LOAD FARMS
    # ====================================================
    farms = api_client.get_farms()

    farm_options = {
        farm["id"]: farm["name"]
        for farm in farms
    }

    # ====================================================
    # MONITORED HERD
    # ====================================================
    with tab_list:

        selected_farm_id = None

        if farms:
            col_filter, col_space = st.columns([1, 2])

            with col_filter:
                farm_choice = st.selectbox(
                    "Filter by Farm",
                    options=[
                        "All Farms"
                    ] + list(farm_options.values()),
                    key="animal_farm_filter"
                )

                if farm_choice != "All Farms":
                    for farm_id, farm_name in farm_options.items():
                        if farm_name == farm_choice:
                            selected_farm_id = farm_id
                            break

        # ------------------------------------------------
        # FETCH ANIMALS
        # ------------------------------------------------
        with st.spinner("Fetching livestock records..."):
            animals = api_client.get_animals(
                farm_id=selected_farm_id
            )

        if not animals:

            st.info(
                "No animals found. Use the 'Register Animal' tab "
                "to add your livestock."
            )

        else:

            st.caption(
                f"Showing {len(animals)} animal(s)"
            )

            # ====================================================
            # ANIMAL CARDS
            # ====================================================
            for animal in animals:

                animal_id = animal.get("id")
                animal_name = animal.get("name") or "Unnamed"
                tag_id = animal.get("tag_id") or "N/A"
                species = animal.get("species") or "N/A"
                breed = animal.get("breed") or "N/A"

                gender = str(
                    animal.get("gender") or "N/A"
                ).capitalize()

                weight = animal.get(
                    "weight_kg",
                    "N/A"
                )

                health_status = str(
                    animal.get(
                        "health_status",
                        "healthy"
                    )
                )

                health_display = health_status.replace(
                    "_",
                    " "
                ).upper()

                farm_name = farm_options.get(
                    animal.get("farm_id"),
                    animal.get("farm_id", "N/A")
                )

                # ------------------------------------------------
                # ANIMAL CONTAINER
                # ------------------------------------------------
                with st.container(border=True):

                    # Animal name + status
                    col_name, col_status = st.columns(
                        [4, 1]
                    )

                    with col_name:
                        st.subheader(
                            animal_name
                        )

                        st.caption(
                            f"Tag ID: {tag_id}"
                        )

                    with col_status:

                        if health_status == "healthy":
                            st.success(
                                health_display
                            )

                        elif health_status == "monitoring":
                            st.warning(
                                health_display
                            )

                        elif health_status == "at_risk":
                            st.warning(
                                health_display
                            )

                        elif health_status == "critical":
                            st.error(
                                health_display
                            )

                        else:
                            st.info(
                                health_display
                            )

                    # ------------------------------------------------
                    # ANIMAL DETAILS
                    # ------------------------------------------------
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric(
                            "Species",
                            species
                        )

                    with col2:
                        st.metric(
                            "Breed",
                            breed
                        )

                    with col3:
                        st.metric(
                            "Gender",
                            gender
                        )

                    with col4:
                        st.metric(
                            "Weight",
                            f"{weight} kg"
                        )

                    # ------------------------------------------------
                    # IDENTIFICATION DETAILS
                    # ------------------------------------------------
                    st.caption(
                        f"Animal ID: {animal_id}"
                    )

                    st.caption(
                        f"Farm: {farm_name}"
                    )

                    # ------------------------------------------------
                    # HEALTH PROFILE BUTTON
                    # ------------------------------------------------
                    if st.button(
                        "View Animal Health Profile",
                        key=f"profile_{animal_id}",
                        use_container_width=True
                    ):
                        st.session_state[
                            "selected_animal_id"
                        ] = animal_id

                        st.session_state[
                            "open_animal_profile"
                        ] = True

                        st.rerun()

            # ====================================================
            # EXISTING ANIMAL PROFILE
            # ====================================================
            if st.session_state.get(
                "open_animal_profile",
                False
            ):
                st.divider()

                if st.button(
                    "Back to Livestock Registry",
                    key="back_to_animals"
                ):
                    st.session_state[
                        "open_animal_profile"
                    ] = False

                    st.rerun()

                render_animal_profile_page()

    # ====================================================
    # REGISTER ANIMAL
    # ====================================================
    with tab_create:

        st.subheader(
            "Register New Animal"
        )

        st.caption(
            "Enroll an individual animal under one of your registered farms."
        )

        if not farms:

            st.warning(
                "You must register at least one farm "
                "before enrolling livestock."
            )

        else:

            with st.form(
                "create_animal_form",
                clear_on_submit=True
            ):

                farm_id_select = st.selectbox(
                    "Assigned Farm",
                    options=list(
                        farm_options.keys()
                    ),
                    format_func=lambda fid: farm_options[fid]
                )

                col_a, col_b = st.columns(2)

                # ====================================================
                # BASIC DETAILS
                # ====================================================
                with col_a:

                    tag_id = st.text_input(
                        "Ear Tag ID",
                        placeholder="e.g. COW-002"
                    )

                    name = st.text_input(
                        "Animal Name (Optional)",
                        placeholder="e.g. Ganga"
                    )

                    species = st.selectbox(
                        "Species",
                        [
                            "Cattle",
                            "Buffalo",
                            "Sheep",
                            "Goat",
                            "Other"
                        ]
                    )

                    breed = st.text_input(
                        "Breed",
                        placeholder=(
                            "e.g. Holstein Friesian, Gir, Murrah"
                        )
                    )

                # ====================================================
                # HEALTH DETAILS
                # ====================================================
                with col_b:

                    gender = st.selectbox(
                        "Gender",
                        [
                            "female",
                            "male"
                        ]
                    )

                    dob = st.date_input(
                        "Date of Birth",
                        value=date(
                            2023,
                            1,
                            1
                        )
                    )

                    weight = st.number_input(
                        "Weight (kg)",
                        min_value=1.0,
                        max_value=2000.0,
                        value=350.0,
                        step=5.0
                    )

                    health_status = st.selectbox(
                        "Current Health Status",
                        [
                            "healthy",
                            "monitoring",
                            "at_risk",
                            "critical"
                        ]
                    )

                # ====================================================
                # NOTES
                # ====================================================
                notes = st.text_area(
                    "Veterinary Notes / Markings (Optional)",
                    placeholder=(
                        "Vaccination history, ear notch, "
                        "physical condition..."
                    )
                )

                # ====================================================
                # SUBMIT
                # ====================================================
                submitted = st.form_submit_button(
                    "Enroll Animal",
                    type="primary",
                    use_container_width=True
                )

                if submitted:

                    if (
                        not tag_id
                        or not species
                        or not breed
                    ):

                        st.error(
                            "Tag ID, Species, and Breed are required."
                        )

                    else:

                        payload = {
                            "tag_id": tag_id.strip(),
                            "name": (
                                name.strip()
                                if name
                                else None
                            ),
                            "species": species.strip(),
                            "breed": breed.strip(),
                            "gender": gender,
                            "date_of_birth": dob.isoformat(),
                            "weight_kg": float(weight),
                            "health_status": health_status,
                            "notes": (
                                notes.strip()
                                if notes
                                else None
                            )
                        }

                        with st.spinner(
                            "Enrolling animal..."
                        ):

                            success, result = (
                                api_client.create_animal(
                                    farm_id_select,
                                    payload
                                )
                            )

                        if success:

                            st.success(
                                f"Animal '{tag_id}' enrolled successfully "
                                f"under {farm_options[farm_id_select]}!"
                            )

                            st.rerun()

                        else:

                            st.error(
                                result
                            )
from typing import Optional
import streamlit as st


def init_session():
    """
    Initialize default session state keys if not already present.
    """
    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = False

    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    if "full_name" not in st.session_state:
        st.session_state["full_name"] = None

    if "email" not in st.session_state:
        st.session_state["email"] = None

    if "role" not in st.session_state:
        st.session_state["role"] = None


def set_user_session(token_data: dict):
    """
    Store authenticated user session data in Streamlit state.
    """
    user_info = token_data.get("user", {})

    st.session_state["is_authenticated"] = True
    st.session_state["access_token"] = token_data.get("access_token")
    st.session_state["user_id"] = user_info.get("id")
    st.session_state["full_name"] = user_info.get("full_name")
    st.session_state["email"] = user_info.get("email")
    st.session_state["role"] = user_info.get("role")


def get_token() -> Optional[str]:
    """
    Retrieve current JWT access token from session.
    """
    return st.session_state.get("access_token")


def get_user_info() -> dict:
    """
    Retrieve user metadata from session.
    """
    return {
        "user_id": st.session_state.get("user_id"),
        "full_name": st.session_state.get("full_name"),
        "email": st.session_state.get("email"),
        "role": st.session_state.get("role"),
    }


def is_authenticated() -> bool:
    """
    Check if the user is currently authenticated.
    """
    return bool(st.session_state.get("is_authenticated") and st.session_state.get("access_token"))


def clear_session():
    """
    Clear all user session state keys upon logout.
    """
    st.session_state["is_authenticated"] = False
    st.session_state["access_token"] = None
    st.session_state["user_id"] = None
    st.session_state["full_name"] = None
    st.session_state["email"] = None
    st.session_state["role"] = None

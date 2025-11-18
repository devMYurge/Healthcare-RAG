import streamlit as st
from frontend.auth.session_manager import SessionManager


def show_login_page():
    st.title("MedLinkAI — Sign in")
    st.write("Sign in to start using the MedLinkAI assistant (local/demo auth)")
    with st.form("login_form"):
        email = st.text_input("Email")
        name = st.text_input("Name (optional)")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if not email:
                st.error("Please enter an email to continue.")
            else:
                SessionManager.login(email=email, name=name)
                st.experimental_rerun()

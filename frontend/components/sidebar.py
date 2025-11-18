import streamlit as st
from frontend.auth.session_manager import SessionManager


def show_sidebar():
    st.sidebar.title("MedLinkAI")
    if st.session_state.user:
        st.sidebar.markdown(f"**Signed in:** {st.session_state.user.get('name') or st.session_state.user.get('email')} ")
        if st.sidebar.button("Sign out"):
            SessionManager.logout()
            st.experimental_rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Sessions")
    sess = st.session_state.get('sessions', {})
    if sess:
        for sid, s in sess.items():
            if st.sidebar.button(s.get('title', sid)):
                st.session_state.current_session = s
                st.experimental_rerun()
    else:
        st.sidebar.write("No sessions yet")

    if st.sidebar.button("➕ New session"):
        SessionManager.create_chat_session()
        st.experimental_rerun()

# app_streamlit.py - modular MedLinkAI Streamlit UI
import streamlit as st
import os
from pathlib import Path
import sys

# Ensure repo root is on path so local backend imports (if ever needed) resolve
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from frontend.auth.session_manager import SessionManager
from frontend.components.auth_pages import show_login_page
from frontend.components.sidebar import show_sidebar
from frontend.components.analysis_form import show_analysis_form
from frontend.components.footer import show_footer
from frontend.config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON


st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="wide")

SessionManager.init_session()

st.title("MedLinkAI — Multimodal Healthcare RAG")
st.caption("Informational only. Not medical advice.")

# Show top-level greeting / login flow
if not SessionManager.is_authenticated():
    show_login_page()
    show_footer()
    st.stop()

# show greeting and sidebar
user = st.session_state.get('user')
if user:
    st.markdown(f"<div style='text-align: right; color:#2b6cb0;'>👋 Hi, {user.get('name') or user.get('email')}</div>", unsafe_allow_html=True)

show_sidebar()

# Main area: session chooser and chat
if st.session_state.get('current_session'):
    st.header(f"💬 {st.session_state.current_session['title']}")
    # show history
    success, messages = SessionManager.get_session_messages(st.session_state.current_session['id'])
    if success and messages:
        for m in messages:
            if m['role'] == 'user':
                st.info(m['content'])
            else:
                # assistant message may include metadata about the model used
                content = m.get('content', '')
                meta = m.get('meta') or {}
                model_used = meta.get('model')
                if model_used:
                    st.success(content)
                    st.caption(f"Model: {model_used}")
                else:
                    st.success(content)

    # Small helper button to reveal which model was used for the last response (fallback)
    last_model = st.session_state.get('last_model_used')
    if last_model:
        # show a subtle button; clicking reveals the model name
        if st.button("Which model was used?"):
            st.info(f"Model used: {last_model}")
    else:
        # allow the user to query backend stats on demand
        if st.button("Which model was used?"):
            try:
                import requests
                from os import getenv
                backend = getenv('BACKEND_URL', 'http://localhost:8000')
                r = requests.get(f"{backend}/api/stats", timeout=5)
                if r.ok:
                    st.info(f"Model: {r.json().get('embedding_model')}")
                else:
                    st.info("Model information not available")
            except Exception:
                st.info("Model information not available")

    # show form
    show_analysis_form()
else:
    st.markdown(
        f"<div style='text-align:center; padding:30px;'><h1>{APP_ICON} {APP_NAME}</h1><p>{APP_DESCRIPTION}</p><p style='color:#666'>{APP_TAGLINE}</p></div>",
        unsafe_allow_html=True,
    )

show_footer()

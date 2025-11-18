import streamlit as st
import requests
import os
from frontend.auth.session_manager import SessionManager


def _backend_url():
    return os.getenv('BACKEND_URL', 'http://localhost:8000')


def show_analysis_form():
    session = st.session_state.get('current_session')
    if not session:
        st.warning("No active session. Create one from the sidebar.")
        return

    st.subheader("Ask MedLinkAI")
    with st.form('ask_form'):
        mode = st.selectbox('Mode', ['Patient–Doctor', 'Disease & Jargon', 'Image Identification'])
        question = st.text_area('Question', height=120)
        uploaded = st.file_uploader('Attach image (optional)', type=['png', 'jpg', 'jpeg'], accept_multiple_files=False)
        submitted = st.form_submit_button('Send')

        if submitted:
            if not question and uploaded is None:
                st.error('Please provide a question or attach an image')
                return

            # Append user message (include mode metadata)
            SessionManager.append_message(session['id'], 'user', question or '[image upload]', meta={'mode': mode})

            image_doc_id = None
            if uploaded is not None:
                # Save temp file and upload to backend
                files = {'file': (uploaded.name, uploaded.getvalue())}
                metadata = {'mode': mode}
                try:
                    resp = requests.post(f"{_backend_url()}/api/documents/image", files=files, data={'metadata': str(metadata)})
                    if resp.status_code == 200:
                        j = resp.json()
                        image_doc_id = j.get('document_id') or j.get('document_id')
                    else:
                        st.warning(f"Image upload returned {resp.status_code}")
                except Exception as e:
                    st.warning(f"Failed to upload image: {e}")

            # Query backend
            payload = {'question': question, 'max_results': 3, 'mode': mode}
            try:
                r = requests.post(f"{_backend_url()}/api/query", json=payload, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    answer = data.get('answer') or data.get('response') or ''
                    st.success('Answer received')

                    # Try to determine which model was used. Prefer per-response field, else fall back to /api/stats
                    model_name = None
                    if isinstance(data, dict):
                        model_name = data.get('model') or data.get('model_used') or data.get('model_name')

                    if not model_name:
                        try:
                            s = requests.get(f"{_backend_url()}/api/stats", timeout=5)
                            if s.ok:
                                stats = s.json()
                                # backend may report embedding model; use that as a proxy
                                model_name = stats.get('embedding_model') or stats.get('llm_model') or stats.get('model')
                        except Exception:
                            model_name = None

                    # store last model used in session state for the UI
                    if model_name:
                        st.session_state['last_model_used'] = model_name

                    # Append assistant message with optional model metadata so the UI can display it inline
                    meta = {'model': model_name} if model_name else None
                    SessionManager.append_message(session['id'], 'assistant', answer, meta=meta)
                else:
                    st.error(f"Query failed: {r.status_code} {r.text}")
            except Exception as e:
                st.error(f"Query request failed: {e}")

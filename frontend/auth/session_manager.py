import streamlit as st
import time
import hashlib


class SessionManager:
    @staticmethod
    def init_session():
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'sessions' not in st.session_state:
            st.session_state.sessions = {}
        if 'current_session' not in st.session_state:
            st.session_state.current_session = None

    @staticmethod
    def is_authenticated():
        return bool(st.session_state.get('user'))

    @staticmethod
    def login(email: str, name: str = ''):
        st.session_state.user = {'email': email, 'name': name}

    @staticmethod
    def logout():
        st.session_state.user = None

    @staticmethod
    def create_chat_session(title: str = None):
        # create a simple in-memory session
        title = title or f"Session {len(st.session_state.sessions)+1}"
        sid = hashlib.sha1(f"{title}-{time.time()}".encode()).hexdigest()[:8]
        session = {'id': sid, 'title': title, 'messages': []}
        st.session_state.sessions[sid] = session
        st.session_state.current_session = session
        return True, session

    @staticmethod
    def get_session_messages(session_id: str):
        s = st.session_state.sessions.get(session_id)
        if not s:
            return False, []
        return True, s.get('messages', [])

    @staticmethod
    def append_message(session_id: str, role: str, content: str, meta: dict = None):
        """Append a message to the in-memory session. Optionally include a meta dict.

        meta is stored under the message key 'meta' and can include model, mode, or other info.
        """
        s = st.session_state.sessions.get(session_id)
        if not s:
            return False
        msg = {'role': role, 'content': content}
        if meta:
            msg['meta'] = meta
        s.setdefault('messages', []).append(msg)
        return True

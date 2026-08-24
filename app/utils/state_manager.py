import streamlit as st


def init_session_state():
    defaults = {
        "app_mode": "upload",
        "learner_level": "초등 저학년",
        "analysis": None,
        "selected_problem_types": [],
        "quiz": None,
        "answers": {},
        "grading": None,
        "uploaded_filename": "",
        "material_bytes": None,
        "material_mime": None,
        "kindergarten_examples": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()

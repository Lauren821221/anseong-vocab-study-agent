import streamlit as st

DEFAULTS = {
    "analysis": None,
    "recommendation": None,
    "questions": [],
    "answers": {},
    "grade": None,
    "selected_types": [],
    "material_title": "학습 자료",
    "material_id": None,
    "upload_nonce": 0,
    "source_mode": "📁 사진 파일 업로드",
    "recommended_for_signature": None,
}

def init_state():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v.copy() if isinstance(v, (dict, list)) else v

def reset_main():
    nonce = st.session_state.get("upload_nonce", 0) + 1
    for k, v in DEFAULTS.items():
        st.session_state[k] = v.copy() if isinstance(v, (dict, list)) else v
    st.session_state["upload_nonce"] = nonce

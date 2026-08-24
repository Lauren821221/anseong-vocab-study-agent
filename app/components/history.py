import requests
import streamlit as st

from utils.state_manager import reset_session_state
from config import get_api_base_url


API_BASE_URL = get_api_base_url()


def fetch_history():
    try:
        response = requests.get(f"{API_BASE_URL}/history/", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def render_history_ui():
    st.subheader("📚 학습 이력")

    history = fetch_history()

    if not history:
        st.info("저장된 학습 이력이 없습니다.")
        return

    for item in history:
        with st.container(border=True):
            st.markdown(f"**{item['learner_level']} | {item['created_at']}**")
            st.caption(
                f"자료: {item.get('source_name') or '-'} · "
                f"점수: {item.get('score', 0)}/{item.get('total', 0)}"
            )

            weak_words = item.get("weak_words", [])
            if weak_words:
                st.write("보완 단어:", ", ".join(weak_words[:8]))

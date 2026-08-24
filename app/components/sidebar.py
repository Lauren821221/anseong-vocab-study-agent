import streamlit as st
from components.history import render_history_ui


LEVELS = [
    "유치원",
    "초등 저학년",
    "초등 고학년",
    "중학생",
    "고등학생",
    "성인",
]


def render_sidebar():
    with st.sidebar:
        st.header("⚙️ 학습 설정")

        st.selectbox(
            "학습자 수준",
            LEVELS,
            key="learner_level",
        )

        st.caption(
            "유치원은 예문 중심, 초등 이상은 "
            "문제 추천 → 출제 → 채점 → 복습 추천으로 진행됩니다."
        )

        st.divider()
        render_history_ui()

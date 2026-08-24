import requests, streamlit as st
from config import API_BASE_URL

def render_history():
    st.markdown("#### 🕘 학습 이력")
    try:
        r=requests.get(f"{API_BASE_URL}/history",timeout=10); r.raise_for_status()
        rows=r.json()
    except Exception:
        st.caption("학습 이력을 불러오지 못했습니다.")
        return
    if not rows:
        st.caption("아직 저장된 학습 이력이 없어요.")
    for x in rows[:20]:
        label=f"{x['learner_level']} · {x['title']}"
        with st.expander(label):
            st.caption(f"{x['difficulty']} · {x['question_count']}문제 · {x['score']}점")
            if x.get("result",{}).get("weak_words"):
                st.write("복습 단어:", ", ".join(x["result"]["weak_words"]))

import requests, streamlit as st
from config import API_BASE_URL
from utils.state_manager import init_state, reset_main
from components.history import render_history

st.set_page_config(page_title="안성맞춤 수준별 단어 스터디",page_icon="📚",layout="wide")
init_state()

st.markdown("""
<style>
.block-container{max-width:1100px;padding-top:2rem}.stButton>button{border-radius:10px}
div[data-testid="stFileUploader"]{border-radius:14px}
</style>""",unsafe_allow_html=True)

with st.sidebar:
    st.title("📚 안성맞춤 단어 스터디")
    st.caption("수준과 학습 자료를 분석해 나에게 맞는 영어 문제를 만듭니다.")
    if st.button("＋ 새 학습 시작",use_container_width=True):
        reset_main(); st.rerun()
    render_history()

st.title("안성맞춤 수준별 단어 스터디 에이전트")
st.caption("공부한 자료를 올리면 AI가 분석하고, 원하는 유형과 난이도로 문제를 만들어 드려요.")

levels=["유치원","초등 저학년","초등 고학년","중학생","고등학생","성인"]
difficulties=["쉬움","보통","어려움","TOSEL 수준","TOEFL Junior 수준","TOEFL 수준","최선어학원 유형"]

st.subheader("① 공부한 자료 올리기")
st.caption("사진 파일을 선택하거나 카메라로 바로 촬영하세요. 새 학습 시작 시 메인 화면만 초기화되고 학습 이력은 유지됩니다.")
c1,c2=st.columns(2)
with c1:
    upload=st.file_uploader("사진 파일 선택",type=["jpg","jpeg","png","webp","heic","heif"],key=f"file_{st.session_state.upload_nonce}")
with c2:
    camera=st.camera_input("카메라로 촬영",key=f"cam_{st.session_state.upload_nonce}")
image=camera or upload

st.subheader("② 학습자 수준 · 문제 난이도 · 문제 수")
a,b,c=st.columns(3)
with a: level=st.selectbox("학습자 수준",levels,index=1)
with b: difficulty=st.selectbox("문제 난이도 / 시험 유형",difficulties,index=1)
with c: count=st.selectbox("문제 수",[5,10,15,20,25,30],index=1,format_func=lambda x:f"{x}문제")

if image and st.button("🔎 자료 분석하고 AI 추천 받기",type="primary"):
    try:
        with st.spinner("사진에서 학습 단어를 분석하고 있어요..."):
            files={"file":(image.name,image.getvalue(),image.type or "image/jpeg")}
            r=requests.post(f"{API_BASE_URL}/analyze",files=files,data={"learner_level":level},timeout=120); r.raise_for_status()
            st.session_state.analysis=r.json()
            st.session_state.material_title=st.session_state.analysis.get("title","학습 자료")
            rr=requests.post(f"{API_BASE_URL}/recommend",json={"learner_level":level,"difficulty":difficulty,"words":st.session_state.analysis.get("words",[])},timeout=60); rr.raise_for_status()
            st.session_state.recommendation=rr.json()
            st.session_state.selected_types=st.session_state.recommendation.get("recommended_type_ids",[])
            st.session_state.questions=[]; st.session_state.grade=None
    except Exception as e: st.error(f"자료 분석 오류: {e}")

if st.session_state.analysis:
    st.success(f"자료 분석 완료: {st.session_state.analysis.get('summary','')}")
    words=st.session_state.analysis.get("words",[])
    edited=st.text_area("추출된 단어 확인/편집 (쉼표로 구분)",value=", ".join(x.get("word","") for x in words),height=90)
    edited_words=[x.strip() for x in edited.split(",") if x.strip()]
    st.session_state.analysis["words"]=[{"word":x,"meaning":""} for x in edited_words]

    st.subheader("③ AI 에이전트 추천 → 사용자가 최종 선택")
    rec=st.session_state.recommendation or {}
    st.info("✨ "+rec.get("reason","학습 수준과 난이도를 기준으로 추천했습니다."))
    try:
        qt=requests.get(f"{API_BASE_URL}/question-types",timeout=10).json()
    except Exception: qt=[]
    selected=[]
    cols=st.columns(2)
    rec_ids=set(rec.get("recommended_type_ids",[]))
    for i,t in enumerate(qt):
        with cols[i%2]:
            checked=st.checkbox(f"{t['name']} — {t['description']}",value=t["id"] in rec_ids,key=f"type_{t['id']}")
            if checked: selected.append(t["id"])
    st.session_state.selected_types=selected

    if level=="유치원":
        st.caption("💡 유치원은 뜻·그림/상황·짧은 예문 중심을 우선 추천하며, 생성 문제도 짧고 구체적인 문장으로 조정합니다.")

    if st.button("선택한 조건으로 문제 만들기 →",type="primary",disabled=not selected):
        try:
            with st.spinner(f"{count}문제를 만들고 있어요..."):
                payload={"learner_level":level,"difficulty":difficulty,"words":st.session_state.analysis["words"],"type_ids":selected,"question_count":count}
                r=requests.post(f"{API_BASE_URL}/quiz",json=payload,timeout=180); r.raise_for_status()
                st.session_state.questions=r.json().get("questions",[])
                st.session_state.answers={}; st.session_state.grade=None
        except Exception as e: st.error(f"문제 생성 오류: {e}")

if st.session_state.questions:
    st.divider(); st.subheader("④ 문제 풀기")
    with st.form("quiz_form"):
        answers={}
        for q in st.session_state.questions:
            st.markdown(f"**{q['id']}. [{q.get('type_name','')}] {q['question']}**")
            if q.get("format")=="short_answer":
                answers[str(q["id"])]=st.text_input("답",key=f"a_{q['id']}")
            else:
                choices=q.get("choices",[])
                answers[str(q["id"])]=st.radio("정답 선택",["선택 안 함"]+choices,index=0,key=f"a_{q['id']}")
            st.write("")
        submitted=st.form_submit_button("채점하기",type="primary")
    if submitted:
        answers={k:("" if v=="선택 안 함" else v) for k,v in answers.items()}
        try:
            with st.spinner("채점하고 복습 단어를 분석하고 있어요..."):
                payload={"learner_level":level,"difficulty":difficulty,"title":st.session_state.material_title,
                         "words":st.session_state.analysis["words"],"type_ids":st.session_state.selected_types,
                         "questions":st.session_state.questions,"answers":answers}
                r=requests.post(f"{API_BASE_URL}/grade",json=payload,timeout=180); r.raise_for_status()
                st.session_state.grade=r.json()
        except Exception as e: st.error(f"채점 오류: {e}")

if st.session_state.grade:
    g=st.session_state.grade
    st.divider(); st.subheader("⑤ 채점 · 복습")
    st.metric("점수",f"{g['score']}점",f"{g['correct_count']}/{g['total']} 정답")
    if g.get("weak_words"):
        st.warning("더 공부하면 좋은 단어: "+", ".join(g["weak_words"]))
    if g.get("review"):
        st.markdown("#### 함께 공부하면 좋은 단어")
        for x in g["review"]:
            st.markdown(f"**{x['word']}** — {x.get('why','')}\n\n→ {', '.join(x.get('related_words',[]))}")
    with st.expander("문항별 정답 확인"):
        qmap={q["id"]:q for q in st.session_state.questions}
        for d in g.get("details",[]):
            q=qmap.get(d["id"],{})
            st.markdown(f"{'✅' if d['correct'] else '❌'} **{d['id']}번** · 내 답: {d.get('user_answer','')} · 정답/예시: {d.get('answer','')}")
            if q.get("explanation"): st.caption(q["explanation"])

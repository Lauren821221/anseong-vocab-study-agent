import requests
import streamlit as st

from components.sidebar import render_sidebar
from utils.state_manager import init_session_state, reset_session_state
from config import get_api_base_url


API_BASE_URL = get_api_base_url()


def analyze_material(file_obj):
    files = {
        "file": (
            file_obj.name,
            file_obj.getvalue(),
            file_obj.type or "image/jpeg",
        )
    }
    data = {"learner_level": st.session_state.learner_level}

    response = requests.post(
        f"{API_BASE_URL}/study/analyze",
        files=files,
        data=data,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def generate_quiz():
    analysis = st.session_state.analysis
    payload = {
        "learner_level": st.session_state.learner_level,
        "analysis": analysis,
        "problem_types": st.session_state.selected_problem_types,
        "question_count": st.session_state.question_count,
    }

    response = requests.post(
        f"{API_BASE_URL}/study/generate",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    st.session_state.quiz = response.json()
    st.session_state.answers = {}
    st.session_state.app_mode = "quiz"
    st.rerun()


def grade_quiz():
    payload = {
        "learner_level": st.session_state.learner_level,
        "quiz": st.session_state.quiz,
        "answers": st.session_state.answers,
        "source_name": st.session_state.uploaded_filename,
    }

    response = requests.post(
        f"{API_BASE_URL}/study/grade",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    st.session_state.grading = response.json()
    st.session_state.app_mode = "result"
    st.rerun()


def generate_kindergarten_examples():
    payload = {
        "learner_level": "유치원",
        "analysis": st.session_state.analysis,
    }

    response = requests.post(
        f"{API_BASE_URL}/study/kindergarten-examples",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    st.session_state.kindergarten_examples = response.json()
    st.session_state.app_mode = "kindergarten"
    st.rerun()


def render_upload():
    st.header("1️⃣ 공부한 영어 자료 올리기")

    st.write(
        "단어장, 교재, 프린트, 노트 등을 사진으로 올리거나 "
        "카메라로 바로 촬영할 수 있어요."
    )

    tab1, tab2 = st.tabs(["📁 파일 업로드", "📷 카메라 촬영"])

    with tab1:
        uploaded = st.file_uploader(
            "이미지 파일 선택",
            type=["png", "jpg", "jpeg", "webp"],
            key="file_upload",
        )

    with tab2:
        camera = st.camera_input("공부한 자료 촬영")

    file_obj = camera or uploaded

    if file_obj:
        st.image(file_obj, caption="업로드한 학습 자료", width=500)

        if st.button("🔍 자료 분석하기", type="primary"):
            try:
                with st.spinner("자료에서 단어와 학습 내용을 분석하고 있어요..."):
                    result = analyze_material(file_obj)

                st.session_state.analysis = result
                st.session_state.uploaded_filename = getattr(
                    file_obj, "name", "camera.jpg"
                )
                st.session_state.app_mode = "proposal"
                st.rerun()

            except requests.RequestException as e:
                st.error("분석 서버 호출에 실패했습니다.")
                st.exception(e)


def render_proposal():
    analysis = st.session_state.analysis or {}

    st.header("2️⃣ 분석 결과와 추천 학습 방식")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("추출된 핵심 단어")
        words = analysis.get("extracted_words", [])
        if words:
            st.write(", ".join(words))
        else:
            st.info("추출된 단어가 없습니다.")

        st.subheader("자료 난이도 분석")
        st.write(analysis.get("difficulty_summary", "-"))

    with col2:
        st.subheader("에이전트의 추천")
        st.write(analysis.get("study_advice", "-"))

    if st.session_state.learner_level == "유치원":
        st.info(
            "유치원 학습자는 시험보다 문장 노출이 중요하므로 "
            "같은 단어를 기초·기본·중급·상급 예문으로 확장해 드려요."
        )

        if st.button("🌱 수준별 예문 만들기", type="primary"):
            try:
                with st.spinner("수준별 예문을 만들고 있어요..."):
                    generate_kindergarten_examples()
            except requests.RequestException as e:
                st.error("예문 생성에 실패했습니다.")
                st.exception(e)
        return

    recommendations = analysis.get("recommended_problem_types", [])

    if recommendations:
        option_map = {
            item["id"]: f"{item['name']} — {item['reason']}"
            for item in recommendations
        }

        default_ids = [item["id"] for item in recommendations[:3]]

        selected = st.multiselect(
            "출제할 문제 유형을 선택하세요.",
            options=list(option_map.keys()),
            default=default_ids,
            format_func=lambda x: option_map[x],
        )

        st.session_state.selected_problem_types = selected
    else:
        st.warning("추천 문제 유형이 없습니다.")
        st.session_state.selected_problem_types = []

    st.slider(
        "문제 수",
        min_value=5,
        max_value=25,
        value=10,
        step=5,
        key="question_count",
    )

    if st.button(
        "✏️ 선택한 유형으로 문제 만들기",
        type="primary",
        disabled=not st.session_state.selected_problem_types,
    ):
        try:
            with st.spinner("학습 자료와 수준을 반영해 문제를 만들고 있어요..."):
                generate_quiz()
        except requests.RequestException as e:
            st.error("문제 생성에 실패했습니다.")
            st.exception(e)


def render_quiz():
    quiz = st.session_state.quiz or {}
    questions = quiz.get("questions", [])

    st.header("3️⃣ 안성맞춤 영어 문제")

    st.caption(
        f"수준: {st.session_state.learner_level} · "
        f"총 {len(questions)}문제"
    )

    for idx, q in enumerate(questions, start=1):
        with st.container(border=True):
            st.markdown(f"**{idx}. {q['question']}**")

            qid = q["id"]
            qtype = q.get("question_type", "multiple_choice")

            if qtype == "multiple_choice":
                st.session_state.answers[qid] = st.radio(
                    "답 선택",
                    q.get("options", []),
                    key=f"answer_{qid}",
                    index=None,
                )
            else:
                st.session_state.answers[qid] = st.text_input(
                    "답 입력",
                    key=f"answer_{qid}",
                )

            if q.get("target_word"):
                st.caption(f"학습 단어: {q['target_word']}")

    if st.button("✅ 채점하기", type="primary"):
        unanswered = [
            q["id"]
            for q in questions
            if not st.session_state.answers.get(q["id"])
        ]

        if unanswered:
            st.warning("아직 답하지 않은 문제가 있어요.")
            return

        try:
            with st.spinner("채점하고 복습 단어를 분석하고 있어요..."):
                grade_quiz()
        except requests.RequestException as e:
            st.error("채점 요청에 실패했습니다.")
            st.exception(e)


def render_result():
    result = st.session_state.grading or {}

    st.header("4️⃣ 채점 및 맞춤 복습")

    score = result.get("score", 0)
    total = result.get("total", 0)
    accuracy = result.get("accuracy", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("점수", f"{score}/{total}")
    c2.metric("정답률", f"{accuracy}%")
    c3.metric("학습 수준", st.session_state.learner_level)

    st.subheader("문제별 결과")
    for item in result.get("details", []):
        icon = "✅" if item.get("correct") else "❌"
        with st.container(border=True):
            st.write(
                f"{icon} {item.get('question', '')}"
            )
            st.caption(
                f"내 답: {item.get('user_answer', '-')} | "
                f"정답: {item.get('correct_answer', '-')}"
            )
            if item.get("explanation"):
                st.write("해설:", item["explanation"])

    st.subheader("🎯 더 공부해야 할 단어")
    weak_words = result.get("weak_words", [])
    if weak_words:
        st.write(", ".join(weak_words))
    else:
        st.success("이번 문제에서는 특별히 보완할 단어가 없어요.")

    st.subheader("🔗 같이 공부하면 좋은 단어")
    related = result.get("related_words", [])
    for item in related:
        with st.container(border=True):
            st.markdown(
                f"**{item.get('word')}** — {item.get('meaning', '')}"
            )
            st.caption(
                f"함께 공부하는 이유: {item.get('reason', '')}"
            )

    if result.get("study_plan"):
        st.subheader("📌 다음 학습 제안")
        st.write(result["study_plan"])

    if st.button("🔄 새로운 자료로 다시 공부하기"):
        reset_session_state()
        st.rerun()


def render_kindergarten():
    data = st.session_state.kindergarten_examples or {}

    st.header("🌱 유치원 수준별 예문")

    for word_item in data.get("words", []):
        with st.container(border=True):
            st.subheader(
                f"{word_item.get('word')} "
                f"({word_item.get('meaning', '')})"
            )

            examples = word_item.get("examples", {})
            for level in ["기초", "기본", "중급", "상급"]:
                ex = examples.get(level)
                if ex:
                    st.markdown(f"**{level}**")
                    st.write(ex.get("english", ""))
                    st.caption(ex.get("korean", ""))

    if data.get("parent_tip"):
        st.info(data["parent_tip"])

    if st.button("🔄 다른 자료 공부하기"):
        reset_session_state()
        st.rerun()


def main():
    st.set_page_config(
        page_title="안성맞춤 수준별 단어 스터디 에이전트",
        page_icon="📚",
        layout="wide",
    )

    init_session_state()
    render_sidebar()

    st.title("📚 안성맞춤 수준별 단어 스터디 에이전트")
    st.write(
        "내가 공부한 영어 자료를 올리면, "
        "학습자 수준에 맞는 문제를 제안하고 출제·채점한 뒤 "
        "다음에 공부할 단어까지 추천해주는 AI 학습 에이전트입니다."
    )

    mode = st.session_state.app_mode

    if mode == "upload":
        render_upload()
    elif mode == "proposal":
        render_proposal()
    elif mode == "quiz":
        render_quiz()
    elif mode == "result":
        render_result()
    elif mode == "kindergarten":
        render_kindergarten()


if __name__ == "__main__":
    main()

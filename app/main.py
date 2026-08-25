import requests
import streamlit as st

from config import API_BASE_URL
from utils.state_manager import init_state, reset_main


st.set_page_config(
    page_title="안성맞춤 수준별 단어 스터디",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_state()


# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

.block-container{
    max-width:1100px;
    padding-top:1.6rem;
    padding-bottom:4rem;
}

div[data-testid="stTabs"] button{
    font-weight:700;
}

div[data-testid="stFileUploader"]{
    border-radius:14px;
}

.stButton>button{
    border-radius:10px;
}

.study-card{
    border:1px solid #e3e6eb;
    border-radius:14px;
    padding:14px;
    margin:8px 0;
    background:#fff;
}

.review-card{
    border:1px solid #e3e6eb;
    border-radius:14px;
    padding:16px;
    margin:10px 0;
}

.small-muted{
    font-size:.86rem;
    color:#6b7280;
}

@media(max-width:700px){
    .block-container{
        padding-left:1rem;
        padding-right:1rem;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# API
# =========================================================

def api_get(path, timeout=20):

    r = requests.get(
        f"{API_BASE_URL}{path}",
        timeout=timeout
    )

    r.raise_for_status()

    return r.json()


def api_post(path, **kwargs):

    r = requests.post(
        f"{API_BASE_URL}{path}",
        **kwargs
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# QUIZ DISPLAY HELPERS
# =========================================================

def underline_word(text, highlight_word):
    """
    Streamlit radio 선택지에서 특정 단어를 눈에 띄게 표시한다.

    HTML을 radio 내부에서 직접 렌더링할 수 없기 때문에
    Unicode combining low line을 사용한다.

    서버로 전달되는 실제 답은 원문을 사용하므로
    채점에는 영향을 주지 않는다.
    """

    if not text:
        return ""

    if not highlight_word:
        return text

    if highlight_word not in text:
        return text

    underlined = "".join(
        char + "\u0332"
        for char in highlight_word
    )

    return text.replace(
        highlight_word,
        underlined,
        1
    )


def choice_display_text(choice):
    """
    신규 구조:
    {
        "text": "...",
        "highlight_word": "..."
    }

    구버전 문자열 choice도 지원한다.
    """

    if isinstance(choice, str):
        return choice

    if not isinstance(choice, dict):
        return str(choice)

    text = choice.get("text", "")
    highlight_word = choice.get(
        "highlight_word",
        ""
    )

    return underline_word(
        text,
        highlight_word
    )


def original_choice_text(choice):
    """
    화면 표시용 밑줄 문자열이 아니라
    서버 채점용 원래 문자열을 반환한다.
    """

    if isinstance(choice, str):
        return choice

    if isinstance(choice, dict):
        return choice.get("text", "")

    return str(choice)


def display_question_text(question):
    """
    문제 본문에 highlight_word가 있는 경우
    문제 본문에서도 강조한다.
    """

    text = question.get(
        "question",
        ""
    )

    highlight_word = question.get(
        "highlight_word",
        ""
    )

    return underline_word(
        text,
        highlight_word
    )


# =========================================================
# HEADER
# =========================================================

st.title(
    "📚 안성맞춤 수준별 단어 스터디 에이전트"
)

st.caption(
    "공부한 자료를 분석하고, 학습자에게 맞는 문제를 "
    "추천·출제·채점한 뒤 맞춤 복습까지 연결합니다."
)


tab_test, tab_history = st.tabs(
    [
        "📝 테스트 문제 만들기",
        "📊 학습 이력"
    ]
)


# =========================================================
# TEST TAB
# =========================================================

with tab_test:

    top1, top2 = st.columns(
        [5, 1]
    )

    with top2:

        if st.button(
            "＋ 새 학습",
            use_container_width=True
        ):

            reset_main()

            st.rerun()


    # =====================================================
    # 1. SOURCE
    # =====================================================

    st.subheader(
        "① 학습 자료 선택"
    )

    st.caption(
        "사진 업로드, 카메라 촬영, 기존 학습자료 중 "
        "하나를 선택하세요. 카메라는 촬영 방식을 "
        "선택했을 때만 실행됩니다."
    )


    source_mode = st.radio(
        "자료 선택 방식",
        [
            "📁 사진 파일 업로드",
            "📷 카메라로 촬영",
            "📚 기존 학습자료 불러오기"
        ],
        horizontal=True,
        key="source_mode",
    )


    image = None


    # -----------------------------------------------------
    # FILE UPLOAD
    # -----------------------------------------------------

    if source_mode == "📁 사진 파일 업로드":

        image = st.file_uploader(
            "영어 학습자료 사진",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
                "heic",
                "heif"
            ],
            key=f"file_{st.session_state.upload_nonce}",
            help=(
                "iPhone에서는 사진 보관함 또는 "
                "파일에서 선택할 수 있습니다."
            ),
        )


    # -----------------------------------------------------
    # CAMERA
    # -----------------------------------------------------

    elif source_mode == "📷 카메라로 촬영":

        st.info(
            "📷 촬영을 선택했기 때문에 카메라를 표시합니다. "
            "iPhone Safari에서는 카메라 권한을 허용해주세요."
        )

        image = st.camera_input(
            "학습자료 촬영",
            key=f"cam_{st.session_state.upload_nonce}",
        )


    # -----------------------------------------------------
    # EXISTING MATERIAL
    # -----------------------------------------------------

    else:

        try:

            materials = api_get(
                "/materials"
            )

        except Exception as e:

            materials = []

            st.error(
                f"기존 학습자료를 불러오지 못했습니다: {e}"
            )


        if materials:

            options = {
                (
                    f"{m['title']} · "
                    f"{len(m.get('words', []))}단어 · "
                    f"{m.get('created_at','')[:10]}"
                ): m

                for m in materials
            }


            selected_label = st.selectbox(
                "저장된 학습자료",
                list(options.keys())
            )


            if st.button(
                "📚 이 자료 불러오기",
                type="primary"
            ):

                m = options[
                    selected_label
                ]

                st.session_state.analysis = {
                    "title": m["title"],
                    "summary": m.get(
                        "summary",
                        ""
                    ),
                    "words": m.get(
                        "words",
                        []
                    ),
                    "material_id": m["id"],
                }

                st.session_state.material_id = (
                    m["id"]
                )

                st.session_state.material_title = (
                    m["title"]
                )

                st.session_state.recommendation = None
                st.session_state.questions = []
                st.session_state.grade = None

                st.success(
                    "기존 학습자료를 불러왔습니다."
                )

        else:

            st.caption(
                "아직 저장된 학습자료가 없습니다."
            )


    # =====================================================
    # ANALYZE IMAGE
    # =====================================================

    if image is not None:

        if st.button(
            "🔎 AI 자료 분석",
            type="primary"
        ):

            try:

                with st.spinner(
                    "사진에서 학습 단어를 분석하고 있어요..."
                ):

                    files = {
                        "file": (
                            getattr(
                                image,
                                "name",
                                "camera.jpg"
                            ),
                            image.getvalue(),
                            getattr(
                                image,
                                "type",
                                None
                            ) or "image/jpeg"
                        )
                    }


                    result = api_post(
                        "/analyze",

                        files=files,

                        data={
                            "learner_level":
                                "초등 저학년"
                        },

                        timeout=180,
                    )


                    st.session_state.analysis = (
                        result
                    )

                    st.session_state.material_id = (
                        result.get(
                            "material_id"
                        )
                    )

                    st.session_state.material_title = (
                        result.get(
                            "title",
                            "학습 자료"
                        )
                    )

                    st.session_state.recommendation = None
                    st.session_state.questions = []
                    st.session_state.grade = None


            except Exception as e:

                st.error(
                    f"자료 분석 오류: {e}"
                )


    # =====================================================
    # 2. ANALYSIS / WORD EDIT
    # =====================================================

    if st.session_state.analysis:

        st.divider()

        st.subheader(
            "② AI 자료 분석 → 단어 확인·수정"
        )


        analysis = (
            st.session_state.analysis
        )


        st.success(
            f"자료 분석 완료 · "
            f"{analysis.get('summary','')}"
        )


        words = analysis.get(
            "words",
            []
        )


        current = ", ".join(
            x.get("word", "")
            for x in words
            if x.get("word")
        )


        edited = st.text_area(
            "추출된 단어 확인/수정",
            value=current,
            height=100,
            help=(
                "쉼표로 구분해 단어를 "
                "삭제하거나 추가할 수 있습니다."
            ),
        )


        edited_words = [
            x.strip()
            for x in edited.split(",")
            if x.strip()
        ]


        old_meanings = {
            x.get("word", ""):
                x.get("meaning", "")
            for x in words
        }


        st.session_state.analysis[
            "words"
        ] = [

            {
                "word": x,
                "meaning":
                    old_meanings.get(
                        x,
                        ""
                    )
            }

            for x in edited_words
        ]


        st.caption(
            f"현재 학습 단어: "
            f"{len(edited_words)}개"
        )


        # =================================================
        # 3. CONDITIONS
        # =================================================

        st.subheader(
            "③ 학습 조건 선택"
        )


        levels = [
            "유치원",
            "초등 저학년",
            "초등 고학년",
            "중학생",
            "고등학생",
            "성인"
        ]


        difficulties = [
            "쉬움",
            "보통",
            "어려움",
            "TOSEL 수준",
            "TOEFL Junior 수준",
            "TOEFL 수준",
            "최선어학원 유형"
        ]


        school_modes = [
            "적용 안 함",
            "중학교 내신",
            "고등학교 내신"
        ]


        c1, c2, c3 = st.columns(3)


        with c1:

            level = st.selectbox(
                "학습자 수준",
                levels,
                index=1
            )


        with c2:

            difficulty = st.selectbox(
                "난이도 / 시험유형",
                difficulties,
                index=1
            )


        with c3:

            school_mode = st.selectbox(
                "내신 준비형",
                school_modes,
                index=0
            )


        signature = (
            level,
            difficulty,
            school_mode,
            tuple(edited_words)
        )


        # =================================================
        # AI RECOMMEND
        # =================================================

        if st.button(
            "✨ AI 문제유형 추천",
            type="primary"
        ):

            try:

                with st.spinner(
                    "학습 조건에 맞는 문제유형을 "
                    "고르고 있어요..."
                ):

                    rec = api_post(
                        "/recommend",

                        json={
                            "learner_level":
                                level,

                            "difficulty":
                                difficulty,

                            "school_mode":
                                school_mode,

                            "words":
                                st.session_state.analysis[
                                    "words"
                                ],
                        },

                        timeout=60,
                    )


                    st.session_state.recommendation = (
                        rec
                    )

                    st.session_state.selected_types = (
                        rec.get(
                            "recommended_type_ids",
                            []
                        )
                    )

                    st.session_state[
                        "recommended_for_signature"
                    ] = signature


            except Exception as e:

                st.error(
                    f"문제유형 추천 오류: {e}"
                )


        # =================================================
        # 4. QUESTION TYPES
        # =================================================

        if st.session_state.recommendation:

            st.subheader(
                "④ AI 추천 문제유형 → "
                "사용자가 추가/삭제"
            )


            st.info(
                "✨ "
                + st.session_state.recommendation.get(
                    "reason",
                    "학습 조건에 맞는 유형을 추천했습니다."
                )
            )


            try:

                all_types = api_get(
                    "/question-types"
                )

            except Exception as e:

                all_types = []

                st.error(
                    f"문제유형 목록 오류: {e}"
                )


            recommended = set(
                st.session_state.recommendation.get(
                    "recommended_type_ids",
                    []
                )
            )


            selected = []

            cols = st.columns(2)


            for i, t in enumerate(
                all_types
            ):

                with cols[i % 2]:

                    checked = st.checkbox(
                        (
                            f"{t['name']} — "
                            f"{t['description']}"
                        ),

                        value=(
                            t["id"]
                            in recommended
                        ),

                        key=(
                            f"qtype_"
                            f"{t['id']}_"
                            f"{st.session_state.upload_nonce}"
                        ),
                    )


                    if checked:

                        selected.append(
                            t["id"]
                        )


            st.session_state.selected_types = (
                selected
            )


            # =================================================
            # 5. QUESTION COUNT
            # =================================================

            st.subheader(
                "⑤ 문제 수 선택 → 문제 출제"
            )


            q1, q2 = st.columns(
                [1, 2]
            )


            with q1:

                count = st.selectbox(
                    "문제 수",
                    [
                        5,
                        10,
                        15,
                        20,
                        25,
                        30
                    ],
                    index=1,
                    format_func=lambda x:
                        f"{x}문제"
                )


            with q2:

                st.write("")
                st.write("")

                make_quiz = st.button(
                    "선택한 조건으로 문제 만들기 →",
                    type="primary",
                    use_container_width=True,
                    disabled=not selected,
                )


            if make_quiz:

                try:

                    with st.spinner(
                        f"{count}문제를 만들고 있어요..."
                    ):

                        result = api_post(
                            "/quiz",

                            json={
                                "learner_level":
                                    level,

                                "difficulty":
                                    difficulty,

                                "school_mode":
                                    school_mode,

                                "words":
                                    st.session_state.analysis[
                                        "words"
                                    ],

                                "type_ids":
                                    selected,

                                "question_count":
                                    count,
                            },

                            timeout=240,
                        )


                        st.session_state.questions = (
                            result.get(
                                "questions",
                                []
                            )
                        )


                        st.session_state.grade = None


                        st.session_state[
                            "active_level"
                        ] = level


                        st.session_state[
                            "active_difficulty"
                        ] = difficulty


                        st.session_state[
                            "active_school_mode"
                        ] = school_mode


                except Exception as e:

                    st.error(
                        f"문제 생성 오류: {e}"
                    )


    # =====================================================
    # 6. QUIZ
    # =====================================================

    if st.session_state.questions:

        st.divider()

        st.subheader(
            "⑥ 문제 풀기"
        )


        with st.form(
            "quiz_form"
        ):

            answers = {}


            for q in (
                st.session_state.questions
            ):

                question_text = (
                    display_question_text(q)
                )


                st.markdown(
                    f"**{q['id']}. "
                    f"[{q.get('type_name','')}] "
                    f"{question_text}**"
                )


                # -----------------------------------------
                # SHORT ANSWER
                # -----------------------------------------

                if (
                    q.get("format")
                    == "short_answer"
                ):

                    answers[
                        str(q["id"])
                    ] = st.text_input(
                        "답",
                        key=(
                            f"answer_{q['id']}"
                        )
                    )


                # -----------------------------------------
                # MULTIPLE CHOICE
                # -----------------------------------------

                else:

                    raw_choices = q.get(
                        "choices",
                        []
                    )


                    display_choices = [
                        choice_display_text(c)
                        for c in raw_choices
                    ]


                    selected_display = (
                        st.radio(
                            "정답 선택",

                            [
                                "선택 안 함"
                            ]
                            + display_choices,

                            index=0,

                            key=(
                                f"answer_{q['id']}"
                            ),
                        )
                    )


                    if (
                        selected_display
                        == "선택 안 함"
                    ):

                        answers[
                            str(q["id"])
                        ] = ""


                    else:

                        try:

                            selected_index = (
                                display_choices.index(
                                    selected_display
                                )
                            )


                            original_choice = (
                                raw_choices[
                                    selected_index
                                ]
                            )


                            answers[
                                str(q["id"])
                            ] = (
                                original_choice_text(
                                    original_choice
                                )
                            )


                        except (
                            ValueError,
                            IndexError
                        ):

                            answers[
                                str(q["id"])
                            ] = ""


                st.write("")


            submitted = (
                st.form_submit_button(
                    "채점하기",
                    type="primary"
                )
            )


        # =================================================
        # GRADE
        # =================================================

        if submitted:

            try:

                with st.spinner(
                    "채점하고 맞춤 복습 카드를 "
                    "만들고 있어요..."
                ):

                    result = api_post(
                        "/grade",

                        json={
                            "learner_level":
                                st.session_state.get(
                                    "active_level",
                                    "초등 저학년"
                                ),

                            "difficulty":
                                st.session_state.get(
                                    "active_difficulty",
                                    "보통"
                                ),

                            "school_mode":
                                st.session_state.get(
                                    "active_school_mode",
                                    "적용 안 함"
                                ),

                            "title":
                                st.session_state.material_title,

                            "words":
                                st.session_state.analysis[
                                    "words"
                                ],

                            "type_ids":
                                st.session_state.selected_types,

                            "questions":
                                st.session_state.questions,

                            "answers":
                                answers,
                        },

                        timeout=240,
                    )


                    st.session_state.grade = (
                        result
                    )


            except Exception as e:

                st.error(
                    f"채점 오류: {e}"
                )


    # =====================================================
    # 7. RESULT
    # =====================================================

    if st.session_state.grade:

        st.divider()

        st.subheader(
            "⑦ 채점 결과 · 맞춤 복습"
        )


        g = (
            st.session_state.grade
        )


        m1, m2 = st.columns(2)


        m1.metric(
            "점수",
            f"{g['score']}점"
        )


        m2.metric(
            "정답",
            (
                f"{g['correct_count']} "
                f"/ {g['total']}"
            )
        )


        if g.get(
            "weak_words"
        ):

            st.warning(
                "🎯 취약 단어: "
                + ", ".join(
                    g["weak_words"]
                )
            )

        else:

            st.success(
                "🎉 이번 테스트에서 "
                "취약 단어가 발견되지 않았어요."
            )


        # -------------------------------------------------
        # REVIEW
        # -------------------------------------------------

        if g.get(
            "review"
        ):

            st.markdown(
                "#### 🌱 함께 공부하면 "
                "좋은 단어와 예문"
            )


            for x in g[
                "review"
            ]:

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"### "
                        f"{x.get('word','')}"
                    )


                    c1, c2 = (
                        st.columns(2)
                    )


                    with c1:

                        st.write(
                            "**유의어:**",
                            ", ".join(
                                x.get(
                                    "synonyms",
                                    []
                                )
                            ) or "-"
                        )

                        st.write(
                            "**반의어:**",
                            ", ".join(
                                x.get(
                                    "antonyms",
                                    []
                                )
                            ) or "-"
                        )


                    with c2:

                        st.write(
                            "**관련어:**",
                            ", ".join(
                                x.get(
                                    "related_words",
                                    []
                                )
                            ) or "-"
                        )

                        st.write(
                            "**Collocation/표현:**",
                            ", ".join(
                                x.get(
                                    "collocations",
                                    []
                                )
                            ) or "-"
                        )


                    st.write(
                        "**예문**"
                    )


                    for ex in x.get(
                        "examples",
                        []
                    ):

                        st.write(
                            "• " + ex
                        )


                    if x.get(
                        "tip"
                    ):

                        st.caption(
                            "학습 팁: "
                            + x["tip"]
                        )


        # -------------------------------------------------
        # QUESTION DETAILS
        # -------------------------------------------------

        with st.expander(
            "문항별 정답 확인"
        ):

            qmap = {
                q["id"]: q
                for q in
                st.session_state.questions
            }


            for d in g.get(
                "details",
                []
            ):

                q = qmap.get(
                    d["id"],
                    {}
                )


                st.markdown(
                    f"{'✅' if d['correct'] else '❌'} "
                    f"**{d['id']}번** "
                    f"· 내 답: "
                    f"{d.get('user_answer','')} "
                    f"· 정답/예시: "
                    f"{d.get('answer','')}"
                )


                if q.get(
                    "explanation"
                ):

                    st.caption(
                        q[
                            "explanation"
                        ]
                    )


# =========================================================
# HISTORY TAB
# =========================================================

with tab_history:

    st.subheader(
        "📊 학습 이력"
    )

    st.caption(
        "과거 테스트의 조건, 점수, 취약 단어와 "
        "맞춤 복습 내용을 다시 확인할 수 있습니다."
    )


    try:

        histories = api_get(
            "/history"
        )

    except Exception as e:

        histories = []

        st.error(
            f"학습 이력을 불러오지 못했습니다: {e}"
        )


    if not histories:

        st.info(
            "아직 저장된 학습 이력이 없습니다."
        )


    else:

        for h in histories:

            label = (
                f"{h['title']} · "
                f"{h['learner_level']} · "
                f"{h['difficulty']} · "
                f"{h.get('school_mode','적용 안 함')} · "
                f"{h['score']}점"
            )


            with st.expander(
                label
            ):

                st.write(
                    f"**문제 수:** "
                    f"{h['question_count']}문제"
                )


                weak = (
                    h.get(
                        "result",
                        {}
                    )
                    .get(
                        "weak_words",
                        []
                    )
                )


                st.write(
                    "**취약 단어:**",
                    (
                        ", ".join(weak)
                        if weak
                        else "없음"
                    )
                )


                review = (
                    h.get(
                        "result",
                        {}
                    )
                    .get(
                        "review",
                        []
                    )
                )


                if review:

                    st.markdown(
                        "**맞춤 복습**"
                    )


                    for x in review:

                        st.markdown(
                            f"- **"
                            f"{x.get('word','')}"
                            f"**"
                        )


                        st.caption(
                            f"유의어: "
                            f"{', '.join(x.get('synonyms', [])) or '-'} / "
                            f"반의어: "
                            f"{', '.join(x.get('antonyms', [])) or '-'} / "
                            f"관련어: "
                            f"{', '.join(x.get('related_words', [])) or '-'}"
                        )


                        for ex in x.get(
                            "examples",
                            []
                        ):

                            st.write(
                                "  • " + ex
                            )


                if st.button(
                    "이 학습자료로 다시 테스트 만들기",
                    key=f"reuse_{h['id']}"
                ):

                    st.session_state.analysis = {
                        "title":
                            h["title"],

                        "summary":
                            "학습 이력에서 불러온 자료",

                        "words":
                            h.get(
                                "words",
                                []
                            ),
                    }


                    st.session_state.material_title = (
                        h["title"]
                    )

                    st.session_state.recommendation = None
                    st.session_state.questions = []
                    st.session_state.grade = None


                    st.success(
                        "자료를 불러왔습니다. "
                        "상단의 ‘테스트 문제 만들기’ 탭에서 "
                        "새 조건을 선택하세요."
                    )

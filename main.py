import os
import io
import json
import random
import re
import copy
from datetime import datetime

import requests
import streamlit as st
from PIL import Image, ImageOps
from google import genai
from google.genai import types

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None

try:
    from app.utils.state_manager import init_state, reset_main
except Exception:
    def init_state():
        defaults = {
            "upload_nonce": 0, "analysis": None, "material_id": None,
            "material_title": "", "recommendation": None, "questions": [],
            "grade": None, "selected_types": [], "thread_id": None,
            "agent_evidence": None,
        }
        for k, v in defaults.items():
            st.session_state.setdefault(k, v)

    def reset_main():
        st.session_state.upload_nonce = st.session_state.get("upload_nonce", 0) + 1
        for k, v in {
            "analysis": None, "material_id": None, "material_title": "",
            "recommendation": None, "questions": [], "grade": None,
            "selected_types": [], "agent_evidence": None,
        }.items():
            st.session_state[k] = v

st.set_page_config(
    page_title="안성맞춤 수준별 영어 스터디",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Home menu cards: equal-height columns/cards
st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3))
      > div[data-testid="stColumn"] {
        align-self: stretch;
    }
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3))
      > div[data-testid="stColumn"] > div {
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* HOME: Vocabulary / Grammar / History cards — same size */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] div[style*="border:1px solid"],
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] div[style*="border: 1px solid"] {
    min-height: 258px !important;
    height: 258px !important;
    box-sizing: border-box !important;
}
</style>
""", unsafe_allow_html=True)

LEVELS = ["유치원", "초등 저학년", "초등 고학년", "중학생", "고등학생", "성인"]

init_state()

for key, default in {
    "grammar_analysis": None,
    "grammar_recommendation": None,
    "grammar_questions": [],
    "grammar_grade": None,
    "grammar_selected_types": [],
    "grammar_upload_nonce": 0,
    "reading_analysis": None,
    "reading_questions": [],
    "reading_grade": None,
    "reading_selected_types": [],
    "reading_upload_nonce": 0,
    "local_history": [],
    "learner_name": "",
    "history_loaded": False,
}.items():
    st.session_state.setdefault(key, default)

st.markdown("""
<style>
.block-container{max-width:1100px;padding-top:1.6rem;padding-bottom:4rem}
div[data-testid="stTabs"] button{font-weight:700}
div[data-testid="stFileUploader"]{border-radius:14px}
.stButton>button{border-radius:10px}
.review-card{border:1px solid #e3e6eb;border-radius:14px;padding:16px;margin:10px 0;background:#fff}
.small-muted{font-size:.86rem;color:#6b7280}
@media(max-width:700px){.block-container{padding-left:1rem;padding-right:1rem}}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------
def api_get(path, timeout=20):
    r = requests.get(f"{API_BASE_URL}{path}", timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(path, **kwargs):
    r = requests.post(f"{API_BASE_URL}{path}", **kwargs)
    r.raise_for_status()
    return r.json()


def extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.replace("```json", "", 1).replace("```", "")
    try:
        return json.loads(text)
    except Exception:
        start_obj, end_obj = text.find("{"), text.rfind("}")
        start_arr, end_arr = text.find("["), text.rfind("]")
        if start_arr >= 0 and end_arr > start_arr:
            return json.loads(text[start_arr:end_arr + 1])
        if start_obj >= 0 and end_obj > start_obj:
            return json.loads(text[start_obj:end_obj + 1])
        raise


def _gemini_json_once(prompt, image_bytes=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [prompt]
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return extract_json(response.text)




def gemini_json(prompt, image_bytes=None, max_retries=3):
    """Gemini JSON call with retry only for temporary service errors.
    Hard quota exhaustion (free-tier daily/request quota) is NOT retried.
    """
    import time
    last_error = None

    for attempt in range(max_retries):
        try:
            return _gemini_json_once(prompt, image_bytes)
        except Exception as e:
            last_error = e
            msg = str(e)
            low = msg.lower()

            hard_quota = (
                "quota exceeded" in low
                or "free_tier_requests" in low
                or "generatecontent_free_tier_requests" in low
                or "perdayperprojectpermodel" in low
            )
            if hard_quota:
                raise

            transient = (
                "503" in msg
                or "UNAVAILABLE" in msg
                or "high demand" in low
                or (
                    ("429" in msg or "RESOURCE_EXHAUSTED" in msg)
                    and ("retry" in low or "rate" in low)
                )
            )

            if not transient or attempt == max_retries - 1:
                raise

            time.sleep(2 * (attempt + 1))

    raise last_error
def is_gemini_hard_quota_error(error):
    msg = str(error).lower()
    return (
        "quota exceeded" in msg
        or "free_tier_requests" in msg
        or "generatecontent_free_tier_requests" in msg
        or "perdayperprojectpermodel" in msg
    )


def show_ai_error(prefix, error):
    """Show a concise message instead of raw Gemini quota payload."""
    if is_gemini_hard_quota_error(error):
        st.error(
            f"{prefix}: 오늘 사용할 수 있는 Gemini 무료 API 요청 한도를 모두 사용했습니다. "
            "무료 한도가 초기화된 뒤 다시 시도하거나, Gemini API의 결제/쿼터를 늘려야 합니다."
        )
    else:
        st.error(f"{prefix}: {error}")



def combine_uploaded_images(uploaded_images, max_width=1400, max_total_height=10000):
    """여러 이미지를 기존 /analyze 1회 호출에 사용할 수 있도록 세로로 합친다."""
    images = []
    for uploaded in uploaded_images:
        raw = uploaded.getvalue()
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, max(1, int(img.height * ratio))))
        images.append(img)

    if not images:
        return None

    width = max(i.width for i in images)
    heights = [int(i.height * (width / i.width)) if i.width != width else i.height for i in images]
    total_height = sum(heights)

    if total_height > max_total_height:
        scale = max_total_height / total_height
        width = max(600, int(width * scale))
        resized, heights = [], []
        for img in images:
            ratio = width / img.width
            r = img.resize((width, max(1, int(img.height * ratio))))
            resized.append(r)
            heights.append(r.height)
        images = resized
    else:
        resized = []
        for img in images:
            if img.width != width:
                ratio = width / img.width
                img = img.resize((width, max(1, int(img.height * ratio))))
            resized.append(img)
        images = resized
        heights = [x.height for x in images]

    canvas = Image.new("RGB", (width, sum(heights)), "white")
    y = 0
    for img in images:
        canvas.paste(img, (0, y))
        y += img.height

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()



def choice_value(choice):
    """Return the canonical answer value for a choice."""
    if isinstance(choice, dict):
        for key in ("text", "label", "value", "option"):
            value = choice.get(key)
            if value is not None:
                return str(value)
        return str(choice)
    return str(choice)


def underline_text(text, target):
    """Visually underline target inside text using combining underline characters."""
    text = str(text or "")
    target = str(target or "").strip()
    if not target:
        return text

    pattern = re.compile(re.escape(target), re.IGNORECASE)

    def _u(match):
        return "".join(ch + "\u0332" for ch in match.group(0))

    return pattern.sub(_u, text)


def choice_display(choice):
    """Human-friendly option text; hides dict structure and applies underline."""
    if isinstance(choice, dict):
        text = choice_value(choice)
        highlight = (
            choice.get("highlight_word")
            or choice.get("highlight")
            or choice.get("underline")
            or ""
        )
        return underline_text(text, highlight)
    return str(choice)


def clean_question_text(value):
    """Remove accidental outer Markdown bold markers returned by an LLM."""
    s = str(value or "").strip()
    while s.startswith("**") and s.endswith("**") and len(s) >= 4:
        s = s[2:-2].strip()
    return s




def answer_text_from_question(q):
    """Resolve answer metadata to the actual correct choice text."""
    choices = list(q.get("choices", []) or [])
    raw = q.get("answer", q.get("correct_answer", q.get("correct_index")))

    if isinstance(raw, dict):
        return choice_value(raw)

    if isinstance(raw, int):
        if 0 <= raw < len(choices):
            return choice_value(choices[raw])
        if 1 <= raw <= len(choices):
            return choice_value(choices[raw - 1])

    if isinstance(raw, str):
        s = raw.strip()
        values = [choice_value(c) for c in choices]
        if s in values:
            return s

        letters = [chr(65 + i) for i in range(len(values))]
        if s.upper() in letters:
            return values[letters.index(s.upper())]

        if s.isdigit():
            n = int(s)
            if 0 <= n < len(values):
                return values[n]
            if 1 <= n <= len(values):
                return values[n - 1]

    return ""


def ensure_five_choices(questions, study_kind="English"):
    """Ensure every MCQ has exactly five unique choices.
    All invalid items are repaired in ONE Gemini request to minimize quota usage.
    """
    questions = list(questions or [])
    invalid_indexes = []

    for i, q in enumerate(questions):
        if q.get("format") == "short_answer":
            continue

        choices = list(q.get("choices", []) or [])
        values = [choice_value(c).strip() for c in choices]
        answer_text = answer_text_from_question(q).strip()

        valid = (
            len(choices) == 5
            and len(set(values)) == 5
            and answer_text
            and answer_text in values
        )

        if valid:
            q["answer"] = values.index(answer_text)
            q.pop("correct_answer", None)
            q.pop("correct_index", None)
        else:
            invalid_indexes.append(i)

    if not invalid_indexes:
        return questions

    invalid_items = [questions[i] for i in invalid_indexes]

    prompt = f"""
You are repairing {study_kind} multiple-choice quiz items.

Repair ALL supplied items in ONE response.

STRICT REQUIREMENTS:
1. Preserve each item's tested concept, meaning, type, and similar difficulty.
2. Each multiple-choice item must have exactly FIVE answer choices.
3. All five choices must be UNIQUE and plausible.
4. Exactly ONE choice must be correct.
5. The correct answer MUST appear among the five choices.
6. Use "answer" as a ZERO-BASED integer index: A=0, B=1, C=2, D=3, E=4.
7. Do NOT include "선택 안 함", "정답 없음", "none of the above", or equivalents.
8. Preserve existing highlight metadata for ordinary underline questions.
9. For Error Detection / 오류 찾기, do NOT underline or visually reveal the incorrect target.
   Use "highlight_word": "" and do not say "underlined".
10. Return ONLY a JSON array with the SAME number of items and SAME order.

ITEMS:
{json.dumps(invalid_items, ensure_ascii=False)}
"""

    repaired = gemini_json(prompt)
    if isinstance(repaired, dict):
        repaired = repaired.get("questions", repaired.get("items", []))

    if not isinstance(repaired, list) or len(repaired) != len(invalid_indexes):
        raise ValueError("5지선다 보정 결과 형식이 올바르지 않습니다. 다시 문제 만들기를 눌러주세요.")

    result = list(questions)
    for idx, fixed in zip(invalid_indexes, repaired):
        if isinstance(fixed, dict):
            result[idx] = fixed

    # Normalize answer metadata after the batch repair.
    for q in result:
        if q.get("format") == "short_answer":
            continue
        choices = list(q.get("choices", []) or [])
        values = [choice_value(c).strip() for c in choices]
        answer_text = answer_text_from_question(q).strip()
        if answer_text and answer_text in values:
            q["answer"] = values.index(answer_text)
            q.pop("correct_answer", None)
            q.pop("correct_index", None)

    return result


def validate_five_choice_questions(questions):
    """Final safety gate for five-choice multiple-choice questions."""
    bad_ids = []

    for i, q in enumerate(questions):
        if q.get("format") == "short_answer":
            continue

        choices = list(q.get("choices", []) or [])
        values = [choice_value(c).strip() for c in choices]
        answer_text = answer_text_from_question(q).strip()

        banned = {"선택 안 함", "정답 없음", "none of the above"}

        if (
            len(choices) != 5
            or any(not v for v in values)
            or len(set(values)) != 5
            or any(v.lower() in {x.lower() for x in banned} for v in values)
            or not answer_text
            or answer_text not in values
        ):
            bad_ids.append(q.get("id", i + 1))

    if bad_ids:
        raise ValueError(
            "일부 객관식 문항을 정상적인 5지선다로 구성하지 못했습니다. "
            f"문항: {', '.join(map(str, bad_ids))}. 문제 만들기를 다시 눌러주세요."
        )

    return questions


def grammar_answer_text(q):
    """Resolve a grammar answer into actual choice text."""
    choices = list(q.get("choices", []) or [])
    raw = q.get("answer", q.get("correct_answer", q.get("correct_index")))

    if isinstance(raw, dict):
        return choice_value(raw)

    if isinstance(raw, int):
        if 0 <= raw < len(choices):
            return choice_value(choices[raw])
        if 1 <= raw <= len(choices):
            return choice_value(choices[raw - 1])

    if isinstance(raw, str):
        s = raw.strip()
        values = [choice_value(c) for c in choices]
        if s in values:
            return s
        if s.upper() in ["A", "B", "C", "D"]:
            i = ord(s.upper()) - 65
            if 0 <= i < len(values):
                return values[i]
        if s.isdigit():
            n = int(s)
            if 0 <= n < len(values):
                return values[n]
            if 1 <= n <= len(values):
                return values[n - 1]

    return ""


def grammar_question_is_valid(q):
    """Validate grammar question integrity before showing it."""
    if not isinstance(q, dict):
        return False

    if q.get("format") == "short_answer":
        return bool(str(q.get("answer", "")).strip())

    choices = list(q.get("choices", []) or [])
    if len(choices) != 5:
        return False

    values = [choice_value(c).strip() for c in choices]
    if any(not v for v in values):
        return False
    if len(set(values)) != 4:
        return False

    answer_text = grammar_answer_text(q).strip()
    if not answer_text or answer_text not in values:
        return False

    if grammar_question_needs_highlight(q):
        highlight = (
            q.get("highlight_word")
            or q.get("highlight_phrase")
            or q.get("underlined_text")
            or q.get("target_phrase")
            or q.get("underline")
            or ""
        )
        if not highlight or str(highlight) not in str(q.get("question", "")):
            return False

    return True


def repair_invalid_grammar_questions(questions):
    """Regenerate only broken grammar items."""
    bad_indexes = [i for i, q in enumerate(questions) if not grammar_question_is_valid(q)]
    if not bad_indexes:
        return questions

    bad_items = [questions[i] for i in bad_indexes]

    prompt = f"""
Repair the following invalid English grammar quiz items.

STRICT RULES:
1. Keep the same grammar concept and similar difficulty.
2. Multiple-choice items must have exactly 5 UNIQUE choices.
3. There must be exactly ONE best answer.
4. The correct answer MUST appear among the four choices.
5. "answer" MUST be a ZERO-BASED integer index: A=0, B=1, C=2, D=3, E=4.
6. If the instruction mentions 밑줄 친/밑줄친/underlined, include "highlight_word".
7. "highlight_word" must be an exact substring of "question".
8. Return ONLY a JSON array, same item count, same order.

INVALID ITEMS:
{json.dumps(bad_items, ensure_ascii=False)}
"""
    repaired = gemini_json(prompt)
    if isinstance(repaired, dict):
        repaired = repaired.get("questions", repaired.get("items", []))

    if not isinstance(repaired, list) or len(repaired) != len(bad_indexes):
        return questions

    result = list(questions)
    for i, fixed in zip(bad_indexes, repaired):
        result[i] = fixed

    return result


def validate_grammar_questions_or_raise(questions):
    """Final safety gate: do not expose broken grammar questions."""
    bad_ids = [
        q.get("id", i + 1)
        for i, q in enumerate(questions)
        if not grammar_question_is_valid(q)
    ]
    if bad_ids:
        raise ValueError(
            "일부 문항의 정답/보기 구성이 올바르지 않아 출제를 중단했습니다. "
            f"문항: {', '.join(map(str, bad_ids))}. 문제 만들기를 다시 눌러주세요."
        )
    return questions


def grammar_is_error_detection(q):
    """Error Detection 문항인지 판별."""
    type_name = str(q.get("type_name", "")).lower()
    question = str(q.get("question", "")).lower()
    return (
        "error detection" in type_name
        or "오류 찾기" in type_name
        or "어법 오류" in type_name
        or ("identify" in question and "incorrect" in question)
        or "문법적으로 적절하지 않은" in question
    )


def grammar_question_display(q):
    """문법 문제 표시. Error Detection에서는 정답을 노출할 수 있는 밑줄을 표시하지 않는다."""
    q_text = clean_question_text(q.get("question", ""))
    if grammar_is_error_detection(q):
        return q_text
    highlight = (
        q.get("highlight_word")
        or q.get("highlight_phrase")
        or q.get("underlined_text")
        or q.get("target_phrase")
        or q.get("underline")
        or ""
    )
    return underline_text(q_text, highlight)


def grammar_question_needs_highlight(q):
    """밑줄이 실제로 필요한 문제인지 판별. Error Detection은 정답 노출 방지를 위해 제외."""
    if grammar_is_error_detection(q):
        return False
    q_text = str(q.get("question", ""))
    markers = ["밑줄", "underlined", "underline", "밑줄 친", "밑줄친"]
    return any(m.lower() in q_text.lower() for m in markers)


def repair_missing_grammar_highlights(questions):
    """Ask Gemini once to add missing highlight metadata without changing answers."""
    missing = [
        q for q in questions
        if grammar_question_needs_highlight(q)
        and not (
            q.get("highlight_word")
            or q.get("highlight_phrase")
            or q.get("underlined_text")
            or q.get("target_phrase")
            or q.get("underline")
        )
    ]
    if not missing:
        return questions

    prompt = f"""
You are repairing grammar quiz JSON.

Some questions explicitly mention an underlined word or phrase, but the underline metadata is missing.
For EVERY question that refers to an underlined part:
1. Add "highlight_word" containing the EXACT word or phrase already present in the question text.
2. The exact highlight_word MUST occur verbatim inside "question".
3. Do NOT change the correct answer, choices, question type, topic, or meaning.
4. If needed, minimally rewrite only the sentence portion so the target phrase is explicitly present.
5. Questions that do not need an underline should use "highlight_word": "".

Return the FULL question array only.

QUESTIONS:
{json.dumps(questions, ensure_ascii=False)}
"""
    repaired = gemini_json(prompt)
    if isinstance(repaired, dict):
        repaired = repaired.get("questions", questions)
    return repaired if isinstance(repaired, list) else questions


def radio_choice(label, choices, key):
    """Render answer choices without an artificial '선택 안 함' option."""
    choices = list(choices or [])
    option_ids = list(range(len(choices)))

    selected = st.radio(
        label,
        option_ids,
        index=None,
        key=key,
        format_func=lambda i: choice_display(choices[i]),
    )

    if selected is None:
        return ""
    return choice_value(choices[selected])


def balance_answer_positions(questions):
    """정답 위치를 보기 개수에 맞춰 가능한 균등하게 재배치한다.
    5지선다는 A~E에 분산하고, 기존 데이터도 안전하게 처리한다.
    """
    rng = random.SystemRandom()
    grouped = {}

    for q in questions:
        choices = list(q.get("choices", []) or [])
        if q.get("format") == "short_answer" or len(choices) < 2:
            continue

        answer_key = next(
            (k for k in ("answer", "correct_answer", "correct_index") if k in q),
            None,
        )
        if not answer_key:
            continue

        grouped.setdefault(len(choices), []).append((q, answer_key))

    for choice_count, objective in grouped.items():
        targets = list(range(choice_count)) * ((len(objective) + choice_count - 1) // choice_count)
        targets = targets[:len(objective)]
        rng.shuffle(targets)

        for (q, key), target in zip(objective, targets):
            choices = list(q["choices"])
            raw = q[key]
            old_index = None
            representation = "text"

            if isinstance(raw, int):
                if 0 <= raw < choice_count:
                    old_index, representation = raw, "zero"
                elif 1 <= raw <= choice_count:
                    old_index, representation = raw - 1, "one"

            elif isinstance(raw, dict):
                raw_value = choice_value(raw)
                values = [choice_value(c) for c in choices]
                if raw_value in values:
                    old_index, representation = values.index(raw_value), "dict"

            elif isinstance(raw, str):
                s = raw.strip()
                values = [choice_value(c) for c in choices]

                if s in values:
                    old_index, representation = values.index(s), "text"
                elif len(s) == 1 and s.upper() in [chr(65+i) for i in range(choice_count)]:
                    old_index, representation = ord(s.upper()) - 65, "letter"
                elif s.isdigit():
                    n = int(s)
                    if 0 <= n < choice_count:
                        old_index, representation = n, "zero_str"
                    elif 1 <= n <= choice_count:
                        old_index, representation = n - 1, "one_str"

            if old_index is None:
                continue

            correct = choices[old_index]
            distractors = [c for i, c in enumerate(choices) if i != old_index]
            rng.shuffle(distractors)

            new_choices = distractors[:]
            new_choices.insert(target, correct)
            q["choices"] = new_choices

            if representation in ("text", "dict"):
                q[key] = choice_value(correct)
            elif representation == "letter":
                q[key] = chr(65 + target)
            elif representation == "zero":
                q[key] = target
            elif representation == "one":
                q[key] = target + 1
            elif representation == "zero_str":
                q[key] = str(target)
            elif representation == "one_str":
                q[key] = str(target + 1)

    return questions

# ---------------------------------------------------------------------
# 브라우저 localStorage: 사용자 이름 + 사용자별 학습 이력
# ---------------------------------------------------------------------
STORAGE_USER = "anseong_english_study_user"
STORAGE_HISTORY_PREFIX = "anseong_english_study_history_"


def js_get(key, widget_key):
    if streamlit_js_eval is None:
        return None
    return streamlit_js_eval(
        js_expressions=f"localStorage.getItem({json.dumps(key)})",
        key=widget_key,
    )


def js_set(key, value, widget_key):
    if streamlit_js_eval is None:
        return None
    payload = json.dumps(json.dumps(value, ensure_ascii=False))
    return streamlit_js_eval(
        js_expressions=f"localStorage.setItem({json.dumps(key)}, {payload}); true",
        key=widget_key,
    )


def js_remove(key, widget_key):
    if streamlit_js_eval is None:
        return None
    return streamlit_js_eval(
        js_expressions=f"localStorage.removeItem({json.dumps(key)}); true",
        key=widget_key,
    )


def load_browser_profile():
    if st.session_state.history_loaded:
        return
    if streamlit_js_eval is None:
        st.session_state.history_loaded = True
        return
    name = js_get(STORAGE_USER, "load_user_once")
    if name is None:
        return
    st.session_state.learner_name = name or ""
    if name:
        raw = js_get(STORAGE_HISTORY_PREFIX + name, "load_history_once")
        if raw is None:
            return
        try:
            st.session_state.local_history = json.loads(raw) if raw else []
        except Exception:
            st.session_state.local_history = []
    st.session_state.history_loaded = True


def save_profile_name(name):
    st.session_state.learner_name = name.strip()
    st.session_state.local_history = []
    st.session_state.history_loaded = True
    if streamlit_js_eval is not None:
        js_set(STORAGE_USER, st.session_state.learner_name, f"save_user_{random.randint(1,999999)}")
        raw = js_get(STORAGE_HISTORY_PREFIX + st.session_state.learner_name, f"read_new_{random.randint(1,999999)}")
        if raw:
            try:
                st.session_state.local_history = json.loads(raw)
            except Exception:
                pass


def append_history(item):
    if not st.session_state.learner_name:
        return
    item = dict(item)
    item["created_at"] = datetime.now().isoformat(timespec="seconds")
    st.session_state.local_history.insert(0, item)
    if streamlit_js_eval is not None:
        js_set(
            STORAGE_HISTORY_PREFIX + st.session_state.learner_name,
            st.session_state.local_history,
            f"save_hist_{random.randint(1,999999)}",
        )


load_browser_profile()

# ---------------------------------------------------------------------
# 홈
# ---------------------------------------------------------------------
st.title("📚 안성맞춤 수준별 영어 스터디 에이전트")
st.caption("Vocabulary · Grammar · Reading을 학습하고, AI 문제 생성·채점·복습·학습 이력까지 연결합니다.")



if "active_page" not in st.session_state:
    st.session_state.active_page = "home"

active_page = st.session_state.active_page

# One-page navigation: no URL links, no new page/tab.
nav_cols = st.columns(5)
nav_items = [
    ("🏠 홈", "home"),
    ("📘 Vocabulary", "vocab"),
    ("✏️ Grammar", "grammar"),
    ("📖 Reading", "reading"),
    ("📊 학습 이력", "history"),
]
for col, (label, page_key) in zip(nav_cols, nav_items):
    with col:
        if st.button(
            label,
            key=f"top_nav_{page_key}",
            use_container_width=True,
            type="primary" if active_page == page_key else "secondary",
        ):
            st.session_state.active_page = page_key
            st.rerun()

st.markdown(
    """
    <style>
    /* Hide Streamlit heading anchor/link icons */
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* Home cards rendered as real Streamlit buttons so navigation stays in one page */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        white-space: normal;
    }

    .home-card-note {
        color:#8b8f97;
        font-size:14px;
        margin-top:-8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
if active_page == "home":
    st.subheader("👤 사용자 정보")
    st.caption("이름 또는 별칭을 한 번 등록하면 이 브라우저에 저장되며, 학습 이력 화면에서 사용됩니다.")
    c1, c2 = st.columns([3, 1])
    with c1:
        profile_name = st.text_input(
            "이름 또는 별칭",
            value=st.session_state.learner_name,
            placeholder="예: 민준",
            label_visibility="collapsed",
        )
    with c2:
        if st.button("사용자 저장", type="primary", use_container_width=True):
            if profile_name.strip():
                save_profile_name(profile_name)
                st.success("사용자 정보를 저장했습니다.")
            else:
                st.warning("이름 또는 별칭을 입력해주세요.")

    st.divider()

    # Same-page clickable cards
    # 네 학습/이력 카드의 높이와 버튼 위치를 맞춥니다.
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        with st.container(border=True, height=320):
            st.markdown("### 📘 Vocabulary 학습")
            st.markdown(
                '<div style="height:64px; font-size:18px; line-height:1.55;">'
                '기존 단어 학습 흐름을 그대로 유지합니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="height:64px; color:#8b8f97; font-size:15px; line-height:1.5;">'
                '여러 장 사진 분석 · AI 유형 추천 · 10개 유형 · 채점 · 복습 카드'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Vocabulary 학습 열기",
                key="home_card_vocab",
                use_container_width=True,
            ):
                st.session_state.active_page = "vocab"
                st.rerun()

    with c2:
        with st.container(border=True, height=320):
            st.markdown("### ✏️ Grammar 학습")
            st.markdown(
                '<div style="height:64px; font-size:18px; line-height:1.55;">'
                '공부한 문법 자료를 분석해 수준별 문법 문제를 만듭니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="height:64px; color:#8b8f97; font-size:15px; line-height:1.5;">'
                'AI 유형 추천 · TOEFL/Junior/최선/내신 · 취약 문법 복습'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Grammar 학습 열기",
                key="home_card_grammar",
                use_container_width=True,
            ):
                st.session_state.active_page = "grammar"
                st.rerun()

    with c3:
        with st.container(border=True, height=320):
            st.markdown("### 📖 Reading 학습")
            st.markdown(
                '<div style="height:64px; font-size:18px; line-height:1.55;">'
                '읽은 영어원서 페이지를 바탕으로 리딩 문제를 만듭니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="height:64px; color:#8b8f97; font-size:15px; line-height:1.5;">'
                'TOEFL Junior · TOEFL · 최선형 · Main Idea · Inference'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Reading 학습 열기",
                key="home_card_reading",
                use_container_width=True,
            ):
                st.session_state.active_page = "reading"
                st.rerun()

    with c4:
        with st.container(border=True, height=320):
            st.markdown("### 📊 학습 이력")
            st.markdown(
                '<div style="height:64px; font-size:18px; line-height:1.55;">'
                '홈에서 등록한 사용자의 학습 결과만 보여줍니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="height:64px; color:#8b8f97; font-size:15px; line-height:1.5;">'
                'Vocabulary · Grammar · Reading 결과를 현재 브라우저에 저장'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "학습 이력 열기",
                key="home_card_history",
                use_container_width=True,
            ):
                st.session_state.active_page = "history"
                st.rerun()


def normalize_answer_text(value):
    return " ".join(str(value or "").strip().split()).casefold()


def prepare_vocab_grade_questions(questions):
    """Backend 호환용: 객관식 정답을 실제 보기 텍스트로 변환해 전달."""
    prepared = copy.deepcopy(list(questions or []))

    for q in prepared:
        if q.get("format") == "short_answer":
            continue

        correct_text = answer_text_from_question(q).strip()
        if correct_text:
            q["answer"] = correct_text
            q.pop("correct_answer", None)
            q.pop("correct_index", None)

    return prepared


def local_vocab_objective_result(questions, answers):
    """Vocabulary 객관식 로컬 확정 채점."""
    return local_objective_result(questions, answers)


def local_objective_result(questions, answers):
    """객관식 문제는 AI가 아니라 코드로 확정 채점한다."""
    details = []
    correct_count = 0
    objective_count = 0
    has_short_answer = False
    unanswered_ids = []

    for q in questions:
        qid = str(q.get("id", ""))

        if q.get("format") == "short_answer":
            has_short_answer = True
            if not str(answers.get(qid, "") or "").strip():
                unanswered_ids.append(q.get("id"))
            continue

        objective_count += 1
        correct_text = answer_text_from_question(q).strip()
        user_text = str(answers.get(qid, "") or "").strip()

        if not user_text:
            unanswered_ids.append(q.get("id"))

        is_correct = (
            bool(user_text)
            and bool(correct_text)
            and normalize_answer_text(user_text) == normalize_answer_text(correct_text)
        )

        if is_correct:
            correct_count += 1

        details.append({
            "id": q.get("id"),
            "correct": is_correct,
            "user_answer": user_text,
            "answer": correct_text,
        })

    return {
        "all_objective": objective_count > 0 and not has_short_answer,
        "has_short_answer": has_short_answer,
        "objective_count": objective_count,
        "correct_count": correct_count,
        "details": details,
        "score": round((correct_count / objective_count) * 100) if objective_count else 0,
        "unanswered_ids": unanswered_ids,
    }


def merge_local_objective_grade(ai_result, local_check, *, weak_key, review_key):
    """AI 결과의 설명/복습은 유지하되 객관식 점수·정오표는 코드 결과로 확정한다."""
    result = dict(ai_result or {})

    if local_check.get("all_objective"):
        result["correct_count"] = local_check["correct_count"]
        result["total"] = local_check["objective_count"]
        result["score"] = local_check["score"]

        ai_details = {
            str(x.get("id")): x
            for x in result.get("details", [])
            if isinstance(x, dict)
        }

        merged_details = []
        for d in local_check["details"]:
            merged = dict(ai_details.get(str(d.get("id")), {}))
            merged.update(d)
            merged_details.append(merged)

        result["details"] = merged_details

        if local_check["correct_count"] == local_check["objective_count"]:
            result[weak_key] = []
            result[review_key] = []

    return result




# ---------------------------------------------------------------------
# Vocabulary - 기존 서비스 흐름 유지
# ---------------------------------------------------------------------
if active_page == "vocab":
    top1, top2 = st.columns([5, 1])
    with top2:
        if st.button("＋ 새 학습", key="vocab_reset", use_container_width=True):
            reset_main()
            st.rerun()

    st.subheader("① 학습 자료 선택")
    st.caption("학습자 수준을 먼저 선택한 뒤 사진 업로드, 카메라 촬영, 기존 학습자료 중 하나를 선택하세요.")

    levels = LEVELS
    learner_level = st.selectbox(
        "학습자 수준", levels, index=1, key="learner_level",
        help="자료 분석부터 문제 추천·출제·채점까지 동일한 수준을 사용합니다.",
    )

    source_mode = st.radio(
        "자료 선택 방식",
        ["📁 사진 파일 업로드", "📷 카메라로 촬영", "📚 기존 학습자료 불러오기"],
        horizontal=True, key="source_mode",
    )

    analyze_bytes = None
    analyze_name = "material.jpg"

    if source_mode == "📁 사진 파일 업로드":
        images = st.file_uploader(
            "영어 학습자료 사진",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"file_{st.session_state.upload_nonce}",
            help="여러 장을 한 번에 선택할 수 있습니다.",
        )
        if images:
            st.caption(f"선택된 사진: {len(images)}장")
            analyze_bytes = combine_uploaded_images(images)
            analyze_name = "combined_material.jpg"

    elif source_mode == "📷 카메라로 촬영":
        st.caption(
            "📱 휴대폰/태블릿에서는 아래 버튼을 누른 뒤 **카메라/사진 찍기**를 선택하세요. "
            "브라우저 셀프카메라 대신 기기의 기본 카메라가 열리므로 책을 찍기 좋은 **후면 카메라**를 사용할 수 있어요."
        )
        camera_images = st.file_uploader(
            "📷 책 사진 촬영 또는 선택",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"cam_upload_{st.session_state.upload_nonce}",
            help="모바일에서는 '카메라/사진 찍기'를 선택해 후면 카메라로 촬영하세요. 여러 페이지도 선택할 수 있습니다.",
        )
        if camera_images:
            st.caption(f"촬영/선택된 사진: {len(camera_images)}장")
            analyze_bytes = combine_uploaded_images(camera_images)
            analyze_name = "camera_material.jpg"

    else:
        try:
            materials = api_get("/materials")
        except Exception as e:
            materials = []
            st.error(f"기존 학습자료를 불러오지 못했습니다: {e}")
        if materials:
            options = {
                f"{m['title']} · {len(m.get('words', []))}단어 · {m.get('created_at','')[:10]}": m
                for m in materials
            }
            selected_label = st.selectbox("저장된 학습자료", list(options.keys()))
            if st.button("📚 이 자료 불러오기", type="primary"):
                m = options[selected_label]
                st.session_state.analysis = {
                    "title": m["title"], "summary": m.get("summary", ""),
                    "words": m.get("words", []), "material_id": m["id"],
                }
                st.session_state.material_id = m["id"]
                st.session_state.material_title = m["title"]
                st.session_state.recommendation = None
                st.session_state.questions = []
                st.session_state.grade = None
                st.success("기존 학습자료를 불러왔습니다.")
        else:
            st.caption("아직 저장된 학습자료가 없습니다.")

    if analyze_bytes is not None:
        if st.button("🔎 AI 자료 분석", type="primary", key="vocab_analyze"):
            try:
                with st.spinner("사진에서 학습 단어를 분석하고 있어요..."):
                    result = api_post(
                        "/analyze",
                        files={"file": (analyze_name, analyze_bytes, "image/jpeg")},
                        data={"learner_level": learner_level},
                        timeout=180,
                    )
                    st.session_state.analysis = result
                    st.session_state.material_id = result.get("material_id")
                    st.session_state.material_title = result.get("title", "학습 자료")
                    st.session_state.recommendation = None
                    st.session_state.questions = []
                    st.session_state.grade = None
            except Exception as e:
                st.error(f"자료 분석 오류: {e}")

    if st.session_state.analysis:
        st.divider()
        st.subheader("② AI 자료 분석 → 단어 확인·수정")
        analysis = st.session_state.analysis
        st.success(f"자료 분석 완료 · {analysis.get('summary','')}")
        words = analysis.get("words", [])
        current = ", ".join(x.get("word", "") for x in words if x.get("word"))
        edited = st.text_area(
            "추출된 단어 확인/수정", value=current, height=100,
            help="쉼표로 구분해 단어를 삭제하거나 추가할 수 있습니다.",
        )
        edited_words = [x.strip() for x in edited.split(",") if x.strip()]
        old_meanings = {x.get("word", ""): x.get("meaning", "") for x in words}
        st.session_state.analysis["words"] = [
            {"word": x, "meaning": old_meanings.get(x, "")} for x in edited_words
        ]
        st.caption(f"현재 학습 단어: {len(edited_words)}개")

        st.subheader("③ 학습 조건 선택")
        difficulties = ["쉬움", "보통", "어려움", "TOSEL 수준", "TOEFL Junior 수준", "TOEFL 수준", "최선어학원 유형"]
        school_modes = ["적용 안 함", "중학교 내신", "고등학교 내신"]
        level = learner_level
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("학습자 수준", value=level, disabled=True, key="v_level_show")
        with c2:
            difficulty = st.selectbox("난이도 / 시험유형", difficulties, index=1, key="v_diff")
        with c3:
            school_mode = st.selectbox("내신 준비형", school_modes, index=0, key="v_school")

        if st.button("✨ AI 문제유형 추천", type="primary", key="v_recommend"):
            try:
                with st.spinner("학습 조건에 맞는 문제유형을 고르고 있어요..."):
                    payload = {
                        "learner_level": level, "difficulty": difficulty,
                        "school_mode": school_mode, "words": st.session_state.analysis["words"],
                    }
                    if st.session_state.get("thread_id"):
                        payload["thread_id"] = st.session_state.thread_id
                    rec_response = api_post("/recommend", json=payload, timeout=60)
                    rec = rec_response.get("recommendation", rec_response)
                    st.session_state.recommendation = rec
                    st.session_state.selected_types = rec.get("recommended_type_ids", [])
            except Exception as e:
                st.error(f"문제유형 추천 오류: {e}")

        if st.session_state.recommendation:
            st.subheader("④ AI 추천 문제유형 → 사용자가 추가/삭제")
            st.info("✨ " + st.session_state.recommendation.get("reason", "학습 조건에 맞는 유형을 추천했습니다."))
            try:
                all_types = api_get("/question-types")
            except Exception as e:
                all_types = []
                st.error(f"문제유형 목록 오류: {e}")

            recommended = set(st.session_state.recommendation.get("recommended_type_ids", []))
            selected = []
            cols = st.columns(2)
            for i, t in enumerate(all_types[:10]):
                with cols[i % 2]:
                    checked = st.checkbox(
                        f"{t['name']} — {t['description']}",
                        value=t["id"] in recommended,
                        key=f"qtype_{t['id']}_{st.session_state.upload_nonce}",
                    )
                    if checked:
                        selected.append(t["id"])
            st.session_state.selected_types = selected

            st.subheader("⑤ 문제 수 선택 → 문제 출제")
            q1, q2 = st.columns([1, 2])
            with q1:
                count = st.selectbox(
                    "문제 수", [5, 10, 15, 20, 25, 30], index=0,
                    format_func=lambda x: f"{x}문제", key="v_count",
                )
            with q2:
                st.write(""); st.write("")
                make_quiz = st.button(
                    "선택한 조건으로 문제 만들기 →", type="primary",
                    use_container_width=True, disabled=not selected, key="v_make_quiz",
                )

            if make_quiz:
                try:
                    with st.spinner(f"{count}문제를 만들고 있어요..."):
                        payload = {
                            "learner_level": level, "difficulty": difficulty,
                            "school_mode": school_mode, "words": st.session_state.analysis["words"],
                            "type_ids": selected, "question_count": count,
                        }
                        if st.session_state.get("thread_id"):
                            payload["thread_id"] = st.session_state.thread_id
                        result = api_post("/quiz", json=payload, timeout=240)
                        vocab_qs = result.get("questions", [])
                        vocab_qs = ensure_five_choices(vocab_qs, study_kind="Vocabulary")
                        vocab_qs = validate_five_choice_questions(vocab_qs)
                        vocab_qs = balance_answer_positions(vocab_qs)
                        vocab_qs = validate_five_choice_questions(vocab_qs)
                        st.session_state.questions = vocab_qs
                        st.session_state.grade = None
                        st.session_state["active_level"] = level
                        st.session_state["active_difficulty"] = difficulty
                        st.session_state["active_school_mode"] = school_mode
                except Exception as e:
                    show_ai_error("문제 생성 오류", e)

    if st.session_state.questions:
        st.divider()
        st.subheader("⑥ 문제 풀기")
        with st.form("vocab_quiz_form"):
            answers = {}
            for q in st.session_state.questions:
                q_text = clean_question_text(q.get("question", ""))
                st.markdown(f"**{q['id']}. [{q.get('type_name','')}]** {q_text}")
                if q.get("format") == "short_answer":
                    answers[str(q["id"])] = st.text_input("답", key=f"v_answer_{q['id']}")
                else:
                    answers[str(q["id"])] = radio_choice(
                        "정답 선택",
                        q.get("choices", []),
                        key=f"v_answer_{q['id']}",
                    )
                st.write("")
            submitted = st.form_submit_button("답안 제출 및 채점", type="primary")

        if submitted:
            local_check = local_objective_result(
                st.session_state.questions,
                answers,
            )

            if local_check.get("unanswered_ids"):
                st.warning(
                    "아직 답을 선택하지 않은 문항이 있어요: "
                    + ", ".join(map(str, local_check["unanswered_ids"]))
                    + "번. 모든 문제에 답한 뒤 채점해주세요."
                )
            else:
                try:
                    with st.spinner("채점하고 맞춤 복습 카드를 만들고 있어요..."):
                        grade_questions = prepare_vocab_grade_questions(
                            st.session_state.questions
                        )

                        # 전부 맞은 객관식은 AI/backend 호출 없이 코드로 바로 확정.
                        if (
                            local_check.get("all_objective")
                            and local_check["correct_count"] == local_check["objective_count"]
                        ):
                            result = {
                                "score": 100,
                                "correct_count": local_check["correct_count"],
                                "total": local_check["objective_count"],
                                "details": local_check["details"],
                                "weak_words": [],
                                "review": [],
                            }
                        else:
                            grade_payload = {
                                "questions": grade_questions,
                                "answers": answers,
                                "material_id": st.session_state.get("material_id"),
                                "material_title": st.session_state.get("material_title"),
                                "learner_level": st.session_state.get("active_level"),
                                "difficulty": st.session_state.get("active_difficulty"),
                                "school_mode": st.session_state.get("active_school_mode"),
                            }

                            result = None
                            backend_error = None

                            try:
                                result = api_post("/grade", json=grade_payload, timeout=240)
                            except Exception as e1:
                                backend_error = e1
                                try:
                                    # 구버전 backend 계약 호환
                                    legacy_payload = {
                                        "learner_level": st.session_state.get("active_level", "초등 저학년"),
                                        "difficulty": st.session_state.get("active_difficulty", "보통"),
                                        "school_mode": st.session_state.get("active_school_mode", "적용 안 함"),
                                        "title": st.session_state.material_title,
                                        "words": st.session_state.analysis["words"],
                                        "type_ids": st.session_state.selected_types,
                                        "questions": grade_questions,
                                        "answers": answers,
                                    }
                                    result = api_post("/grade", json=legacy_payload, timeout=240)
                                    backend_error = None
                                except Exception as e2:
                                    backend_error = e2

                            # 객관식은 backend가 실패해도 점수 자체는 안전하게 제공.
                            if result is None and local_check.get("all_objective"):
                                result = {
                                    "score": local_check["score"],
                                    "correct_count": local_check["correct_count"],
                                    "total": local_check["objective_count"],
                                    "details": local_check["details"],
                                    "weak_words": [],
                                    "review": [],
                                }
                                st.info(
                                    "점수는 정상적으로 계산했습니다. "
                                    "다만 복습 카드 생성 서버 응답이 없어 이번에는 복습 카드가 생략됐어요."
                                )
                            elif result is None:
                                raise backend_error or RuntimeError("채점 서버 응답이 없습니다.")

                            result = merge_local_objective_grade(
                                result,
                                local_check,
                                weak_key="weak_words",
                                review_key="review",
                            )

                        st.session_state.grade = result
                        append_history({
                            "study_type": "Vocabulary",
                            "test_mode": st.session_state.get("active_difficulty", ""),
                            "question_count": result.get("total", len(st.session_state.questions)),
                            "score": result.get("score", 0),
                            "weak_items": result.get("weak_words", []),
                        })
                except Exception as e:
                    st.error(f"채점 오류: {e}")

    if st.session_state.grade:
        st.divider()
        st.subheader("⑦ 채점 결과 · 맞춤 복습")
        g = st.session_state.grade
        m1, m2 = st.columns(2)
        m1.metric("점수", f"{g.get('score', 0)}점")
        m2.metric("정답", f"{g.get('correct_count', 0)} / {g.get('total', len(st.session_state.questions))}")

        if g.get("weak_words"):
            st.warning("🎯 취약 단어: " + ", ".join(g["weak_words"]))
        else:
            st.success("🎉 이번 테스트에서 취약 단어가 발견되지 않았어요.")

        if g.get("review"):
            st.markdown("#### 🌱 틀린 단어 복습 카드")
            for x in g["review"]:
                with st.container(border=True):
                    st.markdown(f"### {x.get('word','')}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**유의어:**", ", ".join(x.get("synonyms", [])) or "-")
                        st.write("**반의어:**", ", ".join(x.get("antonyms", [])) or "-")
                    with c2:
                        st.write("**관련어:**", ", ".join(x.get("related_words", [])) or "-")
                        st.write("**Collocation/표현:**", ", ".join(x.get("collocations", [])) or "-")
                    st.write("**예문**")
                    for ex in x.get("examples", []):
                        st.write("• " + ex)
                    if x.get("tip"):
                        st.caption("학습 팁: " + x["tip"])

        with st.expander("📋 문항별 정답 확인"):
            qmap = {str(q["id"]): q for q in st.session_state.questions}
            for d in g.get("details", []):
                q = qmap.get(str(d.get("id")), {})
                st.markdown(
                    f"{'✅' if d.get('correct') else '❌'} **{d.get('id')}번** "
                    f"· 내 답: {d.get('user_answer','')} · 정답/예시: {d.get('answer','')}"
                )
                if q.get("explanation"):
                    st.caption(q["explanation"])

        if st.button("🔁 취약 단어로 재시험", type="primary", key="v_retry"):
            st.session_state.grade = None
            st.session_state.recommendation = None
            st.session_state.questions = []
            st.info("취약 단어를 기준으로 다시 AI 문제유형을 추천받아 재시험을 진행해주세요.")


# ---------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------
READING_TYPES = [
    {"id": "main_idea", "name": "Main Idea / Main Title", "description": "글 전체의 중심 생각이나 가장 적절한 제목 찾기"},
    {"id": "topic_sentence", "name": "Topic Sentence", "description": "문단의 핵심 내용을 대표하는 문장 찾기"},
    {"id": "detail", "name": "Factual Information / Detail", "description": "본문에 명시된 세부 정보 확인"},
    {"id": "inference", "name": "Inference", "description": "본문의 단서를 근거로 직접 쓰이지 않은 내용을 추론"},
    {"id": "vocab_context", "name": "Vocabulary in Context", "description": "문맥 속 단어·표현의 의미 추론"},
    {"id": "reference", "name": "Reference", "description": "대명사·지시어가 가리키는 대상 찾기"},
    {"id": "purpose", "name": "Author / Character Purpose", "description": "글쓴이 또는 등장인물의 의도·목적 파악"},
    {"id": "sequence", "name": "Sequence / Plot", "description": "사건의 순서와 전개 관계 파악"},
    {"id": "cause_effect", "name": "Cause & Effect", "description": "원인과 결과의 관계 파악"},
    {"id": "character", "name": "Character / Motivation", "description": "등장인물의 성격·감정·행동 동기 추론"},
    {"id": "summary", "name": "Summary", "description": "핵심 내용을 가장 잘 요약한 선택지 찾기"},
    {"id": "sentence_insertion", "name": "Sentence Insertion / Coherence", "description": "문맥 흐름에 맞는 문장 또는 위치 판단"},
]


def reset_reading():
    st.session_state.reading_upload_nonce = st.session_state.get("reading_upload_nonce", 0) + 1
    for k, v in {
        "reading_analysis": None,
        "reading_questions": [],
        "reading_grade": None,
        "reading_selected_types": [],
    }.items():
        st.session_state[k] = v


if active_page == "reading":
    rc1, rc2 = st.columns([5, 1])
    with rc2:
        if st.button("＋ 새 학습", key="r_reset", use_container_width=True):
            reset_reading()
            st.rerun()

    st.subheader("① 읽은 영어원서 페이지 올리기")
    st.caption(
        "오늘 읽은 부분만 사진으로 올리면, 그 내용 안에서만 리딩 문제를 만듭니다. "
        "여러 페이지를 한 번에 올릴 수 있어요."
    )

    r_level = st.selectbox("학습자 수준", LEVELS, index=2, key="r_level")

    r_source_mode = st.radio(
        "자료 선택 방식",
        ["📁 사진 파일 업로드", "📷 카메라로 촬영"],
        horizontal=True,
        key="r_source_mode",
    )

    r_image_bytes = None

    if r_source_mode == "📁 사진 파일 업로드":
        r_images = st.file_uploader(
            "읽은 영어원서 페이지",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"r_files_{st.session_state.reading_upload_nonce}",
            help="연속해서 읽은 페이지를 여러 장 선택하세요.",
        )
        if r_images:
            st.caption(f"선택된 사진: {len(r_images)}장")
            r_image_bytes = combine_uploaded_images(r_images)

    else:
        st.caption(
            "📱 휴대폰/태블릿에서는 아래 버튼을 누른 뒤 카메라/사진 찍기를 선택해 "
            "후면 카메라로 책 페이지를 촬영하세요."
        )
        r_camera_images = st.file_uploader(
            "📷 책 사진 촬영 또는 선택",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"r_cam_upload_{st.session_state.reading_upload_nonce}",
            help="여러 페이지를 촬영하거나 선택할 수 있습니다.",
        )
        if r_camera_images:
            st.caption(f"촬영/선택된 사진: {len(r_camera_images)}장")
            r_image_bytes = combine_uploaded_images(r_camera_images)

    if r_image_bytes is not None:
        if st.button("🔎 읽은 내용 분석", type="primary", key="r_analyze"):
            prompt = f"""
You are a Reading Material Analyzer for a {r_level} Korean learner.
Analyze ONLY the English book pages visible in the uploaded images.

Important:
- Do not invent events, facts, characters, motives, or context not supported by the uploaded pages.
- If a page is partially unreadable, mark uncertainty rather than guessing.
- Do not reproduce long copyrighted passages. Summarize in your own words.
- Preserve character names and essential story facts that are clearly visible.

Return JSON only:
{{
  "title": "book title if clearly visible, otherwise 읽은 영어원서",
  "section_summary": "2-4 sentence Korean summary of only the uploaded portion",
  "characters_or_entities": ["..."],
  "key_events_or_points": ["..."],
  "inference_clues": ["brief paraphrased clue 1", "brief paraphrased clue 2"],
  "readability_note": "clear / partly unclear and short Korean note"
}}
"""
            try:
                with st.spinner("읽은 페이지의 내용과 문제 출제 근거를 분석하고 있어요..."):
                    st.session_state.reading_analysis = gemini_json(prompt, r_image_bytes)
                    st.session_state.reading_questions = []
                    st.session_state.reading_grade = None
            except Exception as e:
                show_ai_error("리딩 자료 분석 오류", e)

    if st.session_state.reading_analysis:
        ra = st.session_state.reading_analysis
        st.divider()
        st.subheader("② 읽은 내용 확인")
        st.success(ra.get("section_summary", "읽은 부분 분석이 완료됐어요."))
        if ra.get("readability_note"):
            st.caption("사진 판독 상태: " + str(ra.get("readability_note")))

        st.subheader("③ 문제 스타일 선택")
        r_style = st.radio(
            "출제 스타일",
            ["TOEFL Junior 유형", "TOEFL 유형", "최선어학원 유형"],
            horizontal=True,
            key="r_style",
            help="공식/실제 기출문제를 복제하지 않고, 각 시험·학원에서 연습하는 독해 사고방식을 참고한 새 문제를 만듭니다.",
        )

        st.subheader("④ 문제 유형 선택")
        st.caption("원하는 유형만 골라도 되고 여러 유형을 섞어도 됩니다.")

        r_selected = []
        cols = st.columns(2)
        defaults = {"main_idea", "detail", "inference", "vocab_context", "character"}
        for idx, item in enumerate(READING_TYPES):
            with cols[idx % 2]:
                checked = st.checkbox(
                    f"{item['name']} — {item['description']}",
                    value=item["id"] in defaults,
                    key=f"r_type_{item['id']}",
                )
                if checked:
                    r_selected.append(item["id"])

        st.session_state.reading_selected_types = r_selected

        st.subheader("⑤ 문제 수 선택")
        r_count = st.selectbox(
            "문제 수",
            [5, 10, 15, 20],
            index=0,
            format_func=lambda x: f"{x}문제",
            key="r_count",
        )

        if st.button(
            "선택한 유형으로 Reading 문제 만들기 →",
            type="primary",
            use_container_width=True,
            disabled=not r_selected,
            key="r_make_quiz",
        ):
            type_map = {x["id"]: x for x in READING_TYPES}
            chosen = [type_map[x] for x in r_selected if x in type_map]

            prompt = f"""
You are an English Reading Question Writer for a Korean {r_level} learner.

SOURCE ANALYSIS OF THE UPLOADED PAGES:
{json.dumps(ra, ensure_ascii=False)}

Practice style: {r_style}
Selected question types:
{json.dumps(chosen, ensure_ascii=False)}
Question count: {r_count}

Create ORIGINAL reading-comprehension questions based ONLY on the uploaded-page analysis above.

Rules:
- Never use knowledge from later chapters, the full book, a movie, summaries, or the internet.
- Every correct answer must be supported by the uploaded portion.
- Inference questions must be inferable from at least one concrete clue in the uploaded portion.
- For Main Idea/Main Title, test the whole uploaded section, not one tiny detail.
- For Topic Sentence, test the central idea of a paragraph/section without requiring a long verbatim quotation.
- For Vocabulary in Context, use a word/expression clearly supported by the uploaded pages and test its contextual meaning.
- For TOEFL Junior style: age-appropriate context, clear evidence, plausible distractors.
- For TOEFL style: emphasize main idea, factual information, inference, vocabulary in context, reference, purpose, summary/coherence as appropriate. This is practice inspired by the skills, not an official TOEFL item.
- For 최선어학원 유형: create original advanced academy-style reading practice with close distractors and evidence-based inference. Do not copy proprietary questions.
- All questions must be multiple choice with EXACTLY 5 unique choices.
- Exactly one choice is correct.
- Do not include "선택 안 함", "정답 없음", or "none of the above".
- Store answer as a zero-based integer: A=0, B=1, C=2, D=3, E=4.
- Spread correct-answer positions across A-E as evenly as practical.
- Do not quote long passages from the book. Paraphrase when possible.
- explanation must be in Korean and briefly state the evidence/reason.

Return JSON only:
{{
  "questions": [
    {{
      "id": 1,
      "type_id": "inference",
      "type_name": "Inference",
      "format": "multiple_choice",
      "question": "English question",
      "choices": ["A text","B text","C text","D text","E text"],
      "answer": 0,
      "explanation": "Korean explanation grounded in the uploaded portion"
    }}
  ]
}}
"""
            try:
                with st.spinner(f"읽은 내용을 바탕으로 {r_count}문제를 만들고 있어요..."):
                    rq = gemini_json(prompt).get("questions", [])
                    rq = ensure_five_choices(rq, study_kind="Reading")
                    rq = validate_five_choice_questions(rq)
                    rq = balance_answer_positions(rq)
                    rq = validate_five_choice_questions(rq)

                    if len(rq) != r_count:
                        raise ValueError(
                            f"요청한 {r_count}문제 중 {len(rq)}문제만 생성되었습니다. 다시 문제 만들기를 눌러주세요."
                        )

                    allowed_types = set(r_selected)
                    bad_types = [
                        q.get("id")
                        for q in rq
                        if q.get("type_id") not in allowed_types
                    ]
                    if bad_types:
                        raise ValueError(
                            "선택하지 않은 문제 유형이 포함되어 출제를 중단했습니다. "
                            "문제 만들기를 다시 눌러주세요."
                        )

                    st.session_state.reading_questions = rq
                    st.session_state.reading_grade = None
                    st.session_state["r_active_level"] = r_level
                    st.session_state["r_active_style"] = r_style
            except Exception as e:
                show_ai_error("Reading 문제 생성 오류", e)

    if st.session_state.reading_questions:
        st.divider()
        st.subheader("⑥ Reading Test")

        with st.form("reading_quiz_form"):
            ranswers = {}
            for q in st.session_state.reading_questions:
                st.markdown(
                    f"**{q.get('id')}. [{q.get('type_name','Reading')}]** "
                    f"{clean_question_text(q.get('question',''))}"
                )
                ranswers[str(q.get("id"))] = radio_choice(
                    "정답 선택",
                    q.get("choices", []),
                    key=f"r_answer_{q.get('id')}",
                )
                st.write("")

            rsubmitted = st.form_submit_button("답안 제출 및 채점", type="primary")

        if rsubmitted:
            rcheck = local_objective_result(
                st.session_state.reading_questions,
                ranswers,
            )

            if rcheck.get("unanswered_ids"):
                st.warning(
                    "아직 답을 선택하지 않은 문항이 있어요: "
                    + ", ".join(map(str, rcheck["unanswered_ids"]))
                    + "번. 모든 문제에 답한 뒤 채점해주세요."
                )
            else:
                # Reading 객관식은 AI 재호출 없이 코드로 확정 채점.
                rdetails = []
                qmap = {str(q.get("id")): q for q in st.session_state.reading_questions}
                for d in rcheck["details"]:
                    q = qmap.get(str(d.get("id")), {})
                    item = dict(d)
                    item["type_name"] = q.get("type_name", "Reading")
                    item["explanation"] = q.get("explanation", "")
                    rdetails.append(item)

                wrong_types = []
                for d in rdetails:
                    if not d.get("correct") and d.get("type_name"):
                        wrong_types.append(d["type_name"])
                wrong_types = list(dict.fromkeys(wrong_types))

                rg = {
                    "score": rcheck["score"],
                    "correct_count": rcheck["correct_count"],
                    "total": rcheck["objective_count"],
                    "details": rdetails,
                    "weak_topics": wrong_types,
                }
                st.session_state.reading_grade = rg

                append_history({
                    "study_type": "Reading",
                    "material_title": (
                        (st.session_state.reading_analysis or {}).get("title")
                        or "읽은 영어원서"
                    ),
                    "learner_level": st.session_state.get("r_active_level", r_level),
                    "test_mode": st.session_state.get("r_active_style", ""),
                    "question_count": rg["total"],
                    "score": rg["score"],
                    "weak_items": rg["weak_topics"],
                    "reading_analysis": st.session_state.reading_analysis,
                })

    if st.session_state.reading_grade:
        st.divider()
        st.subheader("⑦ 채점 결과 · 유형별 오답 확인")
        rg = st.session_state.reading_grade

        rr1, rr2 = st.columns(2)
        rr1.metric("점수", f"{rg.get('score', 0)}점")
        rr2.metric("정답", f"{rg.get('correct_count', 0)} / {rg.get('total', 0)}")

        if rg.get("weak_topics"):
            st.warning("🎯 다시 연습할 유형: " + ", ".join(rg["weak_topics"]))
        else:
            st.success("🎉 이번 Reading Test는 모두 맞았어요.")

        st.markdown("#### 📋 문항별 정답과 근거")
        for d in rg.get("details", []):
            with st.container(border=True):
                st.markdown(
                    f"{'✅' if d.get('correct') else '❌'} "
                    f"**{d.get('id')}번 · {d.get('type_name','Reading')}**"
                )
                st.write("내 답:", d.get("user_answer", ""))
                st.write("정답:", d.get("answer", ""))
                if d.get("explanation"):
                    st.caption("근거/해설: " + str(d["explanation"]))

        if st.button("🔁 같은 읽은 부분으로 다시 출제", type="primary", key="r_retry"):
            st.session_state.reading_questions = []
            st.session_state.reading_grade = None
            st.rerun()


# ---------------------------------------------------------------------
# Grammar
# ---------------------------------------------------------------------
GRAMMAR_TYPES = [
    {"id": "grammar_form", "name": "Grammar Form Recognition", "description": "문법 형태와 구조 구별"},
    {"id": "contextual_grammar", "name": "Contextual Grammar", "description": "문맥 속 올바른 문법 선택"},
    {"id": "error_detection", "name": "Error Detection", "description": "틀린 어법/문법 요소 찾기"},
    {"id": "sentence_completion", "name": "Sentence Completion", "description": "문장 흐름에 맞는 구조 선택"},
    {"id": "sentence_transformation", "name": "Sentence Transformation", "description": "문장 변형·재구성"},
    {"id": "word_order", "name": "Word Order / Sentence Building", "description": "어순 및 문장 구성"},
    {"id": "integrated_usage", "name": "Integrated Grammar Usage", "description": "복수 문법 포인트 통합"},
    {"id": "advanced_usage", "name": "Advanced Usage & Inference", "description": "긴 문맥 속 심화 어법 판단"},
]

if active_page == "grammar":
    c1, c2 = st.columns([5, 1])
    with c2:
        if st.button("＋ 새 학습", key="g_reset", use_container_width=True):
            for k, v in {
                "grammar_analysis": None, "grammar_recommendation": None,
                "grammar_questions": [], "grammar_grade": None,
                "grammar_selected_types": [],
            }.items():
                st.session_state[k] = v
            st.session_state.grammar_upload_nonce += 1
            st.rerun()

    st.subheader("① 학습 자료 선택")
    st.caption("Vocabulary와 동일하게 학습자 수준을 먼저 선택하고 문법 교재 사진을 업로드합니다.")

    g_level = st.selectbox("학습자 수준", LEVELS, index=2, key="g_level")

    g_source_mode = st.radio(
        "자료 선택 방식",
        ["📁 사진 파일 업로드", "📷 카메라로 촬영", "📚 이전 문법 학습이력 불러오기"],
        horizontal=True,
        key="g_source_mode",
    )

    g_image_bytes = None

    if g_source_mode == "📁 사진 파일 업로드":
        g_images = st.file_uploader(
            "문법 학습자료 사진",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"g_files_{st.session_state.grammar_upload_nonce}",
            help="공부한 문법 페이지를 여러 장 한 번에 선택할 수 있습니다.",
        )
        if g_images:
            st.caption(f"선택된 사진: {len(g_images)}장")
            g_image_bytes = combine_uploaded_images(g_images)

    elif g_source_mode == "📷 카메라로 촬영":
        st.caption(
            "📱 휴대폰/태블릿에서는 아래 버튼을 누른 뒤 **카메라/사진 찍기**를 선택하세요. "
            "브라우저 셀프카메라 대신 기기의 기본 카메라가 열리므로 책을 찍기 좋은 **후면 카메라**를 사용할 수 있어요."
        )
        g_camera_images = st.file_uploader(
            "📷 문법 책 사진 촬영 또는 선택",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            key=f"g_cam_upload_{st.session_state.grammar_upload_nonce}",
            help="모바일에서는 '카메라/사진 찍기'를 선택해 후면 카메라로 촬영하세요. 여러 페이지도 선택할 수 있습니다.",
        )
        if g_camera_images:
            st.caption(f"촬영/선택된 사진: {len(g_camera_images)}장")
            g_image_bytes = combine_uploaded_images(g_camera_images)

    else:
        grammar_histories = [
            h for h in st.session_state.local_history
            if h.get("study_type") == "Grammar" and h.get("grammar_analysis")
        ]
        if grammar_histories:
            g_history_options = {}
            for h in grammar_histories:
                title = h.get("material_title") or h.get("grammar_analysis", {}).get("title") or "문법 학습자료"
                created = str(h.get("created_at", ""))[:10]
                mode = h.get("test_mode", "")
                label = f"{title} · {mode} · {created}"
                g_history_options[label] = h

            g_history_label = st.selectbox(
                "저장된 문법 학습이력",
                list(g_history_options.keys()),
                key="g_history_select",
            )
            if st.button("📚 이 문법 자료 불러오기", type="primary", key="g_history_load"):
                h = g_history_options[g_history_label]
                st.session_state.grammar_analysis = h.get("grammar_analysis")
                st.session_state.grammar_recommendation = None
                st.session_state.grammar_questions = []
                st.session_state.grammar_grade = None
                st.success("이전 문법 학습자료를 불러왔습니다.")
                st.rerun()
        else:
            st.info(
                "불러올 수 있는 문법 학습이력이 아직 없습니다. "
                "이번 업데이트 이후 완료한 Grammar 테스트부터 원본 문법 분석 내용이 함께 저장됩니다."
            )

    if g_image_bytes is not None:
        if st.button("🔎 AI 문법 분석", type="primary", key="g_analyze"):
            try:
                prompt = f"""
You are a Korean English grammar learning Material Analyzer Agent.
Analyze the uploaded grammar study pages for a {g_level} learner.
Do not merely OCR the page. Identify the grammar concepts the learner studied.
Return JSON only:
{{
  "title": "short Korean title",
  "summary": "Korean summary",
  "concepts": [
    {{
      "topic": "grammar topic",
      "structure": "core structure/form",
      "uses": ["use1","use2"],
      "key_points": ["point1","point2"],
      "example": "original example sentence",
      "cautions": ["common confusion/error"]
    }}
  ]
}}
Keep the concepts faithful to the uploaded material.
"""
                with st.spinner("문법 자료에서 핵심 개념을 분석하고 있어요..."):
                    st.session_state.grammar_analysis = gemini_json(prompt, g_image_bytes)
                    st.session_state.grammar_recommendation = None
                    st.session_state.grammar_questions = []
                    st.session_state.grammar_grade = None
            except Exception as e:
                show_ai_error("문법 분석 오류", e)

    if st.session_state.grammar_analysis:
        ga = st.session_state.grammar_analysis
        st.divider()
        st.subheader("② AI 자료 분석 → 문법 개념 확인·수정")
        st.success("문법 자료 분석 완료 · " + ga.get("summary", ""))

        concept_text = []
        for c in ga.get("concepts", []):
            concept_text.append(
                f"문법 주제: {c.get('topic','')}\n"
                f"핵심 구조: {c.get('structure','')}\n"
                f"주요 용법: {', '.join(c.get('uses', []))}\n"
                f"핵심 포인트: {', '.join(c.get('key_points', []))}\n"
                f"예문: {c.get('example','')}\n"
                f"주의점: {', '.join(c.get('cautions', []))}"
            )
        edited_concepts = st.text_area(
            "분석된 문법 내용 확인/수정",
            value="\n\n".join(concept_text),
            height=230,
            key="g_concept_edit",
        )

        st.subheader("③ 학습 조건 선택")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("학습자 수준", value=g_level, disabled=True, key="g_level_show")
        with c2:
            g_difficulty = st.selectbox(
                "난이도 / 시험유형",
                ["쉬움", "보통", "어려움", "TOSEL 수준", "TOEFL Junior 수준", "TOEFL 수준", "최선어학원 유형"],
                index=4, key="g_diff",
            )
        with c3:
            g_school = st.selectbox(
                "내신 준비형",
                ["적용 안 함", "중학교 내신", "고등학교 내신"],
                index=0, key="g_school",
            )

        if st.button("✨ AI 문제유형 추천", type="primary", key="g_recommend"):
            try:
                prompt = f"""
You are an English Grammar Recommender Agent.
Recommend the most educationally appropriate question types.

Learner level: {g_level}
Difficulty/test style: {g_difficulty}
School exam mode: {g_school}
Studied grammar:
{edited_concepts}

Available types:
{json.dumps(GRAMMAR_TYPES, ensure_ascii=False)}

Rules:
- Recommend a subset, not necessarily all.
- TOEFL Junior: emphasize grammar/form in context and sentence completion.
- TOEFL: do NOT claim there is a standalone official TOEFL grammar section; use academic-context sentence structure and language-use practice.
- 최선어학원 유형: create original advanced academy-style practice; never copy proprietary questions.
- 중학교/고등학교 내신: strengthen error detection, sentence transformation, word order, and integrated usage as appropriate.
Return JSON only:
{{"reason":"Korean explanation","recommended_type_ids":["..."]}}
"""
                with st.spinner("학습 조건에 맞는 문법 문제유형을 추천하고 있어요..."):
                    st.session_state.grammar_recommendation = gemini_json(prompt)
                    st.session_state.grammar_selected_types = st.session_state.grammar_recommendation.get("recommended_type_ids", [])
            except Exception as e:
                st.error(f"문법 문제유형 추천 오류: {e}")

        if st.session_state.grammar_recommendation:
            st.subheader("④ AI 추천 문제유형 → 사용자가 추가/삭제")
            st.info("✨ " + st.session_state.grammar_recommendation.get("reason", "학습 조건에 맞는 유형을 추천했습니다."))
            grecommended = set(st.session_state.grammar_recommendation.get("recommended_type_ids", []))
            gselected = []
            cols = st.columns(2)
            for i, t in enumerate(GRAMMAR_TYPES):
                with cols[i % 2]:
                    checked = st.checkbox(
                        f"{t['name']} — {t['description']}",
                        value=t["id"] in grecommended,
                        key=f"gtype_{t['id']}_{st.session_state.grammar_upload_nonce}",
                    )
                    if checked:
                        gselected.append(t["id"])
            st.session_state.grammar_selected_types = gselected

            st.subheader("⑤ 문제 수 선택 → 문제 출제")
            c1, c2 = st.columns([1, 2])
            with c1:
                g_count = st.selectbox(
                    "문제 수", [5, 10, 15, 20, 25, 30], index=0,
                    format_func=lambda x: f"{x}문제", key="g_count",
                )
            with c2:
                st.write(""); st.write("")
                g_make = st.button(
                    "선택한 조건으로 문제 만들기 →", type="primary",
                    use_container_width=True, disabled=not gselected, key="g_make",
                )

            if g_make:
                try:
                    selected_defs = [x for x in GRAMMAR_TYPES if x["id"] in gselected]
                    prompt = f"""
You are an expert English grammar assessment Quiz Generator Agent.
Create ORIGINAL grammar questions based on the studied material.

Learner level: {g_level}
Difficulty/test style: {g_difficulty}
School exam mode: {g_school}
Studied grammar:
{edited_concepts}
Selected question types:
{json.dumps(selected_defs, ensure_ascii=False)}
Question count: {g_count}

Requirements:
- Test the SAME grammar concepts but use NEW sentences/contexts; do not copy textbook examples.
- Exactly {g_count} questions.
- Use selected types as evenly as educationally appropriate.
- Most questions should be 4-choice multiple choice.
- Sentence transformation/building may use short_answer when useful.
- Exactly one defensible correct answer for multiple-choice.
- Include a concise Korean explanation and learning_point for every question.
- For multiple-choice, spread correct answer positions across A/B/C/D/E.
- Every multiple-choice item must have exactly 5 UNIQUE choices.
- There must be exactly ONE best answer.
- The correct answer MUST appear among the four choices.
- "answer" MUST be a zero-based integer index (A=0, B=1, C=2, D=3, E=4).
- IMPORTANT: If the Korean instruction says "밑줄 친/밑줄친" or the English instruction says "underlined",
  you MUST put the exact target word or phrase in "highlight_word".
- "highlight_word" MUST be an exact substring of "question" so the UI can underline it.
- Never write an instruction referring to an underlined part unless "highlight_word" is non-empty.
- EXCEPTION — Error Detection / 오류 찾기:
  Do NOT underline or visually mark the incorrect answer target in the sentence.
  The learner must identify the incorrect word or phrase from the five choices.
  Use "highlight_word": "".
  Do NOT say "identify the underlined word" or "밑줄 친 부분".
  Instead say "Identify the grammatically incorrect word or phrase in the sentence."
  or "다음 문장에서 문법적으로 적절하지 않은 부분을 고르세요."
- If no underline is needed, use "highlight_word": "".
Return JSON only as an array:
[
 {{
   "id":1,
   "type_id":"contextual_grammar",
   "type_name":"Contextual Grammar",
   "format":"multiple_choice",
   "question":"...",
   "highlight_word":"exact word or phrase in question that must be underlined, or empty string",
   "choices":["A text","B text","C text","D text","E text"],
   "answer":0,
   "explanation":"Korean explanation",
   "learning_point":"Korean learning point",
   "topic":"grammar concept"
 }}
]
For short_answer use "choices":[] and "answer":"model answer".
"""
                    with st.spinner(f"{g_count}개의 문법 문제를 만들고 있어요..."):
                        qs = gemini_json(prompt)
                        if isinstance(qs, dict):
                            qs = qs.get("questions", [])
                        # 1) 밑줄 메타데이터를 먼저 보정
                        qs = repair_missing_grammar_highlights(qs)

                        # 2) 객관식은 모두 5지선다로 정규화
                        qs = ensure_five_choices(qs, study_kind="Grammar")

                        # 3) 5지선다 기준으로만 최종 검증
                        #    (기존 4지선다용 검증/재생성 루틴과 충돌하지 않도록 분리)
                        qs = validate_five_choice_questions(qs)

                        # 4) 정답 위치 A~E 분산
                        qs = balance_answer_positions(qs)

                        # 5) 재배치 후 다시 한 번 검증
                        qs = validate_five_choice_questions(qs)

                        # 6) 밑줄 문제만 별도로 무결성 확인
                        bad_highlight_ids = []
                        for i, q in enumerate(qs):
                            if grammar_question_needs_highlight(q):
                                highlight = (
                                    q.get("highlight_word")
                                    or q.get("highlight_phrase")
                                    or q.get("underlined_text")
                                    or q.get("target_phrase")
                                    or q.get("underline")
                                    or ""
                                )
                                if not highlight or str(highlight) not in str(q.get("question", "")):
                                    bad_highlight_ids.append(q.get("id", i + 1))

                        if bad_highlight_ids:
                            raise ValueError(
                                "일부 문항의 밑줄 표시 정보를 확인하지 못했습니다. "
                                f"문항: {', '.join(map(str, bad_highlight_ids))}. "
                                "문제 만들기를 다시 눌러주세요."
                            )

                        st.session_state.grammar_questions = qs
                        st.session_state.grammar_grade = None
                        st.session_state["g_active_level"] = g_level
                        st.session_state["g_active_difficulty"] = g_difficulty
                        st.session_state["g_active_school"] = g_school
                        st.session_state["g_active_concepts"] = edited_concepts
                except Exception as e:
                    show_ai_error("문법 문제 생성 오류", e)

    if st.session_state.grammar_questions:
        st.divider()
        st.subheader("⑥ Grammar Test")
        with st.form("grammar_quiz_form"):
            ganswers = {}
            for q in st.session_state.grammar_questions:
                q_text = grammar_question_display(q)
                st.markdown(f"**{q.get('id')}. [{q.get('type_name','')}]** {q_text}")
                if q.get("format") == "short_answer":
                    ganswers[str(q.get("id"))] = st.text_input("답", key=f"g_answer_{q.get('id')}")
                else:
                    ganswers[str(q.get("id"))] = radio_choice(
                        "정답 선택",
                        q.get("choices", []),
                        key=f"g_answer_{q.get('id')}",
                    )
                st.write("")
            gsubmitted = st.form_submit_button("답안 제출 및 채점", type="primary")

        if gsubmitted:
            clean_answers = {k: str(v or "").strip() for k, v in ganswers.items()}
            local_check = local_objective_result(
                st.session_state.grammar_questions,
                clean_answers,
            )

            if local_check.get("unanswered_ids"):
                st.warning(
                    "아직 답을 선택하지 않은 문항이 있어요: "
                    + ", ".join(map(str, local_check["unanswered_ids"]))
                    + "번. 모든 문제에 답한 뒤 채점해주세요."
                )
            else:
                try:
                    # 객관식이 전부 정답이면 AI 채점/복습 호출 자체를 생략.
                    if (
                        local_check.get("all_objective")
                        and local_check["correct_count"] == local_check["objective_count"]
                    ):
                        gg = {
                            "score": 100,
                            "correct_count": local_check["correct_count"],
                            "total": local_check["objective_count"],
                            "weak_topics": [],
                            "category_scores": {},
                            "details": local_check["details"],
                            "review_cards": [],
                        }
                    else:
                        prompt = f"""
You are a Grammar Study Coach.
The application has already calculated objective-question correctness deterministically.
Your primary job is to create explanations and focused review cards.

Questions:
{json.dumps(st.session_state.grammar_questions, ensure_ascii=False)}
User answers:
{json.dumps(clean_answers, ensure_ascii=False)}

Return JSON only:
{{
 "score": 0,
 "correct_count": 0,
 "total": 0,
 "weak_topics": ["..."],
 "category_scores": {{
   "Grammar Form Recognition": {{"correct":0,"total":0}}
 }},
 "details": [
   {{"id":1,"correct":true,"user_answer":"...","answer":"...","explanation":"Korean explanation"}}
 ],
 "review_cards": [
   {{
     "topic":"...",
     "core_rule":"...",
     "structure":"...",
     "when_to_use":["..."],
     "common_mistakes":["..."],
     "contrast":"confusable grammar comparison",
     "examples":["original example 1","original example 2"],
     "study_tip":"..."
   }}
 ]
}}

Focus review cards on wrong/weak grammar.
Do not change the question choices.
"""
                        try:
                            with st.spinner("채점 결과를 정리하고 틀린 문법 복습 카드를 만들고 있어요..."):
                                gg = gemini_json(prompt)
                        except Exception as ai_error:
                            if local_check.get("all_objective"):
                                gg = {
                                    "score": local_check["score"],
                                    "correct_count": local_check["correct_count"],
                                    "total": local_check["objective_count"],
                                    "weak_topics": [],
                                    "category_scores": {},
                                    "details": local_check["details"],
                                    "review_cards": [],
                                }
                                st.info(
                                    "점수는 정상적으로 계산했습니다. "
                                    "AI 복습 카드 생성이 일시적으로 실패해 이번에는 복습 카드만 생략됐어요."
                                )
                            else:
                                raise ai_error

                        gg = merge_local_objective_grade(
                            gg,
                            local_check,
                            weak_key="weak_topics",
                            review_key="review_cards",
                        )

                    st.session_state.grammar_grade = gg
                    append_history({
                        "study_type": "Grammar",
                        "material_title": (
                            (st.session_state.grammar_analysis or {}).get("title")
                            or "문법 학습자료"
                        ),
                        "learner_level": st.session_state.get("g_active_level", g_level),
                        "test_mode": st.session_state.get("g_active_difficulty", ""),
                        "school_mode": st.session_state.get("g_active_school", ""),
                        "question_count": gg.get("total", len(st.session_state.grammar_questions)),
                        "score": gg.get("score", 0),
                        "weak_items": gg.get("weak_topics", []),
                        "grammar_analysis": st.session_state.grammar_analysis,
                        "grammar_concepts_text": st.session_state.get("g_active_concepts", ""),
                    })
                except Exception as e:
                    show_ai_error("문법 채점 오류", e)

    if st.session_state.grammar_grade:
        st.divider()
        st.subheader("⑦ 채점 결과 · 문법 진단 · 맞춤 복습")
        gg = st.session_state.grammar_grade
        c1, c2 = st.columns(2)
        c1.metric("점수", f"{gg.get('score',0)}점")
        c2.metric("정답", f"{gg.get('correct_count',0)} / {gg.get('total',0)}")

        weak = gg.get("weak_topics", [])
        if weak:
            st.warning("🎯 취약 문법: " + ", ".join(weak))
        else:
            st.success("🎉 이번 테스트에서 뚜렷한 취약 문법이 발견되지 않았어요.")

        if gg.get("category_scores"):
            st.markdown("#### 영역별 결과")
            for name, score in gg["category_scores"].items():
                total = score.get("total", 0)
                correct = score.get("correct", 0)
                if total:
                    st.progress(correct / total, text=f"{name}: {correct}/{total}")

        st.markdown("#### 🌱 틀린 문법 복습 카드")
        for card in gg.get("review_cards", []):
            with st.container(border=True):
                st.markdown(f"### {card.get('topic','')}")
                st.write("**핵심 규칙:**", card.get("core_rule", "-"))
                st.write("**핵심 구조:**", card.get("structure", "-"))
                if card.get("when_to_use"):
                    st.write("**언제 사용하나요?**")
                    for x in card["when_to_use"]:
                        st.write("• " + x)
                if card.get("common_mistakes"):
                    st.write("**자주 틀리는 부분**")
                    for x in card["common_mistakes"]:
                        st.write("• " + x)
                if card.get("contrast"):
                    st.write("**헷갈리는 문법 비교:**", card["contrast"])
                if card.get("examples"):
                    st.write("**새 예문**")
                    for x in card["examples"]:
                        st.write("• " + x)
                if card.get("study_tip"):
                    st.caption("학습 팁: " + card["study_tip"])

        with st.expander("📋 문항별 정답 확인"):
            for d in gg.get("details", []):
                st.markdown(
                    f"{'✅' if d.get('correct') else '❌'} **{d.get('id')}번** "
                    f"· 내 답: {d.get('user_answer','')} · 정답/예시: {d.get('answer','')}"
                )
                if d.get("explanation"):
                    st.caption(d["explanation"])

        if st.button("🔁 취약 문법으로 재시험", type="primary", key="g_retry"):
            weak_topics = gg.get("weak_topics", [])
            if not weak_topics:
                st.info("현재 뚜렷한 취약 문법이 없어 전체 문법을 다시 연습합니다.")
            try:
                retry_count = max(5, min(15, len(weak_topics) * 3 if weak_topics else 5))
                prompt = f"""
Create a NEW retry grammar test for the learner.
Weak topics: {json.dumps(weak_topics, ensure_ascii=False)}
Original studied grammar:
{st.session_state.get("g_active_concepts","")}
Level: {st.session_state.get("g_active_level","")}
Difficulty: {st.session_state.get("g_active_difficulty","")}

Create exactly {retry_count} NEW questions.
Never repeat previous sentences. Use different situations.
Focus on transfer of the weak grammar concepts.
Use 4-choice questions where possible and balance correct positions.
Return the same JSON question array format used before.
"""
                with st.spinner("취약 문법 중심의 새 문제를 만들고 있어요..."):
                    qs = gemini_json(prompt)
                    if isinstance(qs, dict):
                        qs = qs.get("questions", [])
                    st.session_state.grammar_questions = balance_answer_positions(qs)
                    st.session_state.grammar_grade = None
                    st.rerun()
            except Exception as e:
                st.error(f"재시험 생성 오류: {e}")

# ---------------------------------------------------------------------
# 학습 이력
# ---------------------------------------------------------------------
if active_page == "history":
    st.subheader("📊 학습 이력")
    if not st.session_state.learner_name:
        st.info("홈에서 이름 또는 별칭을 먼저 등록해주세요.")
    else:
        st.markdown(f"### {st.session_state.learner_name}님의 학습 이력")
        st.caption("이 기록은 서버 DB가 아니라 현재 브라우저의 localStorage에 저장됩니다.")

        histories = st.session_state.local_history
        if not histories:
            st.info("아직 저장된 학습 기록이 없습니다.")
        else:
            filter_mode = st.radio("학습 구분", ["전체", "Vocabulary", "Grammar"], horizontal=True)
            filtered = histories if filter_mode == "전체" else [x for x in histories if x.get("study_type") == filter_mode]
            for h in filtered:
                dt = h.get("created_at", "")[:16].replace("T", " ")
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.markdown(f"**{h.get('study_type','')}**")
                    c1.caption(dt)
                    c2.write(h.get("test_mode", ""))
                    c2.caption("취약: " + (", ".join(h.get("weak_items", [])) or "없음"))
                    c3.metric("점수", f"{h.get('score',0)}점")

        if st.button("🗑️ 이 사용자 학습 기록 초기화", key="clear_local_history"):
            st.session_state.local_history = []
            if streamlit_js_eval is not None:
                js_remove(
                    STORAGE_HISTORY_PREFIX + st.session_state.learner_name,
                    f"clear_hist_{random.randint(1,999999)}",
                )
            st.success("현재 사용자의 학습 기록만 초기화했습니다.")


# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------
st.markdown(
    """
    <div style="
        text-align:center;
        margin-top:48px;
        padding:20px 0 8px 0;
        color:#9AA0A6;
        font-size:13px;
        letter-spacing:0.3px;
    ">
        Powered by <strong>Lauren</strong>
    </div>
    """,
    unsafe_allow_html=True,
)



st.markdown("<div style=\"text-align:center;color:#9ca3af;font-size:12px;margin-top:30px;\">Powered by Lauren</div>", unsafe_allow_html=True)

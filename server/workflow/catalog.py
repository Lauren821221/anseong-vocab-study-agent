QUESTION_TYPES = {
    "word_meaning": ("단어-뜻 연결", "단어와 올바른 의미를 연결하는 기본 어휘 문제"),
    "meaning_word": ("뜻 보고 단어 찾기", "뜻·설명에 맞는 영어 단어를 찾는 문제"),
    "syn_ant": ("유의어·반의어", "유의어와 반의어를 이용해 의미 관계를 확장하는 문제"),
    "sentence_blank": ("문장 빈칸", "문맥에 맞는 단어나 표현을 고르는 문제"),
    "context_meaning": ("문맥 속 의미", "문장이나 짧은 글 안에서 단어의 실제 의미를 파악하는 문제"),
    "usage": ("어휘 쓰임 / Usage", "자연스럽고 정확한 어휘 사용을 판단하는 문제"),
    "collocation": ("Collocation · 숙어", "함께 자주 쓰이는 표현·숙어·연어를 익히는 문제"),
    "sentence_completion": ("문장 완성", "어휘와 문법을 함께 적용해 문장을 완성하는 문제"),
    "context_inference": ("문맥 추론", "짧은 지문에서 어휘 의미·의도·함축을 추론하는 문제"),
    "writing": ("서술형 · 영작", "학습 단어를 활용해 직접 문장을 작성하는 문제"),
}

BASE = {
    "유치원": {
        "쉬움": ["word_meaning", "meaning_word"],
        "보통": ["word_meaning", "meaning_word", "sentence_blank"],
        "어려움": ["meaning_word", "sentence_blank", "syn_ant"],
    },
    "초등 저학년": {
        "쉬움": ["word_meaning", "meaning_word", "sentence_blank"],
        "보통": ["word_meaning", "meaning_word", "sentence_blank", "context_meaning"],
        "어려움": ["sentence_blank", "context_meaning", "syn_ant", "sentence_completion"],
    },
    "초등 고학년": {
        "쉬움": ["word_meaning", "sentence_blank", "context_meaning"],
        "보통": ["sentence_blank", "context_meaning", "syn_ant", "sentence_completion"],
        "어려움": ["context_meaning", "usage", "collocation", "sentence_completion", "context_inference"],
    },
    "중학생": {
        "쉬움": ["word_meaning", "sentence_blank", "context_meaning"],
        "보통": ["context_meaning", "syn_ant", "usage", "sentence_completion"],
        "어려움": ["usage", "collocation", "sentence_completion", "context_inference", "writing"],
    },
    "고등학생": {
        "쉬움": ["context_meaning", "syn_ant", "sentence_completion"],
        "보통": ["usage", "collocation", "sentence_completion", "context_inference"],
        "어려움": ["context_meaning", "usage", "collocation", "context_inference", "writing"],
    },
    "성인": {
        "쉬움": ["word_meaning", "context_meaning", "sentence_completion"],
        "보통": ["context_meaning", "usage", "collocation", "sentence_completion", "writing"],
        "어려움": ["usage", "collocation", "context_inference", "writing", "context_meaning"],
    },
}

EXAM = {
    "TOSEL 수준": {
        "유치원": ["word_meaning", "meaning_word"],
        "초등 저학년": ["word_meaning", "meaning_word", "sentence_blank"],
        "초등 고학년": ["word_meaning", "sentence_blank", "context_meaning", "sentence_completion"],
        "중학생": ["sentence_blank", "context_meaning", "sentence_completion", "usage"],
        "고등학생": ["context_meaning", "usage", "sentence_completion", "context_inference"],
        "성인": ["context_meaning", "usage", "sentence_completion", "context_inference"],
    },
    "TOEFL Junior 수준": ["sentence_blank", "context_meaning", "usage", "sentence_completion", "context_inference"],
    "TOEFL 수준": ["context_meaning", "usage", "collocation", "context_inference", "writing"],
    "최선어학원 유형": ["word_meaning", "context_meaning", "sentence_completion", "collocation", "context_inference"],
}

SCHOOL_ADD = {
    "중학교 내신": ["sentence_blank", "usage", "sentence_completion", "writing"],
    "고등학교 내신": ["context_meaning", "usage", "collocation", "context_inference", "writing"],
}

def recommended_types(level: str, difficulty: str, school_mode: str = "적용 안 함"):
    if difficulty in ("쉬움", "보통", "어려움"):
        keys = list(BASE.get(level, BASE["성인"])[difficulty])
    elif difficulty == "TOSEL 수준":
        keys = list(EXAM["TOSEL 수준"].get(level, EXAM["TOSEL 수준"]["초등 고학년"]))
    else:
        keys = list(EXAM.get(difficulty, BASE.get(level, BASE["성인"])["보통"]))

    if school_mode in SCHOOL_ADD:
        # 내신형은 관련 유형을 앞쪽에 보강하되 과도하게 많은 기본 체크는 피한다.
        for x in SCHOOL_ADD[school_mode]:
            if x not in keys:
                keys.append(x)
    return keys[:6]

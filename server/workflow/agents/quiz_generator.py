from server.utils.config import generate_json
from server.workflow.catalog import QUESTION_TYPES


class QuizGeneratorAgent:
    def run(
        self,
        learner_level,
        difficulty,
        school_mode,
        words,
        type_ids,
        question_count,
    ):
        selected = [
            QUESTION_TYPES[x][0]
            for x in type_ids
            if x in QUESTION_TYPES
        ]

        selected_ids = [
            x for x in type_ids
            if x in QUESTION_TYPES
        ]

        word_text = ", ".join(
            [
                w.get("word", "")
                for w in words
                if w.get("word")
            ]
        )

        meaning_text = "; ".join(
            [
                f"{w.get('word', '')}={w.get('meaning', '')}"
                for w in words
                if w.get("word")
            ]
        )

        level_rule = {
            "유치원":
                "Use extremely short, concrete, child-friendly English. "
                "Prefer recognition over production.",

            "초등 저학년":
                "Use short familiar sentences and concrete everyday situations.",

            "초등 고학년":
                "Use school-age contexts, moderate sentence length, "
                "and simple inference.",

            "중학생":
                "Use school-textbook-like context, vocabulary usage, "
                "grammar-in-context, and moderate inference.",

            "고등학생":
                "Use denser context, precise usage, inference, collocation, "
                "and school-exam style reasoning.",

            "성인":
                "Use practical and academic contexts appropriate "
                "to the selected difficulty.",

        }.get(learner_level, "")

        school_rule = {
            "적용 안 함":
                "Do not force Korean school-exam conventions.",

            "중학교 내신":
                "Emphasize textbook-style vocabulary-in-context, blanks, "
                "usage, sentence completion, and short constructed response "
                "suitable for Korean middle-school exams.",

            "고등학교 내신":
                "Emphasize contextual vocabulary, precise usage, collocation, "
                "inference, paraphrase and constructed response suitable "
                "for Korean high-school exams.",

        }.get(school_mode, "")

        prompt = f"""
You are the quiz-generation agent for
'안성맞춤 수준별 단어 스터디 에이전트'.

LEARNER={learner_level}
DIFFICULTY_OR_EXAM_STYLE={difficulty}
SCHOOL_EXAM_MODE={school_mode}

STUDIED_WORDS={word_text}
WORD_MEANINGS_IF_AVAILABLE={meaning_text}

USER_SELECTED_TYPE_IDS={", ".join(selected_ids)}
USER_SELECTED_TYPES={", ".join(selected)}

QUESTION_COUNT={question_count}


==================================================
CORE GENERATION RULES
==================================================

Generate exactly {question_count} ORIGINAL
vocabulary-learning questions.

1. Uploaded/stored vocabulary is the primary target.

2. Do NOT silently replace studied vocabulary
   with unrelated vocabulary.

3. Use ONLY question types selected by the user.

4. Distribute selected question types reasonably.

5. {level_rule}

6. {school_rule}

7. Multiple-choice questions must have exactly
   FOUR plausible choices.

8. Writing questions must use:
   format = "short_answer"

9. All other questions must use:
   format = "multiple_choice"

10. The correct answer must be unambiguous.

11. Never copy or reproduce official copyrighted
    TOEFL, TOEFL Junior, TOSEL, academy,
    textbook or school-exam questions.

12. Create completely original questions
    targeting similar learning skills.


==================================================
DIFFICULTY / EXAM STYLE
==================================================

쉬움:
- direct vocabulary recognition
- simple meanings
- familiar sentences
- low inference demand

보통:
- vocabulary in context
- sentence completion
- basic usage
- synonyms / antonyms
- moderate inference

어려움:
- precise usage
- collocations
- contextual inference
- distractors with similar meanings

TOSEL 수준:
- age-appropriate communicative vocabulary
- short situations
- recognition and basic context
- adjust cognitive demand to learner age

TOEFL Junior 수준:
- vocabulary in context
- grammar/vocabulary integration
- sentence completion
- short reading context
- age-appropriate academic vocabulary

TOEFL 수준:
- precise meaning in context
- academic/daily reading context
- inference
- paraphrase
- collocation
- nuanced vocabulary distinction

최선어학원 유형:
Use a challenging diagnostic mixture inspired by:
- Meaning Recognition
- Meaning in Context
- Sentence Completion
- Collocation & Usage
- Advanced Context / Inference


==================================================
QUESTION TYPE DISPLAY RULES
==================================================

The learner must ALWAYS be able to identify
the vocabulary or expression being tested.

Never say:
"밑줄 친 단어"
"밑줄 친 표현"
"underlined word"
"underlined expression"

unless highlight_word is actually provided.


--------------------------------------------------
1. MEANING / DEFINITION
--------------------------------------------------

Clearly show the target vocabulary.

Example:

question:
"'glamorous'의 뜻으로 가장 알맞은 것은?"

target_word:
"glamorous"

highlight_word:
"glamorous"


--------------------------------------------------
2. SYNONYM
--------------------------------------------------

Clearly identify the target word.

Example:

question:
"'rapid'와 의미가 가장 가까운 단어는?"

target_word:
"rapid"

highlight_word:
"rapid"


--------------------------------------------------
3. ANTONYM
--------------------------------------------------

Clearly identify the target word.

Example:

question:
"'ancient'와 의미가 반대인 단어는?"

target_word:
"ancient"

highlight_word:
"ancient"


--------------------------------------------------
4. SENTENCE COMPLETION / BLANK
--------------------------------------------------

The missing vocabulary position MUST use:

_____

Example:

"The scientist _____ the results carefully."

Do NOT use highlight_word for the blank itself.


--------------------------------------------------
5. MEANING IN CONTEXT
--------------------------------------------------

The tested vocabulary MUST appear
inside the sentence or passage.

Example:

"The city experienced a rapid increase in population.
문장에서 'rapid'의 의미로 가장 알맞은 것은?"

target_word:
"rapid"

highlight_word:
"rapid"


--------------------------------------------------
6. USAGE / 어휘 쓰임
--------------------------------------------------

VERY IMPORTANT.

If the learner must find the awkward or incorrect
vocabulary usage, EVERY choice must clearly identify
the vocabulary being evaluated.

Every choice MUST be an object.

Example:

[
  {{
    "text":
      "The mayor is responsible for running civic programs.",
    "highlight_word":
      "responsible"
  }},
  {{
    "text":
      "She lives a glamorous life as a movie star.",
    "highlight_word":
      "glamorous"
  }},
  {{
    "text":
      "The chef used gourmet ingredients.",
    "highlight_word":
      "gourmet"
  }},
  {{
    "text":
      "He studied hard, hence he failed the test.",
    "highlight_word":
      "hence"
  }}
]

Never generate a Usage question
where a choice has no highlight_word.


--------------------------------------------------
7. COLLOCATION
--------------------------------------------------

Clearly identify the tested vocabulary
or expression.

Example:

question:
"다음 중 'make'와 가장 자연스럽게
어울리는 표현은?"

highlight_word:
"make"


--------------------------------------------------
8. WORD FORM / GRAMMAR IN CONTEXT
--------------------------------------------------

The word or word family being evaluated
must be clearly identifiable.

If a blank is used, represent it with _____.


--------------------------------------------------
9. CONTEXT INFERENCE
--------------------------------------------------

Provide enough context for inference.

Clearly identify the word whose meaning
or usage must be inferred.


--------------------------------------------------
10. ADVANCED APPLICATION
--------------------------------------------------

Clearly separate:

- context
- target vocabulary
- actual question

The learner must never have to guess
which vocabulary item is being tested.


==================================================
CHOICE STRUCTURE
==================================================

For ALL multiple-choice questions,
return choices as objects.

Correct:

"choices": [
  {{
    "text": "choice sentence or word",
    "highlight_word": ""
  }},
  {{
    "text": "choice sentence or word",
    "highlight_word": ""
  }},
  {{
    "text": "choice sentence or word",
    "highlight_word": ""
  }},
  {{
    "text": "choice sentence or word",
    "highlight_word": ""
  }}
]

If a specific word inside a choice should be
visually emphasized, place that exact word in
highlight_word.

For ordinary choices that do not require emphasis:

"highlight_word": ""


==================================================
ANSWER RULE
==================================================

The "answer" field MUST contain the ORIGINAL
choice text only.

Do NOT include underline characters,
HTML, Markdown, numbering, A/B/C/D,
or formatting in the answer.

Example:

choice:

{{
  "text":
    "He studied hard, hence he failed the test.",
  "highlight_word":
    "hence"
}}

answer:

"He studied hard, hence he failed the test."


==================================================
QUALITY VALIDATION
==================================================

Before returning JSON, internally check
EVERY question.

Regenerate any question if:

- it says "밑줄 친" but highlight_word is missing
- a Usage choice has no highlight_word
- a blank question has no _____
- target vocabulary cannot be identified
- correct answer is ambiguous
- multiple-choice question does not have
  exactly four choices
- the question does not test studied vocabulary
- answer differs from the original correct choice text
- a type_id was not selected by the user


==================================================
OUTPUT JSON
==================================================

Return JSON only.

{{
  "questions": [
    {{
      "id": 1,

      "type_id":
        "one user-selected type id",

      "type_name":
        "Korean type name",

      "format":
        "multiple_choice or short_answer",

      "question":
        "question text",

      "choices": [
        {{
          "text": "choice text",
          "highlight_word": ""
        }},
        {{
          "text": "choice text",
          "highlight_word": ""
        }},
        {{
          "text": "choice text",
          "highlight_word": ""
        }},
        {{
          "text": "choice text",
          "highlight_word": ""
        }}
      ],

      "answer":
        "exact original correct choice text or model answer",

      "target_word":
        "studied target word",

      "highlight_word":
        "word inside question to emphasize or empty string",

      "explanation":
        "short Korean explanation"
    }}
  ]
}}
"""

        data = generate_json(prompt)

        qs = data.get("questions", [])

        # 요청한 문제 수보다 많이 반환된 경우 자름
        if len(qs) > question_count:
            qs = qs[:question_count]

        # 방어 로직:
        # 구버전/예외 응답에서 choice가 문자열로 오더라도
        # 프론트엔드가 처리할 수 있도록 그대로 허용한다.
        return {
            "questions": qs
        }

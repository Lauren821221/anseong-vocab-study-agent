from server.utils.config import generate_json
from server.workflow.catalog import QUESTION_TYPES

class QuizGeneratorAgent:
    def run(self, learner_level, difficulty, school_mode, words, type_ids, question_count):
        selected = [QUESTION_TYPES[x][0] for x in type_ids if x in QUESTION_TYPES]
        word_text = ", ".join([w.get("word", "") for w in words if w.get("word")])
        meaning_text = "; ".join([
            f"{w.get('word','')}={w.get('meaning','')}" for w in words if w.get("word")
        ])

        level_rule = {
            "유치원": "Use extremely short, concrete, child-friendly English. Prefer recognition over production.",
            "초등 저학년": "Use short familiar sentences and concrete everyday situations.",
            "초등 고학년": "Use school-age contexts, moderate sentence length, and simple inference.",
            "중학생": "Use school-textbook-like context, vocabulary usage, grammar-in-context, and moderate inference.",
            "고등학생": "Use denser context, precise usage, inference, collocation, and school-exam style reasoning.",
            "성인": "Use practical and academic contexts appropriate to the selected difficulty.",
        }.get(learner_level, "")

        school_rule = {
            "적용 안 함": "Do not force Korean school-exam conventions.",
            "중학교 내신": "Emphasize textbook-style vocabulary-in-context, blanks, usage, sentence completion, and short constructed response suitable for Korean middle-school exams.",
            "고등학교 내신": "Emphasize contextual vocabulary, precise usage, collocation, inference, paraphrase and constructed response suitable for Korean high-school exams.",
        }.get(school_mode, "")

        prompt = f"""
You are the quiz-generation agent for '안성맞춤 수준별 단어 스터디 에이전트'.

LEARNER={learner_level}
DIFFICULTY_OR_EXAM_STYLE={difficulty}
SCHOOL_EXAM_MODE={school_mode}
STUDIED_WORDS={word_text}
WORD_MEANINGS_IF_AVAILABLE={meaning_text}
USER_SELECTED_TYPES={", ".join(selected)}
QUESTION_COUNT={question_count}

Generate exactly {question_count} ORIGINAL vocabulary-learning questions.

Core rules:
1. The uploaded/stored vocabulary is the primary target. Do not silently replace it with unrelated target vocabulary.
2. Use ONLY the question types selected by the user and distribute them reasonably.
3. {level_rule}
4. {school_rule}
5. If difficulty is TOSEL 수준, adjust cognitive demand by age/learner level and favor communicative, age-appropriate tasks.
6. If difficulty is TOEFL Junior 수준, emphasize grammar/vocabulary in context, sentence completion, and short reading context.
7. If difficulty is TOEFL 수준, emphasize vocabulary and meaning in context, concise daily/academic reading, inference and precise usage.
8. If difficulty is 최선어학원 유형, use a challenging diagnostic mix inspired by: meaning recognition, meaning in context, sentence completion, collocation/usage, advanced inference.
9. Do NOT copy or claim to reproduce official/copyrighted test questions. Create new questions that target similar skills.
10. All multiple-choice questions must have exactly four plausible choices.
11. For writing, use short_answer. For all other types, use multiple_choice.
12. Keep the correct answer unambiguous.

Return JSON only:
{{
  "questions":[
    {{
      "id":1,
      "type_id":"one selected id",
      "type_name":"Korean type name",
      "format":"multiple_choice or short_answer",
      "question":"question text",
      "choices":["A","B","C","D"],
      "answer":"exact correct choice text or model answer",
      "target_word":"one studied target word",
      "explanation":"short Korean explanation"
    }}
  ]
}}
"""
        data = generate_json(prompt)
        qs = data.get("questions", [])
        if len(qs) > question_count:
            qs = qs[:question_count]
        return {"questions": qs}

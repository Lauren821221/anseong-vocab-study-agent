from server.utils.config import generate_json
from server.workflow.catalog import QUESTION_TYPES

class QuizGeneratorAgent:
    def run(self, learner_level, difficulty, words, type_ids, question_count):
        selected=[QUESTION_TYPES[x][0] for x in type_ids if x in QUESTION_TYPES]
        word_text=", ".join([w.get("word","") for w in words if w.get("word")])
        prompt=f"""
You are an English vocabulary test writer.
Target learner: {learner_level}
Difficulty/style: {difficulty}
Studied vocabulary: {word_text}
Allowed question types ONLY: {", ".join(selected)}
Create exactly {question_count} questions, distributed as evenly as possible among allowed types.

Rules:
- Test primarily the uploaded/studied vocabulary. Do not replace it with unrelated target words.
- Adjust sentence length, distractors, grammar, and context to learner level and difficulty.
- For kindergarten/young learners use very short, concrete, child-friendly language.
- TOSEL style should be age/cognitive-stage appropriate and communication oriented.
- TOEFL Junior style should emphasize vocabulary/grammar in context and short reading context.
- TOEFL style should emphasize contextual meaning, academic/nonacademic reading, inference and usage.
- "최선어학원 유형" should be a challenging academy-style diagnostic mix: meaning recognition, context, sentence completion, collocation/usage, advanced inference.
- Do not claim these are official copyrighted test questions. Create original questions inspired by skill types.
- Multiple choice questions must have exactly 4 choices.
- guided writing may be short-answer; otherwise use multiple_choice.

Return JSON:
{{
 "questions":[
   {{
    "id":1,
    "type_id":"one allowed id",
    "type_name":"Korean type name",
    "format":"multiple_choice or short_answer",
    "question":"question text",
    "choices":["A","B","C","D"],
    "answer":"exact correct choice text for MC, or model answer for short",
    "target_word":"studied target word",
    "explanation":"short Korean explanation"
   }}
 ]
}}
"""
        data=generate_json(prompt)
        qs=data.get("questions",[])
        if len(qs)>question_count: qs=qs[:question_count]
        return {"questions":qs}

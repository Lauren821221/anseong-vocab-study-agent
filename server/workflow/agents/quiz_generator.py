from server.utils.config import generate_text
from server.utils.json_utils import extract_json


class QuizGeneratorAgent:
    def run(self, state):
        prompt = f"""
학습자 수준: {state['learner_level']}
문제 수: {state['question_count']}
선택한 문제 유형: {state['problem_types']}
우선 사용할 학습 단어: {state.get('focus_words', [])}
원본 자료 분석: {state['analysis']}

규칙:
- 원본 자료의 단어와 표현을 중심으로 출제하세요.
- 수준에 맞게 난이도를 조절하세요.
- 정답은 하나로 명확해야 합니다.
- 객관식은 보기 4개입니다.
- 문제 유형을 균형 있게 섞습니다.
- id는 q1, q2 ... 형식입니다.
- question_type은 multiple_choice 또는 short_answer입니다.

다음 JSON만 반환하세요.
{{
  "title": "맞춤 영어 단어 테스트",
  "questions": [
    {{
      "id": "q1",
      "question_type": "multiple_choice",
      "problem_type": "meaning_choice",
      "target_word": "example",
      "question": "문제",
      "options": ["A","B","C","D"],
      "correct_answer": "A",
      "explanation": "해설"
    }}
  ]
}}
"""
        response_text = generate_text(
            prompt,
            "당신은 수준별 영어 문제 출제 전문가입니다. 반드시 JSON만 반환하세요.",
            0.5,
        )
        return {**state, "quiz": extract_json(response_text)}

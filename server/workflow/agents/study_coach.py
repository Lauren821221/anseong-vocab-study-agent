from server.utils.config import generate_text
from server.utils.json_utils import extract_json


class StudyCoachAgent:
    def run(self, state):
        prompt = f"""
학습자 수준: {state['learner_level']}
채점 결과: {state['grading']}
원본 학습 자료: {state.get('analysis', {})}

틀린 단어를 중심으로 다음 학습을 설계하세요.

다음 JSON만 반환하세요.
{{
  "related_words": [
    {{"word":"단어","meaning":"뜻","reason":"함께 공부하면 좋은 이유"}}
  ],
  "study_plan": "다음 2~3회 학습에서 무엇을 하면 좋은지"
}}

약한 단어가 있으면 관련 단어 5~10개,
약한 단어가 없으면 확장 학습 단어 3~5개를 제안하세요.
"""
        response_text = generate_text(
            prompt,
            "당신은 개인 맞춤 영어 어휘 학습 코치입니다. 반드시 JSON만 반환하세요.",
            0.5,
        )
        coaching = extract_json(response_text)
        grading = dict(state["grading"])
        grading["related_words"] = coaching.get("related_words", [])
        grading["study_plan"] = coaching.get("study_plan", "")
        return {**state, "grading": grading}

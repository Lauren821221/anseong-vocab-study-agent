from server.utils.config import generate_text
from server.utils.json_utils import extract_json


class ProblemRecommenderAgent:
    def run(self, state):
        analysis = state["analysis"]
        level = state["learner_level"]

        prompt = f"""
학습자 수준: {level}
추출된 학습 자료: {analysis}

이 학습자에게 적합한 문제 유형을 4~6개 추천하세요.
유치원이면 문제 추천보다 단어 노출과 예문 학습을 우선하세요.

가능한 문제 유형 id:
meaning_choice, word_choice, sentence_blank, context_meaning,
collocation, synonym_antonym, sentence_building, inference, usage_error

다음 JSON만 반환하세요.
{{
  "recommended_problem_types": [
    {{"id":"meaning_choice","name":"단어 뜻 고르기","reason":"추천 이유"}}
  ]
}}
"""
        response_text = generate_text(
            prompt,
            "당신은 수준별 영어 평가 설계 전문가입니다. 반드시 JSON만 반환하세요.",
            0.3,
        )
        recommendation = extract_json(response_text)
        merged = dict(analysis)
        merged["recommended_problem_types"] = recommendation.get(
            "recommended_problem_types", []
        )
        return {**state, "analysis": merged}

from server.utils.config import analyze_image
from server.utils.json_utils import extract_json


class MaterialAnalyzerAgent:

    def run(self, state):
        level = state["learner_level"]
        image_bytes = state["image_bytes"]
        mime_type = state["mime_type"]

        prompt = f"""
학습자 수준: {level}

업로드된 영어 학습자료 이미지에서 실제로 확인되는 영어 단어와 표현을 분석하세요.
읽기 어려운 글자는 추측하지 마세요.

다음 JSON 형식만 반환하세요.

{{
  "extracted_words": ["word1", "word2"],
  "word_details": [
    {{
      "word": "example",
      "meaning": "예시",
      "context": "이미지에서 확인된 사용 맥락 또는 짧은 메모"
    }}
  ],
  "difficulty_summary": "이 자료의 난이도와 특징",
  "study_advice": "이 수준의 학습자가 이 자료를 공부하는 방법"
}}
"""

        response_text = analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt,
            system_instruction=(
                "당신은 영어 교육 전문가이자 학습 자료 분석 에이전트입니다. "
                "반드시 JSON만 반환하세요."
            ),
        )

        return {
            **state,
            "analysis": extract_json(response_text),
        }

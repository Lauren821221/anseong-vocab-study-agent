from server.utils.config import generate_text
from server.utils.json_utils import extract_json


class KindergartenExampleAgent:
    def run(self, analysis):
        prompt = f"""
다음은 유치원 학습자의 영어 단어 자료입니다.
{analysis}

주요 단어 각각에 대해 기초 / 기본 / 중급 / 상급 예문을 하나씩 만드세요.

난이도:
- 기초: 2~4단어
- 기본: 4~6단어
- 중급: 6~9단어
- 상급: 8~12단어

영어 문장마다 자연스러운 한국어 뜻을 붙이세요.

다음 JSON만 반환하세요.
{{
  "words": [
    {{
      "word": "apple",
      "meaning": "사과",
      "examples": {{
        "기초": {{"english":"An apple.","korean":"사과예요."}},
        "기본": {{"english":"I like apples.","korean":"나는 사과를 좋아해요."}},
        "중급": {{"english":"...","korean":"..."}},
        "상급": {{"english":"...","korean":"..."}}
      }}
    }}
  ],
  "parent_tip": "예문을 활용하는 간단한 방법"
}}
"""
        response_text = generate_text(
            prompt,
            "당신은 유아 영어 문장 학습 전문가입니다. 반드시 JSON만 반환하세요.",
            0.6,
        )
        return extract_json(response_text)

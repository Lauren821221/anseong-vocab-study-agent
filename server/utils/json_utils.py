import json
import re


def extract_json(text: str):
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    obj_match = re.search(r"\{.*\}", text, re.S)
    if obj_match:
        return json.loads(obj_match.group(0))

    arr_match = re.search(r"\[.*\]", text, re.S)
    if arr_match:
        return json.loads(arr_match.group(0))

    raise ValueError("LLM 응답에서 JSON을 찾을 수 없습니다.")

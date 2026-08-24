import json, re
from pydantic_settings import BaseSettings, SettingsConfigDict
from google import genai
from google.genai import types

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./history.db"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
client = genai.Client(api_key=settings.GEMINI_API_KEY)

def _json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    return json.loads(m.group(1) if m else text)

def generate_json(prompt: str):
    r = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.25,
            response_mime_type="application/json",
        ),
    )
    return _json(r.text)

def analyze_image(image_bytes: bytes, mime_type: str, learner_level: str):
    prompt = f"""
You are a vocabulary-learning material analyzer.
Learner level: {learner_level}
Analyze ONLY the visible English learning material in this image.
Extract English vocabulary/phrases accurately. Do not invent invisible words.
Return JSON:
{{
 "title":"short Korean material title",
 "words":[{{"word":"English word/phrase","meaning":"Korean meaning if inferable, otherwise empty"}}],
 "summary":"Korean summary of what was studied"
}}
Deduplicate words. Preserve phrases when they are taught as a phrase.
"""
    r = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
        config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
    )
    return _json(r.text)
